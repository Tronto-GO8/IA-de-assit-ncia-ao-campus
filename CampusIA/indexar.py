import os
import json
import re

from sentence_transformers import SentenceTransformer


# limpa o lixo que os espaços inuteis que vem dos PDFs 


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

    # Remove espaços duplicados mas preserva quebras de linha
    texto = re.sub(r"[ \t]+", " ", texto)

    return texto.strip()




# criar chucks por paragráfos para os documentos mais organizados por sessoes


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


# criar chucks por quantidade de texto (500) para os documentos menos organizados


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


# base de escolha de formato de chunk

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


print("Carregando modelo...")

model = SentenceTransformer(
    "intfloat/multilingual-e5-base"
)

base_conhecimento = []

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
        )

        base_conhecimento.append({

            "arquivo": arquivo,

            "chunk_id": i,

            "titulo": chunk["titulo"],

            "chunk": chunk["texto"],

            "embedding": embedding.tolist()

        })

print(
    f"\nTotal de chunks: {len(base_conhecimento)}"
)

with open(
    "base_conhecimento.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        base_conhecimento,
        f,
        ensure_ascii=False
    )

print("\nBase salva!")

print("\nPrimeiros chunks gerados:\n")

for item in base_conhecimento[:3]:

    print("=" * 80)

    print(
        f"Arquivo: {item['arquivo']}"
    )

    print(
        f"Chunk ID: {item['chunk_id']}"
    )

    print(
        f"Título: {item['titulo']}"
    )

    print()

    print(
        item["chunk"][:500]
    )

    print()