import os
from dotenv import load_dotenv
import google.generativeai as genai

from busca import buscar_contexto

# ==========================================
# CONFIGURAÇÃO
# ==========================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)

# ==========================================
# CHAT
# ==========================================

while True:

    pergunta = input(
        "\nPergunta ('sair' para encerrar): "
    )

    if pergunta.lower() == "sair":

        print("Encerrando...")
        break

    # Busca semântica
    chunks = buscar_contexto(
        pergunta
    )

    if len(chunks) == 0:

        print(
            "\nNenhum resultado encontrado.\n"
        )

        continue

    contexto = ""

    for item in chunks:

        contexto += f"""
ARQUIVO: {item['arquivo']}
TÍTULO: {item['titulo']}

{item['chunk']}

-----------------------------------
"""

    print("\nChunks utilizados:\n")

    for item in chunks:

        print(
            f"- {item['arquivo']} | {item['titulo']}"
        )

    prompt = f"""
Você é um assistente do IFRS Campus Restinga.

REGRAS:

- Responda APENAS com base no contexto fornecido.
- Nunca invente informações.
- Se a informação não estiver presente, diga:
  "Não encontrei essa informação nos documentos."
- Sempre que possível cite o documento utilizado.
- Seja objetivo e claro.

CONTEXTO:

{contexto}

PERGUNTA:

{pergunta}
"""

    try:

        resposta = model.generate_content(
            prompt
        )

        print("\nResposta:\n")

        print(
            resposta.text
        )

        print(
            "\n" + "=" * 60 + "\n"
        )

    except Exception as erro:

        print("\nErro:")

        print(erro)