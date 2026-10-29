import os
import re
import unicodedata
from time import perf_counter

import chromadb
from sentence_transformers import SentenceTransformer
from FlagEmbedding import FlagReranker
from rank_bm25 import BM25Okapi


# ============================================================
# CONFIGURACOES
# ============================================================

MODELO_EMBEDDING = "intfloat/multilingual-e5-base"
MODELO_RERANKER = "BAAI/bge-reranker-v2-m3"

CHROMA_PATH = os.getenv("CHROMA_PATH", "banco_vetorial")
NOME_COLECAO = "campusia"

# Recuperar um conjunto maior e reduzir apenas depois do reranking.
TOP_K_SEMANTICO = 20
TOP_K_LEXICAL = 20
TOP_CANDIDATOS_RRF = 5
TOP_FINAL_PADRAO = 5
RRF_K = 60


# ============================================================
# CARREGAMENTO DOS MODELOS
# ============================================================

print("Carregando modelo de embeddings...")
modelo_embedding = SentenceTransformer(MODELO_EMBEDDING)

print("Carregando reranker...")
reranker = FlagReranker(
    MODELO_RERANKER,
    use_fp16=False,
)


# ============================================================
# CHROMADB
# ============================================================

print("Conectando ao banco vetorial...")
cliente = chromadb.PersistentClient(path=CHROMA_PATH)
colecao = cliente.get_collection(name=NOME_COLECAO)


# ============================================================
# FUNCOES AUXILIARES
# ============================================================

def normalizar_busca(texto: str) -> str:
    """
    Normaliza caixa e acentos para a busca lexical.
    Mantem letras e numeros, incluindo siglas e codigos.
    O texto original continua sendo usado na busca semantica/reranker.
    """
    texto = (texto or "").casefold()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )
    return texto


def tokenizar(texto: str) -> list[str]:
    """
    Tokenizacao lexical tolerante a acentos.
    Mantem tokens alfanumericos como 'PPC', '2025', '2.3' (em partes)
    e siglas presentes em perguntas e documentos.
    """
    texto = normalizar_busca(texto)
    return re.findall(r"[a-z0-9]+", texto, flags=re.UNICODE)


def obter_metadado(metadata, campo, padrao=""):
    if not metadata:
        return padrao

    valor = metadata.get(campo)
    return padrao if valor is None else valor


def converter_numero(valor, padrao=0):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def metadados_item(identificador, documento, metadata):
    return {
        "id": identificador,
        "arquivo": obter_metadado(metadata, "arquivo"),
        "documento": obter_metadado(metadata, "documento"),
        "titulo": obter_metadado(metadata, "titulo"),
        "secao": obter_metadado(metadata, "secao"),
        "subsecao": obter_metadado(metadata, "subsecao"),
        "chunk_id": converter_numero(
            obter_metadado(metadata, "chunk_id", 0), 0
        ),
        "chunk": documento or "",
    }


# ============================================================
# CARREGAMENTO DO INDICE BM25
# ============================================================

print("Carregando chunks para o BM25...")

# Chroma pode paginar resultados quando a colecao e grande.
# Fazemos a leitura em lotes para construir o indice completo.
base_bm25 = []
offset = 0
lote_leitura = 1000

while True:
    dados = colecao.get(
        limit=lote_leitura,
        offset=offset,
        include=["documents", "metadatas"],
    )

    ids = dados.get("ids") or []
    documentos = dados.get("documents") or []
    metadados = dados.get("metadatas") or []

    if not ids:
        break

    for identificador, documento, metadata in zip(ids, documentos, metadados):
        if not documento:
            continue
        base_bm25.append(
            metadados_item(identificador, documento, metadata or {})
        )

    offset += len(ids)
    if len(ids) < lote_leitura:
        break

# O BM25 indexa o documento contextualizado guardado no Chroma.
corpus_tokenizado = [
    tokenizar(item["chunk"])
    for item in base_bm25
]

# Evita incluir documentos vazios no indice lexical.
indices_validos = [
    i for i, tokens in enumerate(corpus_tokenizado) if tokens
]
base_bm25 = [base_bm25[i] for i in indices_validos]
corpus_tokenizado = [corpus_tokenizado[i] for i in indices_validos]

modelo_bm25 = BM25Okapi(corpus_tokenizado) if corpus_tokenizado else None

print(f"Chunks carregados no BM25: {len(base_bm25)}")


# ============================================================
# BUSCA SEMANTICA
# ============================================================

