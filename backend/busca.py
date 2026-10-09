import os
import re

import chromadb

from sentence_transformers import SentenceTransformer
from FlagEmbedding import FlagReranker
from rank_bm25 import BM25Okapi
# temp
from time import perf_counter
# ============================================================
# MODELOS
# ============================================================

print("Carregando modelo de embeddings...")

modelo_embedding = SentenceTransformer(
    "intfloat/multilingual-e5-base"
)

print("Carregando reranker...")

reranker = FlagReranker(
    "BAAI/bge-reranker-v2-m3",
    use_fp16=False
)

# ============================================================
# CHROMADB
# ============================================================

print("Conectando ao banco vetorial...")

cliente = chromadb.PersistentClient(
    path=os.getenv(
        "CHROMA_PATH",
        "banco_vetorial"
    )
)

colecao = cliente.get_collection(
    name="campusia"
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def tokenizar(texto):
    """
    Divide o texto em termos para o BM25.
    Mantém palavras acentuadas e números.
    """

    return re.findall(
        r"\w+",
        texto.lower(),
        flags=re.UNICODE
    )


def obter_metadado(metadata, campo, padrao=""):
    """
    Evita erros quando um metadado não existe
    ou está com valor None.
    """

    if not metadata:
        return padrao

    valor = metadata.get(campo)

    if valor is None:
        return padrao

    return valor


# ============================================================
# CARREGAMENTO DO ÍNDICE BM25
# ============================================================

print("Carregando chunks para o BM25...")

dados_bm25 = colecao.get(
    include=[
        "documents",
        "metadatas"
    ]
)

documentos_bm25 = dados_bm25["documents"] or []
metadados_bm25 = dados_bm25["metadatas"] or []
ids_bm25 = dados_bm25["ids"] or []

# Guarda os dados de cada chunk.
base_bm25 = []

for identificador, documento, metadata in zip(
    ids_bm25,
    documentos_bm25,
    metadados_bm25
):
    if not documento:
        continue

    base_bm25.append({
        "id": identificador,
        "arquivo": obter_metadado(
            metadata, "arquivo"
        ),
        "secao": obter_metadado(
            metadata, "secao"
        ),
        "subsecao": obter_metadado(
            metadata, "subsecao"
        ),
        "chunk_id": obter_metadado(
            metadata, "chunk_id", 0
        ),
        "chunk": documento
    })


# O BM25 precisa de uma lista de tokens para cada chunk.
corpus_tokenizado = [
    tokenizar(item["chunk"])
    for item in base_bm25
]

if corpus_tokenizado:
    modelo_bm25 = BM25Okapi(corpus_tokenizado)
else:
    modelo_bm25 = None

print(f"Chunks carregados no BM25: {len(base_bm25)}")


# ============================================================
# BUSCA SEMÂNTICA
# ============================================================


    


def buscar_semantica(pergunta, top_k=20):
    t0 = perf_counter()

    texto_query = f"query: {pergunta}"

    emb_pergunta = modelo_embedding.encode(
        texto_query,
        normalize_embeddings=True
    ).tolist()

    resultado = colecao.query(
        query_embeddings=[emb_pergunta],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    candidatos = []

    documentos = resultado["documents"][0] or []
    metadados = resultado["metadatas"][0] or []
    distancias = resultado["distances"][0] or []
    ids = resultado["ids"][0] or []

    for identificador, documento, metadata, distancia in zip(
        ids,
        documentos,
        metadados,
        distancias
    ):
        candidatos.append({
            "id": identificador,
            "arquivo": obter_metadado(
                metadata, "arquivo"
            ),
            "secao": obter_metadado(
                metadata, "secao"
            ),
            "subsecao": obter_metadado(
                metadata, "subsecao"
            ),
            "chunk_id": obter_metadado(
                metadata, "chunk_id", 0
            ),
            "chunk": documento,
            "distancia": float(distancia)
        })
    print(f"Busca semântica: {perf_counter() - t0:.2f}s")

    return candidatos


# ============================================================
# BUSCA LEXICAL — BM25
# ============================================================

def buscar_lexical(pergunta, top_k=20):
    t0 = perf_counter()

    if modelo_bm25 is None or not base_bm25:
        return []

    tokens_pergunta = tokenizar(pergunta)

    if not tokens_pergunta:
        return []

    scores = modelo_bm25.get_scores(
        tokens_pergunta
    )

    # Ordena os índices do maior para o menor score.
    indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )

    candidatos = []

    for indice in indices[:top_k]:

        # Não inclui resultados sem correspondência útil.
        if scores[indice] <= 0:
            continue

        item = base_bm25[indice]

        candidatos.append({
            **item,
            "score_bm25": float(scores[indice])
        })
    print(f"Busca lexical: {perf_counter() - t0:.2f}s")

    return candidatos


# ============================================================
# FUSÃO DOS RESULTADOS
# ============================================================

def combinar_resultados(
    resultados_semanticos,
    resultados_lexicais,
    k=60
):
    t0 = perf_counter()
    """
    Combina os rankings usando Reciprocal Rank Fusion (RRF).

    O RRF combina as posições dos resultados, sem precisar
    comparar diretamente a escala de distância do Chroma
    com a escala de pontuação do BM25.
    """

    combinados = {}

    listas = [
        resultados_semanticos,
        resultados_lexicais
    ]

    for lista in listas:

        for posicao, item in enumerate(lista, start=1):

            identificador = item["id"]

            if identificador not in combinados:
                combinados[identificador] = {
                    **item,
                    "score_fusao": 0.0,
                    "origens": []
                }

            registro = combinados[identificador]

            registro["score_fusao"] += (
                1 / (k + posicao)
            )

            if lista is resultados_semanticos:
                origem = "semantica"
            else:
                origem = "lexical"

            if origem not in registro["origens"]:
                registro["origens"].append(origem)

            # Preserva informações das duas buscas.
            for chave, valor in item.items():
                if chave not in registro:
                    registro[chave] = valor
    
    print(f"RRF: {perf_counter() - t0:.2f}s")

    return sorted(
        combinados.values(),
        key=lambda item: item["score_fusao"],
        reverse=True
    )


# ============================================================
# BUSCA HÍBRIDA + RERANKING
# ============================================================

def buscar_contexto(
    pergunta,
    top_k=20,
    top_lexical=20,
    top_final=5
):

    inicio = perf_counter()

    # --------------------------------------------------------
    # 1. BUSCA SEMÂNTICA
    # --------------------------------------------------------

    resultados_semanticos = buscar_semantica(
        pergunta,
        top_k=top_k
    )

    # --------------------------------------------------------
    # 2. BUSCA LEXICAL
    # --------------------------------------------------------

    resultados_lexicais = buscar_lexical(
        pergunta,
        top_k=top_lexical
    )

    # --------------------------------------------------------
    # 3. FUSÃO DOS RESULTADOS
    # --------------------------------------------------------

    candidatos = combinar_resultados(
        resultados_semanticos,
        resultados_lexicais
    )

    if not candidatos:
        return []

    candidatos = candidatos[:7]

    # --------------------------------------------------------
    # 4. RERANKING
    # --------------------------------------------------------

    t0 = perf_counter()
    pares = [
        [pergunta, item["chunk"]]
        for item in candidatos
    ]

    scores_rerank = reranker.compute_score(
        pares,
        normalize=True
    )

    # Garante que o resultado possa ser percorrido
    # mesmo se houver apenas um candidato.
    if isinstance(scores_rerank, (int, float)):
        scores_rerank = [scores_rerank]

    for item, score in zip(candidatos, scores_rerank):
        item["rerank"] = float(score)

    # --------------------------------------------------------
    # 5. ORDENA PELO RERANKER
    # --------------------------------------------------------

    candidatos.sort(
        key=lambda item: item["rerank"],
        reverse=True
    )

    print(f"Reranker: {perf_counter() - t0:.2f}s")

    # --------------------------------------------------------
    # 6. RETORNA OS MELHORES CHUNKS
    # --------------------------------------------------------

    return candidatos[:top_final]

    print(f"Tempo total da busca: {perf_counter() - inicio:.2f}s")