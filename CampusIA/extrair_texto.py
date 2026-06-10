import fitz
import os

PASTA_PDFS = "documentos"
PASTA_TXT = "textos"

os.makedirs(PASTA_TXT, exist_ok=True)

for arquivo in os.listdir(PASTA_PDFS):

    if not arquivo.lower().endswith(".pdf"):
        continue

    caminho_pdf = os.path.join(PASTA_PDFS, arquivo)

    print(f"Processando: {arquivo}")

    pdf = fitz.open(caminho_pdf)

    texto_completo = ""

    for pagina in pdf:
        texto_completo += pagina.get_text()
        texto_completo += "\n"

    nome_txt = arquivo[:-4] + ".txt"

    caminho_txt = os.path.join(PASTA_TXT, nome_txt)

    with open(caminho_txt, "w", encoding="utf-8") as f:
        f.write(texto_completo)

    print(f"Salvo: {nome_txt}")

print("Concluído!")