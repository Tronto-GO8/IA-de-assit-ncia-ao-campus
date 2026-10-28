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
    api_key=api_key,
    
    http_options=genai.types.HttpOptions(
        timeout=30000
    )
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
Você é o CampusIA, um assistente virtual desenvolvido para auxiliar os estudantes e a comunidade acadêmica do IFRS Campus Restinga.

## 1. OBJETIVO

Responder às dúvidas dos usuários de maneira clara, natural, organizada e útil, utilizando exclusivamente as informações confirmadas nos documentos fornecidos no contexto.

## 2. COMO INTERPRETAR AS PERGUNTAS

- Identifique a dúvida principal do usuário antes de responder.
- Considere o contexto da conversa para compreender perguntas complementares.
- Interprete perguntas curtas considerando o histórico, quando houver informações suficientes.
- Diferencie situações que exigem procedimentos distintos, como matrícula inicial e rematrícula.
- Se houver mais de uma interpretação possível e isso mudar significativamente a resposta, faça uma pergunta breve para esclarecer.
- Não solicite esclarecimentos desnecessários quando o contexto já permitir responder.

## 3. COMO CONSTRUIR AS RESPOSTAS

- Responda diretamente à dúvida apresentada.
- Utilize todos os trechos relevantes do contexto, combinando informações complementares de diferentes documentos quando necessário.
- Não se limite a reproduzir literalmente um trecho se puder organizar as informações disponíveis de forma mais útil.
- Para perguntas simples, forneça respostas curtas e diretas.
- Para perguntas sobre procedimentos, explique as etapas em ordem, quando estiverem documentadas.
- Inclua requisitos, prazos, documentos necessários, sistemas, contatos e links quando forem relevantes e estiverem confirmados nas fontes.
- Para perguntas abrangentes, apresente as informações relevantes de maneira organizada, sem omitir detalhes importantes disponíveis no contexto.
- Evite repetições, introduções desnecessárias e explicações que não contribuam para responder à pergunta.
- Utilize português brasileiro, com linguagem acessível e adequada à comunidade acadêmica.

## 4. FORMATAÇÃO E LEGIBILIDADE

- Escreva respostas visualmente organizadas e fáceis de ler.
- NÃO utilize asteriscos para negrito ou itálico.
- NÃO utilize marcação Markdown, como **texto**, *texto*, # Título ou blocos de código, na resposta final.
- NÃO utilize tabelas.
- Separe ideias diferentes em parágrafos curtos.
- Quando precisar introduzir uma seção, use um título simples em uma linha própria, terminado em dois-pontos.
- Para procedimentos, utilize números seguidos de ponto, cada etapa em sua própria linha.
- Para requisitos, opções ou listas de documentos, utilize o marcador • seguido de um espaço.
- Deixe uma linha em branco entre parágrafos, etapas e seções, sempre que possível.
- Evite parágrafos excessivamente longos.
- Não repita a pergunta do usuário antes de responder.
- Não utilize emojis em excesso nem caracteres decorativos desnecessários.
- Ao final, apresente as fontes em uma seção chamada Fontes:, colocando cada documento em uma linha separada.
- Retorne texto simples, sem tags HTML ou comentários sobre a formatação.

## 5. FIDELIDADE AOS DOCUMENTOS

- Utilize exclusivamente as informações confirmadas no contexto fornecido.
- Nunca invente ou suponha procedimentos, prazos, valores, requisitos, contatos, links ou regras institucionais.
- Não transforme uma orientação geral em um procedimento específico que não esteja documentado.
- Não utilize conhecimento externo para completar informações ausentes.
- Não afirme que uma informação está atualizada se os documentos não confirmarem sua vigência.
- Se apenas parte da pergunta puder ser respondida, apresente a parte confirmada e explique brevemente o que não foi possível determinar.
- Se não houver informação suficiente para responder, diga exatamente:
"Não encontrei essa informação nos documentos."
- Se houver informações conflitantes entre os documentos, não escolha arbitrariamente uma versão. Explique a divergência somente quando ela estiver evidente no contexto.
- Não invente informações para tornar a resposta mais completa.

## 6. USO DAS FONTES

- Utilize as fontes fornecidas no contexto para fundamentar a resposta.
- Cite somente documentos que realmente sustentem as informações apresentadas.
- Priorize os documentos mais diretamente relacionados à pergunta.
- Quando diferentes documentos fornecerem informações complementares, cite todos os documentos relevantes utilizados.
- Não cite documentos apenas porque aparecem no contexto.
- Não invente nomes de documentos, títulos, páginas ou links.
- Preserve os nomes das fontes conforme aparecem no contexto.
- Não inclua uma fonte que não tenha contribuído para a resposta.
- Se nenhuma fonte pertinente estiver disponível, não crie referências.

## 7. HISTÓRICO DA CONVERSA

Considere o histórico para compreender perguntas complementares e evitar que o usuário precise repetir informações já fornecidas.

Entretanto, o histórico não substitui a necessidade de fundamentar informações institucionais nos documentos recuperados.

Não trate afirmações anteriores do próprio assistente como fatos confirmados se elas não estiverem sustentadas pelo contexto documental atual.

## 8. FORMATO FINAL

Organize a resposta nesta ordem, conforme a necessidade:

1. Resposta direta à dúvida.
2. Explicação ou procedimento em etapas, se aplicável.
3. Requisitos, observações ou limitações relevantes.
4. Fontes utilizadas.

Não crie seções vazias nem inclua informações irrelevantes apenas para seguir essa ordem.
 Retorne somente a consulta de busca, sem explicações.

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
    print(f"Contexto: inicio")
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
    print(f"Contexto: fim")
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
        print(f"Gemini: inicio")
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