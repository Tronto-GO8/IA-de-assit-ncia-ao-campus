import chromadb

from sentence_transformers import (
    SentenceTransformer,
    CrossEncoder
)


# ============================================================
# MODELOS
# ============================================================

print("Carregando modelo de embeddings...")

modelo_embedding = SentenceTransformer(
    "intfloat/multilingual-e5-base"
)

print("Carregando reranker...")

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


# ============================================================
# CHROMADB
# ============================================================

print("Conectando ao banco vetorial...")

cliente = chromadb.PersistentClient(
    path="banco_vetorial"
)

colecao = cliente.get_collection(
    name="campusia"
)


# ============================================================
# BUSCA
# ============================================================

def buscar_contexto(
    pergunta,
    top_k=20,
    top_final=5
):

    # --------------------------------------------------------
    # 1. EMBEDDING DA PERGUNTA
    # --------------------------------------------------------

    texto_query = f"query: {pergunta}"

    emb_pergunta = modelo_embedding.encode(
        texto_query,
        normalize_embeddings=True
    ).tolist()


    # --------------------------------------------------------
    # 2. BUSCA INICIAL NO CHROMADB
    # --------------------------------------------------------

    resultado = colecao.query(

        query_embeddings=[
            emb_pergunta
        ],

        n_results=top_k,

        include=[
            "documents",
            "metadatas",
            "distances"
        ]

    )


    # --------------------------------------------------------
    # 3. ORGANIZA OS CANDIDATOS
    # --------------------------------------------------------

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

            "arquivo": metadata.get(
                "arquivo",
                ""
            ),

            "secao": metadata.get(
                "secao",
                ""
            ),

            "subsecao": metadata.get(
                "subsecao",
                ""
            ),

            "chunk_id": metadata.get(
                "chunk_id",
                0
            ),

            "chunk": documento,

            "score": float(distancia)

        })


    # --------------------------------------------------------
    # 4. RERANKING
    # --------------------------------------------------------

    pares = [

        (
            pergunta,
            item["chunk"]
        )

        for item in candidatos

    ]


    if not pares:
        return []


    scores_rerank = reranker.predict(
        pares
    )


    for item, score in zip(
        candidatos,
        scores_rerank
    ):

        item["rerank"] = float(
            score
        )


    # --------------------------------------------------------
    # 5. ORDENA PELO RERANKER
    # --------------------------------------------------------

    candidatos.sort(
        key=lambda x: x["rerank"],
        reverse=True
    )


    # --------------------------------------------------------
    # 6. RETORNA OS MELHORES
    # --------------------------------------------------------

    return candidatos[:top_final]