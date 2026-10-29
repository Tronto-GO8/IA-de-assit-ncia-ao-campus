import os
import re
import unicodedata
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURACOES
# ============================================================

PASTA_TEXTOS = "documentos_em_txt"
CAMINHO_BANCO = "banco_vetorial"
NOME_COLECAO = "campusia"

MODELO_EMBEDDING = "intfloat/multilingual-e5-base"

# Tamanho maximo do TEXTO DO CHUNK, em caracteres.
# O contexto documental e adicionado separadamente ao texto armazenado.
TAMANHO_CHUNK = 900
OVERLAP = 120
BATCH_SIZE = 32
TAMANHO_LOTE_CHROMA = 100


# ============================================================
# CHROMADB
# ============================================================

cliente = chromadb.PersistentClient(path=CAMINHO_BANCO)

# IMPORTANTE: esta versao recria a colecao campusia do zero.
# Faca backup da pasta banco_vetorial antes de executar, se precisar
# preservar o indice atual.
try:
    cliente.delete_collection(NOME_COLECAO)
except Exception:
    pass

colecao = cliente.get_or_create_collection(
    name=NOME_COLECAO,
    metadata={"hnsw:space": "cosine"},
)


# ============================================================
# LIMPEZA DO TEXTO
# ============================================================

def parece_linha_de_tabela(linha: str) -> bool:
    """Identifica alguns formatos comuns de linhas tabulares extraidas."""
    if "|" in linha or "\t" in linha:
        return True

    # Extracoes de PDF frequentemente usam varios espacos entre colunas.
    return bool(re.search(r"\S {2,}\S", linha))


def limpar_texto(texto: str) -> str:
    """
    Remove ruido comum sem apagar linhas curtas nem destruir
    separadores de tabelas.
    """
    linhas_limpas = []

    for linha in texto.replace("\x0c", "\n").splitlines():
        linha = linha.strip()

        if not linha:
            linhas_limpas.append("")
            continue

        # Remove apenas numeros de pagina isolados.
        if linha.isdigit():
            continue

        if linha.casefold() in {
            "fls", "rubrica", "sumario", "sumário", "pagina", "página"
        }:
            continue

        # Preserva espacamento multiplo quando ele pode separar colunas.
        if not parece_linha_de_tabela(linha):
            linha = re.sub(r"[ \t]+", " ", linha)

        linhas_limpas.append(linha)

    texto_limpo = "\n".join(linhas_limpas)
    texto_limpo = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", texto_limpo)

    return texto_limpo.strip()


# ============================================================
# DETECCAO CONSERVADORA DE TITULOS E SUBTITULOS
# ============================================================

def eh_titulo_secao(linha: str) -> bool:
    """
    Reconhece titulos numerados, por exemplo:
    '1 INTRODUCAO', '1. INTRODUCAO', '2.3 Matriz curricular'.
    Evita tratar linhas tabulares como titulos.
    """
    linha = linha.strip()

    if not linha or parece_linha_de_tabela(linha):
        return False

    if len(linha) > 140:
        return False

    # Evita reconhecer frases comuns terminadas em pontuacao como titulo.
    if linha.endswith((".", ",", ";")):
        return False

    padrao = r"^\d+(?:\.\d+)*\.?\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ0-9]"
    return bool(re.match(padrao, linha))


