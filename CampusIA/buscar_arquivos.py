import os

PASTA_TEXTOS = "textos"

pergunta = input("Pergunta: ").lower()

print("\nDocumentos relacionados:\n")

for arquivo in os.listdir(PASTA_TEXTOS):

    if not arquivo.endswith(".txt"):
        continue

    caminho = os.path.join(PASTA_TEXTOS, arquivo)

    with open(caminho, "r", encoding="utf-8") as f:
        conteudo = f.read().lower()

    if pergunta in conteudo:
        print(f"- {arquivo}")
        