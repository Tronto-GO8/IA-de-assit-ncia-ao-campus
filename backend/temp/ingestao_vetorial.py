import os
import re

import chromadb

from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_TEXTOS = "textos"

CAMINHO_BANCO = "banco_vetorial"

NOME_COLECAO = "campusia"

MODELO_EMBEDDING = (
    "intfloat/multilingual-e5-base"
)

TAMANHO_CHUNK = 600

OVERLAP = 120

BATCH_SIZE = 32


# ============================================================
# CHROMADB
# ============================================================

cliente = chromadb.PersistentClient(
    path=CAMINHO_BANCO
)


# Apaga a coleção antiga
try:

    cliente.delete_collection(
        NOME_COLECAO
    )

except Exception:
    pass


colecao = cliente.get_or_create_collection(
    name=NOME_COLECAO,
    metadata={
        "hnsw:space": "cosine"
    }
)


# ============================================================
# LIMPEZA
# ============================================================

def limpar_texto(texto):

    linhas = []

    for linha in texto.splitlines():

        linha = linha.strip()

        if not linha:
            linhas.append("")
            continue

        # Remove páginas
        if linha.isdigit():
            continue

        # Remove elementos conhecidos de PDF
        if linha.lower() in [
            "fls",
            "rubrica",
            "sumário",
            "pagina",
            "página"
        ]:
            continue

        linhas.append(linha)

    texto = "\n".join(linhas)

    # Espaços duplicados
    texto = re.sub(
        r"[ \t]+",
        " ",
        texto
    )

    # Quebras excessivas
    texto = re.sub(
        r"\n{3,}",
        "\n\n",
        texto
    )

    return texto.strip()


# ============================================================
# DETECÇÃO DE TÍTULOS
# ============================================================

def eh_titulo_secao(linha):

    linha = linha.strip()

    if not linha:
        return False

    # Exemplos:
    #
    # 1. INTRODUÇÃO
    # 2. METODOLOGIA
    # 3. RESULTADOS
    #
    padrao = r"^\d+(?:\.\d+)*\.?\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ0-9]"

    if re.match(
        padrao,
        linha
    ):
        return True

    return False


# ============================================================
# DETECÇÃO DE SUBTÍTULOS
# ============================================================

def eh_subtitulo(linha):

    linha = linha.strip()

    if not linha:
        return False

    # Exemplos:
    #
    # Carga horária
    # Responsabilidades
    # Requisitos
    #
    # Evitamos considerar frases muito longas
    if len(linha) > 100:
        return False

    # Não considerar frases terminadas em pontuação
    if linha.endswith(
        (".", ",", ";", ":")
    ):
        return False

    palavras = linha.split()

    if len(palavras) > 12:
        return False

    # Se estiver completamente em maiúsculas
    if linha.upper() == linha:
        return True

    # Alguns marcadores comuns
    marcadores = [
        "requisitos",
        "etapas",
        "responsabilidades",
        "objetivos",
        "atividades",
        "carga horária",
        "carga horaria",
        "documentação",
        "documentacao",
        "considerações finais",
        "consideracoes finais"
    ]

    if linha.lower() in marcadores:
        return True

    return False


# ============================================================
# ESTRUTURA DO DOCUMENTO
# ============================================================

def estruturar_documento(texto):

    linhas = texto.splitlines()

    partes = []

    secao_atual = ""

    subsecao_atual = ""

    bloco_atual = []

    def salvar_bloco():

        nonlocal bloco_atual

        if not bloco_atual:
            return

        conteudo = "\n".join(
            bloco_atual
        ).strip()

        if len(conteudo) >= 30:

            partes.append({
                "secao": secao_atual,
                "subsecao": subsecao_atual,
                "texto": conteudo
            })

        bloco_atual = []

    for linha in linhas:

        linha = linha.strip()

        if not linha:
            continue

        # Nova seção
        if eh_titulo_secao(linha):

            salvar_bloco()

            secao_atual = linha
            subsecao_atual = ""

            continue

        # Novo subtítulo
        if eh_subtitulo(linha):

            salvar_bloco()

            subsecao_atual = linha

            continue

        bloco_atual.append(
            linha
        )

    salvar_bloco()

    return partes


# ============================================================
# CHUNKING RECURSIVO
# ============================================================

def dividir_texto(texto):

    if len(texto) <= TAMANHO_CHUNK:
        return [texto]

    # Primeiro tentamos parágrafos
    paragrafos = re.split(
        r"\n\s*\n",
        texto
    )

    paragrafos = [
        p.strip()
        for p in paragrafos
        if p.strip()
    ]

    chunks = []

    chunk_atual = ""

    for paragrafo in paragrafos:

        # Se o parágrafo sozinho já é grande
        if len(paragrafo) > TAMANHO_CHUNK:

            # Salva o que estava acumulado
            if chunk_atual:
                chunks.append(
                    chunk_atual.strip()
                )

                chunk_atual = ""

            # Divide por frases
            frases = re.split(
                r"(?<=[.!?])\s+",
                paragrafo
            )

            subchunk = ""

            for frase in frases:

                if not frase:
                    continue

                candidato = (
                    subchunk
                    + " "
                    + frase
                ).strip()

                if len(candidato) <= TAMANHO_CHUNK:

                    subchunk = candidato

                else:

                    if subchunk:
                        chunks.append(
                            subchunk.strip()
                        )

                    subchunk = frase

            if subchunk:
                chunks.append(
                    subchunk.strip()
                )

            continue

        candidato = (
            chunk_atual
            + "\n\n"
            + paragrafo
        ).strip()

        if len(candidato) <= TAMANHO_CHUNK:

            chunk_atual = candidato

        else:

            if chunk_atual:
                chunks.append(
                    chunk_atual.strip()
                )

            chunk_atual = paragrafo

    if chunk_atual:
        chunks.append(
            chunk_atual.strip()
        )

    return chunks


