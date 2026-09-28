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


    # ======================================
    # HISTÓRICO
    # ======================================

    texto_historico = ""

    for mensagem in historico:

        texto_historico += (
            f"{mensagem.autor}: "
            f"{mensagem.texto}\n"
        )


    # ======================================
    # BUSCA SEMÂNTICA
    # ======================================

    chunks = buscar_contexto(
        pergunta
    )


    if len(chunks) == 0:

        return (
            "Não encontrei essa informação "
            "nos documentos."
        )


    # ======================================
    # CONTEXTO
    # ======================================

    contexto = ""

    for item in chunks:

        contexto += f"""
ARQUIVO: {item['arquivo']}
SEÇÃO: {item.get('secao', '')}
SUBSEÇÃO: {item.get('subsecao', '')}

{item['chunk']}

-----------------------------------
"""


    # ======================================
    # PROMPT
    # ======================================

    prompt = f"""
Você é um assistente do IFRS Campus Restinga.

Sua função é responder perguntas dos usuários
utilizando exclusivamente as informações presentes
no contexto dos documentos fornecido abaixo.

REGRAS:

1. Responda APENAS com base no contexto fornecido.

2. Nunca invente, suponha ou complete informações
que não estejam presentes nos documentos.

3. Se a informação solicitada não estiver presente
no contexto, responda exatamente:

"Não encontrei essa informação nos documentos."

4. Se apenas parte da pergunta puder ser respondida
com segurança utilizando o contexto, responda
somente a parte que estiver comprovada pelos documentos.

5. Responda de maneira natural, clara e objetiva.

6. Não mencione que você é uma IA, modelo de linguagem
ou sistema de RAG, a menos que isso seja perguntado.

7. Não apresente informações como fatos quando elas
não estiverem confirmadas pelos documentos.

8. Ao final da resposta, cite as fontes utilizadas.

9. Ao citar uma fonte, informe o nome do documento
e, quando disponível, a seção ou subseção relacionada.

10. Não invente fontes, títulos, páginas ou referências.

11. Não mencione o formato do arquivo nas citações.
Por exemplo, não escreva ".pdf", ".docx" etc.

12. Se uma informação não possuir uma fonte disponível
no contexto, não crie uma referência para ela.

13. Priorize respostas curtas e diretas, mas forneça
detalhes suficientes para responder à dúvida.

14. Caso a pergunta não possa ser respondida com
segurança utilizando o contexto fornecido, utilize
a resposta padrão:

"Não encontrei essa informação nos documentos."


HISTÓRICO DA CONVERSA:

{texto_historico}


CONTEXTO DOS DOCUMENTOS:

{contexto}


PERGUNTA ATUAL:

{pergunta}
"""


    # ======================================
    # GEMINI
    # ======================================

    try:

        resposta = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt
        )

        retorno = resposta.text

        return retorno, prompt


    except Exception as erro:

        print(
            f"Erro ao gerar resposta: {erro}"
        )

        return (
            "Ocorreu um erro ao gerar a resposta.",
            prompt
        )