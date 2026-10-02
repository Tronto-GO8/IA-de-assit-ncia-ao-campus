from FlagEmbedding import FlagReranker

# Carrega o modelo. Na primeira execução, ele será baixado.
reranker = FlagReranker(
    "BAAI/bge-reranker-v2-m3",
    use_fp16=False
)

pergunta = "Qual é a carga horária da disciplina de Programação?"

chunks = [
    "O curso possui atividades de acompanhamento pedagógico para os estudantes.",
    "A disciplina de Programação possui carga horária de 100 horas.",
    "O componente de Informática Instrumental aborda ferramentas digitais.",
]

pares = [
    [pergunta, chunk]
    for chunk in chunks
]

pontuacoes = reranker.compute_score(
    pares,
    normalize=True
)

resultados = sorted(
    zip(chunks, pontuacoes),
    key=lambda item: item[1],
    reverse=True
)

for texto, pontuacao in resultados:
    print(f"Pontuação: {pontuacao:.4f}")
    print(texto)
    print("-" * 60)