# ============================================================
# OVERLAP
# ============================================================

def adicionar_overlap(chunks):

    if not chunks:
        return []

    resultado = []

    for i, chunk in enumerate(chunks):

        if i == 0:

            resultado.append(
                chunk
            )

            continue

        anterior = chunks[i - 1]

        # Últimos caracteres do chunk anterior
        overlap = anterior[
            -OVERLAP:
        ]

        novo_chunk = (
            overlap
            + "\n"
            + chunk
        )

        resultado.append(
            novo_chunk
        )

    return resultado


# ============================================================
# CRIAÇÃO DOS CHUNKS
# ============================================================

def criar_chunks(texto):

    estrutura = estruturar_documento(
        texto
    )

    # Caso o documento tenha estrutura
    if estrutura:

        chunks_finais = []

        for parte in estrutura:

            chunks = dividir_texto(
                parte["texto"]
            )

            chunks = adicionar_overlap(
                chunks
            )

            for chunk in chunks:

                chunks_finais.append({
                    "secao": parte["secao"],
                    "subsecao": parte["subsecao"],
                    "texto": chunk
                })

        return chunks_finais

    # Fallback:
    # documento sem estrutura clara

    chunks = dividir_texto(
        texto
    )

    chunks = adicionar_overlap(
        chunks
    )

    return [
        {
            "secao": "",
            "subsecao": "",
            "texto": chunk
        }
        for chunk in chunks
    ]


# ============================================================
# MODELO
# ============================================================

print(
    "\nCarregando modelo E5..."
)

model = SentenceTransformer(
    MODELO_EMBEDDING
)

print(
    "Modelo carregado!"
)


# ============================================================
# PROCESSAMENTO
# ============================================================

todos_ids = []
todos_embeddings = []
todos_documents = []
todos_metadatas = []

total_chunks = 0


arquivos = os.listdir(
    PASTA_TEXTOS
)


for arquivo in arquivos:

    if not arquivo.lower().endswith(
        ".txt"
    ):
        continue

    caminho = os.path.join(
        PASTA_TEXTOS,
        arquivo
    )

    print(
        f"\nProcessando: {arquivo}"
    )

    with open(
        caminho,
        "r",
        encoding="utf-8"
    ) as f:

        texto = f.read()

    texto = limpar_texto(
        texto
    )

    if not texto:
        continue

    chunks = criar_chunks(
        texto
    )

    print(
        f"Chunks encontrados: {len(chunks)}"
    )

    # ========================================================
    # PREPARA TEXTOS PARA EMBEDDING
    # ========================================================

    textos_embedding = []

    for chunk in chunks:

        texto_embedding = (
            f"passage: "
            f"Documento: {arquivo}\n"
            f"Seção: {chunk['secao']}\n"
            f"Subseção: {chunk['subsecao']}\n\n"
            f"{chunk['texto']}"
        )

        textos_embedding.append(
            texto_embedding
        )

    # ========================================================
    # EMBEDDINGS EM LOTE
    # ========================================================

    embeddings = model.encode(
        textos_embedding,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    # ========================================================
    # PREPARA PARA O CHROMA
    # ========================================================

    for i, chunk in enumerate(
        chunks
    ):

        id_chunk = (
            f"{arquivo}_{i}"
        )

        todos_ids.append(
            id_chunk
        )

        todos_embeddings.append(
            embeddings[i].tolist()
        )

        # Texto que será recuperado
        # posteriormente pelo RAG
        todos_documents.append(
            chunk["texto"]
        )

        todos_metadatas.append({

            "arquivo": arquivo,

            "chunk_id": i,

            "secao": chunk["secao"],

            "subsecao": chunk["subsecao"]

        })

        total_chunks += 1


# ============================================================
# INSERÇÃO EM LOTE NO CHROMA
# ============================================================

print(
    "\nInserindo chunks no ChromaDB..."
)


TAMANHO_LOTE_CHROMA = 100


for inicio in range(
    0,
    len(todos_ids),
    TAMANHO_LOTE_CHROMA
):

    fim = (
        inicio
        + TAMANHO_LOTE_CHROMA
    )

    colecao.add(

        ids=todos_ids[
            inicio:fim
        ],

        embeddings=todos_embeddings[
            inicio:fim
        ],

        documents=todos_documents[
            inicio:fim
        ],

        metadatas=todos_metadatas[
            inicio:fim
        ]
    )


# ============================================================
# RESULTADO
# ============================================================

print(
    "\n"
    + "=" * 60
)

print(
    f"Total de chunks: {total_chunks}"
)

print(
    f"Chunks no ChromaDB: "
    f"{colecao.count()}"
)

print(
    "=" * 60
)

print(
    "\nBanco vetorial criado com sucesso!"
)