def normalizar_rotulo(linha: str) -> str:
    """Normaliza acentos e caixa para comparar rotulos conhecidos."""
    texto = unicodedata.normalize("NFKD", linha.casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().rstrip(":")


ROTULOS_SUBSECAO = {
    "requisitos",
    "etapas",
    "responsabilidades",
    "objetivos",
    "atividades",
    "carga horaria",
    "documentacao",
    "consideracoes finais",
    "matriz curricular",
    "perfil do egresso",
    "organizacao curricular",
    "componentes curriculares",
    "estagio",
    "avaliacao",
    "duracao",
    "ingresso",
    "certificacao",
    "ementa",
    "infraestrutura",
    "criterios de avaliacao",
    "criterios de selecao",
    "publico-alvo",
    "publico alvo",
    "cronograma",
    "inscricoes",
    "inscricao",
    "vagas",
    "disposicoes gerais",
    "objetivo geral",
    "objetivos especificos",
}


def eh_subtitulo(linha: str) -> bool:
    """
    Reconhece rotulos conhecidos e titulos curtos em caixa alta.
    Nao usa somente 'estar em maiusculas' como criterio: linhas com
    formato tabular, frases longas ou pontuacao final sao preservadas.
    """
    linha = linha.strip()

    if not linha or len(linha) > 90:
        return False

    if parece_linha_de_tabela(linha):
        return False

    # Titulos numerados sao tratados primeiro por eh_titulo_secao().
    if re.match(r"^\d+(?:\.\d+)*\.?\s+", linha):
        return False

    if linha.endswith((".", ",", ";", "?", "!")):
        return False

    rotulo = normalizar_rotulo(linha)
    if rotulo in ROTULOS_SUBSECAO:
        return True

    palavras = linha.split()
    if not 1 <= len(palavras) <= 8:
        return False

    letras = [c for c in linha if c.isalpha()]
    if not letras:
        return False

    # Caixa alta e apenas uma pista adicional, nao uma regra universal.
    # Exclui linhas que parecem valores/codigos ou contem muitos digitos.
    quantidade_digitos = sum(c.isdigit() for c in linha)
    if quantidade_digitos > 0:
        return False

    caixa_alta = all(c.isupper() for c in letras)
    if caixa_alta and not any(s in linha for s in ("|", "\t")):
        return True

    return False


# ============================================================
# ESTRUTURACAO DO DOCUMENTO
# ============================================================

def estruturar_documento(texto: str) -> list[dict]:
    """
    Divide o documento em blocos com secao/subsecao.
    Preserva o conteudo anterior ao primeiro titulo e nao descarta
    blocos apenas por serem curtos.
    """
    partes = []
    secao_atual = ""
    subsecao_atual = ""
    bloco_atual = []

    def salvar_bloco():
        nonlocal bloco_atual

        conteudo = "\n".join(bloco_atual).strip()
        if conteudo:
            partes.append({
                "secao": secao_atual,
                "subsecao": subsecao_atual,
                "texto": conteudo,
            })

        bloco_atual = []

    for linha in texto.splitlines():
        linha = linha.strip()

        if not linha:
            if bloco_atual and bloco_atual[-1] != "":
                bloco_atual.append("")
            continue

        if eh_titulo_secao(linha):
            salvar_bloco()
            secao_atual = linha
            subsecao_atual = ""
            continue

        if eh_subtitulo(linha):
            salvar_bloco()
            subsecao_atual = linha.rstrip(":")
            continue

        bloco_atual.append(linha)

    salvar_bloco()

    # Fallback de seguranca: se nada foi estruturado, preserva o documento.
    if not partes and texto.strip():
        partes.append({
            "secao": "",
            "subsecao": "",
            "texto": texto.strip(),
        })

    return partes


# ============================================================
# DIVISAO EM CHUNKS COM LIMITE E OVERLAP
# ============================================================

def encontrar_fim(texto: str, inicio: int, limite: int) -> int:
    """
    Procura um ponto de corte natural antes do limite.
    Prioridade: quebra de paragrafo, quebra de linha, fim de frase,
    espaco entre palavras. Se nao houver, usa o limite exato.
    """
    if limite >= len(texto):
        return len(texto)

    minimo = inicio + int((limite - inicio) * 0.60)
    trecho = texto[minimo:limite]

    for separador in ("\n\n", "\n"):
        pos = trecho.rfind(separador)
        if pos >= 0:
            fim = minimo + pos + len(separador)
            if fim > inicio:
                return fim

    # Ultimo fim de frase antes do limite.
    matches = list(re.finditer(r"[.!?](?:[\"'’”)]*)\s+", trecho))
    if matches:
        return minimo + matches[-1].end()

    pos_espaco = texto.rfind(" ", minimo, limite)
    if pos_espaco > inicio:
        return pos_espaco

    return limite


def dividir_texto(texto: str, tamanho: int = TAMANHO_CHUNK,
                  overlap: int = OVERLAP) -> list[str]:
    """
    Cria janelas com limite maximo de caracteres e overlap controlado.
    Todo o conteudo e coberto; o overlap nunca faz o chunk ultrapassar
    TAMANHO_CHUNK.
    """
    texto = texto.strip()
    if not texto:
        return []

    if tamanho < 1:
        raise ValueError("TAMANHO_CHUNK precisa ser maior que zero.")

    overlap = max(0, min(overlap, tamanho - 1))

    if len(texto) <= tamanho:
        return [texto]

    chunks = []
    inicio = 0
    tamanho_texto = len(texto)

    while inicio < tamanho_texto:
        limite = min(inicio + tamanho, tamanho_texto)
        fim = encontrar_fim(texto, inicio, limite)

        # Garante progresso mesmo em casos de texto incomum.
        if fim <= inicio:
            fim = limite

        chunk = texto[inicio:fim].strip()
        if chunk:
            # A retirada de espacos nas pontas nao altera o limite maximo.
            if len(chunk) > tamanho:
                chunk = chunk[:tamanho].rstrip()
            chunks.append(chunk)

        if fim >= tamanho_texto:
            break

        proximo_inicio = max(inicio + 1, fim - overlap)

        # Evita comecar no meio de uma palavra. O texto que avanca ate
        # esse espaco ja esta coberto pelo chunk anterior.
        if proximo_inicio > 0 and not texto[proximo_inicio - 1].isspace():
            proximo_espaco = texto.find(" ", proximo_inicio, min(fim, proximo_inicio + 80))
            proxima_quebra = texto.find("\n", proximo_inicio, min(fim, proximo_inicio + 80))
            candidatos = [p for p in (proximo_espaco, proxima_quebra) if p >= 0]
            if candidatos:
                proximo_inicio = min(candidatos) + 1

        if proximo_inicio <= inicio:
            proximo_inicio = fim

        inicio = proximo_inicio

    return chunks


# ============================================================
# CRIACAO DE CHUNKS COM CONTEXTO
# ============================================================

def nome_documento(arquivo: str) -> str:
    """Transforma nome do arquivo em rotulo legivel."""
    nome = Path(arquivo).stem.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", nome).strip()


def criar_chunks(texto: str, arquivo: str) -> list[dict]:
    """
    Cada chunk carrega os metadados da sua origem. O texto principal
    permanece limitado a TAMANHO_CHUNK caracteres.
    """
    estrutura = estruturar_documento(texto)
    chunks_finais = []

    for parte in estrutura:
        secao = parte["secao"].strip()
        subsecao = parte["subsecao"].strip()
        conteudo = parte["texto"].strip()

        if not conteudo:
            continue

        for chunk_texto in dividir_texto(conteudo):
            chunks_finais.append({
                "arquivo": arquivo,
                "documento": nome_documento(arquivo),
                "titulo": subsecao or secao or nome_documento(arquivo),
                "secao": secao,
                "subsecao": subsecao,
                "texto": chunk_texto,
            })

    # Fallback de seguranca para nao perder texto por falha de estruturacao.
    if not chunks_finais and texto.strip():
        for chunk_texto in dividir_texto(texto.strip()):
            chunks_finais.append({
                "arquivo": arquivo,
                "documento": nome_documento(arquivo),
                "titulo": nome_documento(arquivo),
                "secao": "",
                "subsecao": "",
                "texto": chunk_texto,
            })

    return chunks_finais


def montar_documento_contextualizado(chunk: dict) -> str:
    """
    Texto armazenado no ChromaDB. Assim, a origem acompanha o trecho
    recuperado, em vez de existir apenas no embedding ou nos metadados.
    """
    linhas = [f"Documento: {chunk['documento']}"]

    if chunk["secao"]:
        linhas.append(f"Seção: {chunk['secao']}")

    if chunk["subsecao"]:
        linhas.append(f"Subseção: {chunk['subsecao']}")

    linhas.append("Conteúdo:")
    linhas.append(chunk["texto"])

    return "\n".join(linhas)


# ============================================================
# MODELO DE EMBEDDINGS
# ============================================================

print("\nCarregando modelo de embeddings...")
model = SentenceTransformer(MODELO_EMBEDDING)
print("Modelo de embeddings carregado!")


# ============================================================
# PROCESSAMENTO DOS ARQUIVOS TXT
# ============================================================

if not os.path.isdir(PASTA_TEXTOS):
    raise FileNotFoundError(
        f"A pasta '{PASTA_TEXTOS}' nao foi encontrada. "
        "Execute o script na pasta raiz do backend ou ajuste PASTA_TEXTOS."
    )

todos_ids = []
todos_embeddings = []
todos_documents = []
todos_metadatas = []
total_chunks = 0

arquivos = sorted(os.listdir(PASTA_TEXTOS))

for arquivo in arquivos:
    if not arquivo.lower().endswith(".txt"):
        continue

    caminho = os.path.join(PASTA_TEXTOS, arquivo)
    print(f"\nProcessando: {arquivo}")

    with open(caminho, "r", encoding="utf-8-sig") as f:
        texto = f.read()

    texto = limpar_texto(texto)
    if not texto:
        print("Arquivo vazio apos a limpeza; ignorado.")
        continue

    chunks = criar_chunks(texto, arquivo)
    print(f"Chunks encontrados: {len(chunks)}")

    documentos_contextualizados = [
        montar_documento_contextualizado(chunk) for chunk in chunks
    ]

    # E5: o prefixo passage: e usado para os textos indexados.
    textos_embedding = [
        f"passage: {documento}" for documento in documentos_contextualizados
    ]

    embeddings = model.encode(
        textos_embedding,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    for i, chunk in enumerate(chunks):
        id_chunk = f"{Path(arquivo).stem}_{i}"

        todos_ids.append(id_chunk)
        todos_embeddings.append(embeddings[i].tolist())

        # Armazena o texto com contexto para a recuperacao posterior.
        todos_documents.append(documentos_contextualizados[i])

        todos_metadatas.append({
            "arquivo": arquivo,
            "documento": chunk["documento"],
            "titulo": chunk["titulo"],
            "chunk_id": i,
            "secao": chunk["secao"],
            "subsecao": chunk["subsecao"],
        })

        total_chunks += 1


# ============================================================
# INSERCAO EM LOTES NO CHROMADB
# ============================================================

print("\nInserindo chunks no ChromaDB...")

for inicio in range(0, len(todos_ids), TAMANHO_LOTE_CHROMA):
    fim = inicio + TAMANHO_LOTE_CHROMA

    colecao.add(
        ids=todos_ids[inicio:fim],
        embeddings=todos_embeddings[inicio:fim],
        documents=todos_documents[inicio:fim],
        metadatas=todos_metadatas[inicio:fim],
    )

print("\n" + "=" * 60)
print(f"Total de chunks criados: {total_chunks}")
print(f"Chunks no ChromaDB: {colecao.count()}")
print("=" * 60)
print("\nBanco vetorial criado com sucesso!")
