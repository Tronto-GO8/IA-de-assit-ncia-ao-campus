import chromadb

from sentence_transformers import (
    SentenceTransformer,
    CrossEncoder
)

print("Carregando modelo de embeddings...")

modelo_embedding = SentenceTransformer(
    "intfloat/multilingual-e5-base"
)

print("Carregando reranker...")

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

print("Conectando ao banco vetorial...")

cliente = chromadb.PersistentClient(
    path="banco_vetorial"
)

colecao = cliente.get_collection(
    "campusia"
)


def buscar_contexto(
    pergunta,
    top_k=20,
    top_final=5
):

    # Embedding da pergunta

    emb_pergunta = modelo_embedding.encode(
        pergunta
    ).tolist()

    # Busca inicial no banco vetorial

    resultado = colecao.query(

        query_embeddings=[
            emb_pergunta
        ],

        n_results=top_k

    )

    candidatos = []

    documentos = resultado["documents"][0]
    metadados = resultado["metadatas"][0]
    distancias = resultado["distances"][0]

    for documento, metadata, distancia in zip(
        documentos,
        metadados,
        distancias
    ):

        candidatos.append({

            "arquivo": metadata["arquivo"],

            "titulo": metadata["titulo"],

            "chunk_id": metadata["chunk_id"],

            "chunk": documento,

            "score": float(distancia)

        })

    # Reranking

    pares = [

        (
            pergunta,
            item["chunk"]
        )

        for item in candidatos

    ]

    scores_rerank = reranker.predict(
        pares
    )

    for item, score in zip(
        candidatos,
        scores_rerank
    ):

        item["rerank"] = float(score)

    candidatos.sort(
        key=lambda x: x["rerank"],
        reverse=True
    )

    return candidatos[:top_final]