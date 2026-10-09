import os
from dotenv import load_dotenv
from google import genai

from busca import buscar_contexto

#temp 
from time import perf_counter
# ==========================================
# CONFIGURAÇÃO
# ==========================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(
    api_key=api_key
)


# ==========================================
# Função de contextualização de perguntas
# ==========================================


def contextualizar_pergunta(pergunta, historico):
    """
    Reescreve a pergunta atual para que a busca documental
    consiga entendê-la com base no histórico da conversa.
    """

    if not historico:
        return pergunta

    texto_historico = ""

    for mensagem in historico:
        # Aceita tanto dicionários quanto objetos
        if isinstance(mensagem, dict):
            autor = mensagem.get("autor", "")
            texto = mensagem.get("texto", "")
        else:
            autor = getattr(mensagem, "autor", "")
            texto = getattr(mensagem, "texto", "")

        texto_historico += f"{autor}: {texto}\n"

    prompt_busca = f"""
Você é um assistente que transforma perguntas em consultas
para uma busca em documentos institucionais.

Sua tarefa é reescrever a pergunta atual como uma consulta
que possa ser compreendida sem precisar ler o histórico.

REGRAS:
- Use o histórico apenas para esclarecer o assunto da pergunta.
- Preserve a intenção da pergunta atual.
- Recupere do histórico os assuntos e termos necessários.
- Não responda à pergunta.
- Não invente informações, documentos, nomes ou procedimentos.
- Se a pergunta já estiver clara, mantenha-a praticamente igual.
- Retorne somente a consulta de busca, sem explicações.

HISTÓRICO:
{texto_historico}

PERGUNTA ATUAL:
{pergunta}

CONSULTA DE BUSCA:
"""

    try:
        resposta = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt_busca
        )

        consulta = (resposta.text or "").strip()

        if consulta:
            return consulta

    except Exception as erro:
        print(f"Erro ao contextualizar pergunta: {erro}")

    # Se a contextualização falhar, usa a pergunta original
    return pergunta


# ==========================================
# CHAT
# ==========================================

def responder(pergunta, historico=None):

    if historico is None:
        historico = []

    texto_historico = ""

    for mensagem in historico:

        if isinstance(mensagem, dict):
            autor = mensagem.get("autor", "")
            texto = mensagem.get("texto", "")
        else:
            autor = getattr(mensagem, "autor", "")
            texto = getattr(mensagem, "texto", "")

        texto_historico += f"{autor}: {texto}\n"

# ==========================================
# CONTEXTUALIZAÇÃO DA PERGUNTA
# ==========================================

    pergunta_busca = contextualizar_pergunta(
            pergunta,
            historico
    )

    print(f"Pergunta original: {pergunta}")
    print(f"Consulta de busca: {pergunta_busca}")


# ==========================================
# BUSCA SEMÂNTICA
# ==========================================

    chunks = buscar_contexto(
        pergunta_busca
    )


# ==========================================
# FONTES
# ==========================================

    fontes = []
    fontes_vistas = set()

    for item in chunks:

        arquivo_txt = item.get("arquivo", "")
        titulo = item.get("titulo", "")

        if not arquivo_txt:
            continue

        # Troca a extensão .txt por .pdf
        arquivo_pdf = os.path.splitext(arquivo_txt)[0] + ".pdf"

        if arquivo_pdf in fontes_vistas:
            continue

        fontes_vistas.add(arquivo_pdf)

        fontes.append({
            "arquivo": arquivo_pdf,
            "titulo": titulo
        })



    # ==========================================
    # CONTEXTO DOS DOCUMENTOS
    # ==========================================

    contexto = ""

    for item in chunks:

        contexto += f"""
ARQUIVO: {item['arquivo']}
SEÇÃO: {item.get('secao', '')}
SUBSEÇÃO: {item.get('subsecao', '')}

{item['chunk']}

-----------------------------------
"""


    # ==========================================
    # PROMPT
    # ==========================================

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
8. Não invente fontes, títulos, páginas ou referências.
9. Não mencione o formato do arquivo nas citações.
Por exemplo, não escreva ".pdf", ".docx" etc.
10. Se uma informação não possuir uma fonte disponível
no contexto, não crie uma referência para ela.
11. Priorize respostas curtas e diretas, mas forneça
detalhes suficientes para responder à dúvida.
12. Caso a pergunta não possa ser respondida com
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


    # ==========================================
    # SEM RESULTADOS
    # ==========================================

    if len(chunks) == 0:

        return (
            "Não encontrei essa informação nos documentos.",
            [],
            prompt
        )


    # ==========================================
    # GEMINI
    # ==========================================

    try:
        inicio = perf_counter()

        resposta = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )

        print(f"Tempo do Gemini: {perf_counter() - inicio:.2f}s")

        return (
            resposta.text,
            fontes,
            prompt
        )


    except Exception as erro:

        print(
            f"Erro ao consultar o Gemini: {erro}"
        )

        return (
            f"Erro ao consultar o Gemini: {erro}",
            [],
            prompt
        )