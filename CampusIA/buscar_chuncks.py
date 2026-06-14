import json

from sentence_transformers import (
    SentenceTransformer,
    CrossEncoder
)

from sklearn.metrics.pairwise import cosine_similarity


print("Carregando modelo E5...")

model = SentenceTransformer(
    "intfloat/multilingual-e5-base"
)

print("Carregando reranker...")

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

print("Carregando base...")

with open(
    "base_conhecimento.json",
    "r",
    encoding="utf-8"
) as f:

    base = json.load(f)


while True:

    pergunta = input(
        "\nPergunta ('sair' para encerrar): "
    )

    if pergunta.lower() == "sair":
        break

    print("\nBuscando...")

    embedding_pergunta = model.encode(
        pergunta
    )

    resultados = []

    for item in base:

        similaridade = cosine_similarity(
            [embedding_pergunta],
            [item["embedding"]]
        )[0][0]

        resultados.append({

            "arquivo": item["arquivo"],

            "titulo": item.get(
                "titulo",
                ""
            ),

            "chunk": item["chunk"],

            "similaridade": float(
                similaridade
            )

        })

    resultados.sort(
        key=lambda x: x["similaridade"],
        reverse=True
    )

    top20 = resultados[:20]

    print(
        "\nAplicando reranking..."
    )

    pares = [

        (
            pergunta,
            item["chunk"]
        )

        for item in top20

    ]

    scores = reranker.predict(
        pares
    )

    for item, score in zip(
        top20,
        scores
    ):

        item["rerank_score"] = float(
            score
        )

    top20.sort(
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    top5 = top20[:5]

    print(
        "\nTop 5 após reranking:\n"
    )

    for resultado in top5:

        print("=" * 80)

        print(
            f"Arquivo: {resultado['arquivo']}"
        )

        print(
            f"Título: {resultado['titulo']}"
        )

        print(
            f"Score: {resultado['rerank_score']:.4f}"
        )

        print()

        print(
            resultado["chunk"][:1000]
        )

        print("\n")