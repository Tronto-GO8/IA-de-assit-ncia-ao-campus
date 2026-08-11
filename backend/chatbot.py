import os
from dotenv import load_dotenv
from google import genai

from busca import buscar_contexto

# ==========================================
# CONFIGURAÇÃO
# ==========================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(
    api_key=api_key
)

# ==========================================
# CHAT
# ==========================================

def responder(pergunta, historico=None):

    if historico is None:
        historico = []
    
    texto_historico = ""

    for mensagem in historico:

        texto_historico += (
            f"{mensagem.autor}: "
            f"{mensagem.texto}\n"
        )
    

    # Busca semântica
    chunks = buscar_contexto(
        pergunta
    )

    if len(chunks) == 0:
        return "Nenhum resultado encontrado."
        

    contexto = ""

    for item in chunks:

        contexto += f"""
ARQUIVO: {item['arquivo']}
TÍTULO: {item['titulo']}

{item['chunk']}

-----------------------------------
"""

    prompt = f"""
Você é um assistente do IFRS Campus Restinga.

REGRAS:

- Responda APENAS com base no contexto fornecido e so o que foi perguntado.
- Nunca invente informações.
- Se a informação não estiver presente, diga:
- "Não encontrei essa informação nos documentos."
- Seja objetivo e claro.
- Sempre que possível cite o documento utilizado.

HISTÓRICO DA CONVERSA:

{texto_historico}

CONTEXTO DOS DOCUMENTOS:

{contexto}

PERGUNTA ATUAL:

{pergunta}
"""

    try:

        resposta = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt
        )
     
        return resposta.text
    

    except Exception as erro:

        return f"Erro: {erro}"