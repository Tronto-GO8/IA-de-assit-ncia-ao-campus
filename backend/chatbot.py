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

Responda APENAS com base no contexto fornecido.
Nunca invente, suponha ou complete informações que não estejam presentes nos documentos.
Se a informação solicitada não estiver presente no contexto, responda exatamente:"Não encontrei essa informação nos documentos."
Se apenas parte da pergunta puder ser respondida com base no contexto, responda somente a parte que estiver comprovada pelos documentos.
Responda de maneira natural, clara e objetiva, como em uma conversa.
Não mencione que você é uma IA, modelo de linguagem ou sistema de RAG, a menos que isso seja perguntado.
Não apresente informações como fatos quando elas não estiverem confirmadas pelos documentos.
Ao final da resposta, cite as fontes utilizadas.
Ao citar as fontes, informe apenas as informações necessárias para identificar a fonte, sem mencionar o formato do arquivo.
Não invente fontes, títulos, páginas ou referências.
Se não houver uma fonte disponível para determinada informação, não crie uma referência.
Priorize respostas curtas e diretas, mas forneça detalhes suficientes para responder à dúvida do usuário.
Caso a pergunta não possa ser respondida com segurança utilizando o contexto fornecido, utilize a resposta padrão indicada acima.

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
    
        retorno = resposta.text
  
    except Exception as erro:
        retorno = f"Erro: {erro}" 
       
    finally:
        return retorno, prompt
  