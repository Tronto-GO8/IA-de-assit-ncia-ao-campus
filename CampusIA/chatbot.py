import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)

print(api_key)
"""
# ==========================================
# CONFIGURAÇÃO
# ==========================================

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash")

PASTA_TEXTOS = "textos"

# ==========================================
# CARREGAR DOCUMENTOS
# ==========================================

print("Carregando documentos...")

documentos = {}

for arquivo in os.listdir(PASTA_TEXTOS):

    if arquivo.endswith(".txt"):

        caminho = os.path.join(PASTA_TEXTOS, arquivo)

        with open(caminho, "r", encoding="utf-8") as f:
            documentos[arquivo] = f.read()

print(f"{len(documentos)} documentos carregados.\n")

# ==========================================
# BUSCA SIMPLES
# ==========================================

def buscar_documentos(pergunta, documentos, limite=3):

    palavras = pergunta.lower().split()

    resultados = []

    for nome, texto in documentos.items():

        texto_lower = texto.lower()

        pontuacao = 0

        for palavra in palavras:

            if len(palavra) > 2 and palavra in texto_lower:
                pontuacao += 1

        if pontuacao > 0:
            resultados.append((pontuacao, nome))

    resultados.sort(reverse=True)

    return [nome for pontuacao, nome in resultados[:limite]]

# ==========================================
# CHAT
# ==========================================

while True:

    pergunta = input("Pergunta ('sair' para encerrar): ")

    if pergunta.lower() == "sair":
        print("Encerrando...")
        break

    docs_relevantes = buscar_documentos(
        pergunta,
        documentos
    )

    if not docs_relevantes:

        print("\nNenhum documento relacionado encontrado.\n")
        continue

    contexto = ""

    for nome in docs_relevantes:

        contexto += f"\n\n===== DOCUMENTO: {nome} =====\n"
        contexto += documentos[nome]

    print("\nDocumentos utilizados:")

    for doc in docs_relevantes:
        print("-", doc)

    prompt = f""
Você é um assistente do Instituto Federal.

REGRAS:
- Use APENAS as informações dos documentos fornecidos.
- Nunca invente informações.
- Se a resposta não estiver nos documentos, diga claramente.
- Cite o documento quando possível.

DOCUMENTOS:

{contexto}

PERGUNTA:

{pergunta}
""

    try:

        resposta = model.generate_content(prompt)

        print("\nResposta:\n")
        print(resposta.text)
        print("\n" + "=" * 60 + "\n")

    except Exception as erro:

        print("\nErro:")
        print(erro)

        """