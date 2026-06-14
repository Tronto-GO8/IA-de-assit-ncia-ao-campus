import json

from sentence_transformers import (
    SentenceTransformer,
    CrossEncoder
)

from sklearn.metrics.pairwise import cosine_similarity

print("Carregando embeddings...")

modelo_embedding = SentenceTransformer(
    "intfloat/multilingual-e5-base"
)

print("Carregando reranker...")

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

with open(
    "base_conhecimento.json",
    "r",
    encoding="utf-8"
) as f:

    BASE = json.load(f)


def buscar_contexto(
    pergunta,
    top_k=20,
    top_final=5
):

    emb_pergunta = modelo_embedding.encode(
        pergunta
    )

    resultados = []

    for item in BASE:

        score = cosine_similarity(
            [emb_pergunta],
            [item["embedding"]]
        )[0][0]

        resultados.append({
            **item,
            "score": float(score)
        })

    resultados.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    candidatos = resultados[:top_k]

    pares = [
        (pergunta, item["chunk"])
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