def buscar_semantica(pergunta, top_k=TOP_K_SEMANTICO):
    inicio = perf_counter()

    total = colecao.count()
    if total == 0:
        return []

    top_k = max(1, min(top_k, total))
    texto_query = f"query: {pergunta.strip()}"

    emb_pergunta = modelo_embedding.encode(
        texto_query,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).tolist()

    resultado = colecao.query(
        query_embeddings=[emb_pergunta],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    candidatos = []
    documentos = (resultado.get("documents") or [[]])[0] or []
    metadados = (resultado.get("metadatas") or [[]])[0] or []
    distancias = (resultado.get("distances") or [[]])[0] or []
    ids = (resultado.get("ids") or [[]])[0] or []

    for identificador, documento, metadata, distancia in zip(
        ids, documentos, metadados, distancias
    ):
        item = metadados_item(identificador, documento, metadata or {})
        item["distancia"] = float(distancia)
        candidatos.append(item)

    print(f"Busca semantica: {perf_counter() - inicio:.2f}s")
    return candidatos


# ============================================================
# BUSCA LEXICAL — BM25
# ============================================================

def buscar_lexical(pergunta, top_k=TOP_K_LEXICAL):
    inicio = perf_counter()

    if modelo_bm25 is None or not base_bm25:
        return []

    tokens_pergunta = tokenizar(pergunta)
    if not tokens_pergunta:
        return []

    scores = modelo_bm25.get_scores(tokens_pergunta)
    indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )

    candidatos = []
    for indice in indices:
        score = float(scores[indice])
        if score <= 0:
            continue

        item = dict(base_bm25[indice])
        item["score_bm25"] = score
        candidatos.append(item)

        if len(candidatos) >= top_k:
            break

    print(f"Busca lexical: {perf_counter() - inicio:.2f}s")
    return candidatos


# ============================================================
# FUSAO RRF
# ============================================================

def combinar_resultados(
    resultados_semanticos,
    resultados_lexicais,
    k=RRF_K,
):
    inicio = perf_counter()
    combinados = {}

    fontes = [
        ("semantica", resultados_semanticos),
        ("lexical", resultados_lexicais),
    ]

    for origem, lista in fontes:
        for posicao, item in enumerate(lista, start=1):
            identificador = item["id"]

            if identificador not in combinados:
                combinados[identificador] = {
                    **item,
                    "score_fusao": 0.0,
                    "origens": [],
                }

            registro = combinados[identificador]
            registro["score_fusao"] += 1.0 / (k + posicao)

            if origem not in registro["origens"]:
                registro["origens"].append(origem)

            # Completa metadados caso o mesmo ID venha de outra lista.
            for chave, valor in item.items():
                if chave not in registro or registro[chave] in ("", None):
                    registro[chave] = valor

    ordenados = sorted(
        combinados.values(),
        key=lambda item: item["score_fusao"],
        reverse=True,
    )

    print(f"RRF: {perf_counter() - inicio:.2f}s")
    return ordenados


# ============================================================
# RERANKING
# ============================================================

def aplicar_reranking(pergunta, candidatos):
    if not candidatos:
        return []

    pares = [
        [pergunta, item["chunk"]]
        for item in candidatos
    ]

    scores = reranker.compute_score(
        pares,
        normalize=True,
    )

    # Algumas versoes retornam um escalar para um unico par.
    if isinstance(scores, (int, float)):
        scores = [scores]

    for item, score in zip(candidatos, scores):
        item["rerank"] = float(score)

    return sorted(
        candidatos,
        key=lambda item: item.get("rerank", float("-inf")),
        reverse=True,
    )


# ============================================================
# BUSCA HIBRIDA + RERANKING
# ============================================================

def buscar_contexto(
    pergunta,
    top_k=TOP_K_SEMANTICO,
    top_lexical=TOP_K_LEXICAL,
    top_final=TOP_FINAL_PADRAO,
    top_candidatos=TOP_CANDIDATOS_RRF,
):
    inicio = perf_counter()
    pergunta = (pergunta or "").strip()

    if not pergunta:
        return []

    # 1. Busca semantica.
    resultados_semanticos = buscar_semantica(
        pergunta,
        top_k=top_k,
    )

    # 2. Busca lexical.
    resultados_lexicais = buscar_lexical(
        pergunta,
        top_k=top_lexical,
    )

    # 3. Funde os rankings sem comparar diretamente suas escalas.
    candidatos = combinar_resultados(
        resultados_semanticos,
        resultados_lexicais,
    )

    if not candidatos:
        print(f"Nenhum candidato encontrado ({perf_counter() - inicio:.2f}s)")
        return []

    # Antes eram mantidos somente 7 candidatos. Agora preservamos
    # mais diversidade para o reranker avaliar.
    candidatos = candidatos[:max(1, top_candidatos)]

    # 4. Reranker recebe texto contextualizado do Chroma.
    candidatos = aplicar_reranking(pergunta, candidatos)

    resultado_final = candidatos[:max(1, top_final)]
    print(f"Tempo total da busca: {perf_counter() - inicio:.2f}s")

    return resultado_final


# ============================================================
# TESTE MANUAL OPCIONAL
# ============================================================

if __name__ == "__main__":
    while True:
        pergunta = input("\nPergunta para testar (ou 'sair'): ").strip()
        if pergunta.casefold() == "sair":
            break

        resultados = buscar_contexto(pergunta)
        if not resultados:
            print("Nenhum trecho relevante encontrado.")
            continue

        for posicao, item in enumerate(resultados, start=1):
            print("\n" + "=" * 80)
            print(
                f"{posicao}. arquivo={item.get('arquivo')} | "
                f"secao={item.get('secao')} | "
                f"subsecao={item.get('subsecao')}"
            )
            print(
                f"RRF={item.get('score_fusao', 0):.4f} | "
                f"rerank={item.get('rerank', 0):.4f} | "
                f"origens={item.get('origens', [])}"
            )
            print(item["chunk"])
