import os
import re

import chromadb

from sentence_transformers import SentenceTransformer

# ======================================================
# BANCO VETORIAL
# ======================================================

cliente = chromadb.PersistentClient(
    path="banco_vetorial"
)

colecao = cliente.get_or_create_collection(
    name="campusia"
)

# Limpa coleção antiga para evitar duplicações
try:
    cliente.delete_collection("campusia")
except:
    pass

colecao = cliente.get_or_create_collection(
    name="campusia"
)

# ======================================================
# LIMPEZA DOS TEXTOS
# ======================================================

def limpar_texto(texto):

    linhas_limpas = []

    for linha in texto.splitlines():

        linha = linha.strip()

        if not linha:
            continue

        # Remove números de página isolados
        if linha.isdigit():
            continue

        # Remove lixo comum dos PDFs
        if linha.lower() in [
            "fls",
            "rubrica",
            "sumário"
        ]:
            continue

        linhas_limpas.append(linha)

    texto = "\n".join(linhas_limpas)

    texto = re.sub(
        r"[ \t]+",
        " ",
        texto
    )

    return texto.strip()


# ======================================================
# CHUNKING POR SEÇÃO
# ======================================================

def criar_chunks_por_secao(texto):

    secoes = re.split(
        r'(?=\n\d+(?:\.\d+)*\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ])',
        texto
    )

    chunks = []

    for secao in secoes:

        secao = secao.strip()

        if len(secao) < 50:
            continue

        primeira_linha = secao.split("\n")[0]

        chunks.append({
            "titulo": primeira_linha,
            "texto": secao
        })

    return chunks


# ======================================================
# CHUNKING POR PARÁGRAFOS
# ======================================================

def criar_chunks_por_paragrafo(texto):

    paragrafos = texto.split("\n")

    chunks = []

    chunk_atual = ""

    for p in paragrafos:

        p = p.strip()

        if not p:
            continue

        if len(chunk_atual) + len(p) < 500:

            chunk_atual += p + "\n"

        else:

            chunks.append({
                "titulo": "",
                "texto": chunk_atual.strip()
            })

            chunk_atual = p + "\n"

    if chunk_atual:

        chunks.append({
            "titulo": "",
            "texto": chunk_atual.strip()
        })

    return chunks


# ======================================================
# ESCOLHA AUTOMÁTICA DO TIPO DE CHUNK
# ======================================================

def criar_chunks(texto):

    padrao = r'\d+(?:\.\d+)*\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]'

    secoes = re.findall(
        padrao,
        texto
    )

    if len(secoes) >= 5:

        print("→ Chunking por seção")

        return criar_chunks_por_secao(texto)

    print("→ Chunking por parágrafo")

    return criar_chunks_por_paragrafo(texto)


# ======================================================
# CARREGAR MODELO
# ======================================================

print("Carregando modelo...")

model = SentenceTransformer(
    "intfloat/multilingual-e5-base"
)

total_chunks = 0

# ======================================================
# PROCESSAR DOCUMENTOS
# ======================================================

for arquivo in os.listdir("documentos_em_txt"):

    if not arquivo.endswith(".txt"):
        continue

    caminho = os.path.join(
        "documentos_em_txt",
        arquivo
    )

    print(f"\nProcessando {arquivo}")

    with open(
        caminho,
        "r",
        encoding="utf-8"
    ) as f:

        texto = f.read()

    texto = limpar_texto(texto)

    chunks = criar_chunks(texto)

    print(
        f"Chunks gerados: {len(chunks)}"
    )

    for i, chunk in enumerate(chunks):

        texto_para_embedding = f"""
Documento: {arquivo}

Título: {chunk['titulo']}

Conteúdo:
{chunk['texto']}
"""

        embedding = model.encode(
            texto_para_embedding
        ).tolist()

        colecao.add(

            ids=[
                f"{arquivo}_{i}"
            ],

            embeddings=[
                embedding
            ],

            documents=[
                chunk["texto"]
            ],

            metadatas=[{
                "arquivo": arquivo,
                "titulo": chunk["titulo"],
                "chunk_id": i
            }]
        )

        total_chunks += 1

# ======================================================
# RESUMO FINAL
# ======================================================

print("\n" + "=" * 60)

print(
    f"Total de chunks armazenados: {total_chunks}"
)

print(
    f"Quantidade no banco: {colecao.count()}"
)

print("\nBanco vetorial criado com sucesso!")

print(
    "\nArquivos armazenados em: ./banco_vetorial"
)

print("=" * 60)