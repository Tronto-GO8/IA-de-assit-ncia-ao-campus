from pathlib import Path
import os

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db, engine
from models import Log, Base
from chatbot import responder


app = FastAPI()


# ==========================================
# BANCO DE DADOS
# ==========================================

# Cria as tabelas, caso ainda não existam
Base.metadata.create_all(bind=engine)


# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# DOCUMENTOS
# ==========================================

documentos_dir = (
    Path(__file__).resolve().parent / "documentos"
)

if documentos_dir.exists():
    app.mount(
        "/documentos",
        StaticFiles(directory=str(documentos_dir)),
        name="documentos"
    )


# ==========================================
# SCHEMAS
# ==========================================

class Mensagem(BaseModel):
    autor: str
    texto: str


class Pergunta(BaseModel):
    pergunta: str
    historico: list[Mensagem] = Field(
        default_factory=list
    )
    sessao_id: str


# ==========================================
# CHAT
# ==========================================

@app.post("/chat")
def chat(
    dados: Pergunta,
    db: Session = Depends(get_db)
):
    # Verifica se a gravação está habilitada
    gravar_conversa = (
        os.getenv("GRAVAR_CONVERSA", "").strip().lower()
        == "sim"
    )

    print(
        "GRAVAR_CONVERSA =",
        os.getenv("GRAVAR_CONVERSA")
    )

    # Gera a resposta uma única vez
    resposta, fontes, prompt = responder(
        dados.pergunta,
        dados.historico
    )

    # Grava o registro da interação
    if gravar_conversa:

        try:
            log = Log(
                sessao_id=dados.sessao_id,
                prompt=prompt,
                pergunta=dados.pergunta,
                resposta=resposta
            )

            db.add(log)
            db.commit()

            print(
                "Conversa gravada com sucesso. "
                f"Sessão: {dados.sessao_id}"
            )

        except Exception as erro:
            db.rollback()

            print(
                "Erro ao gravar conversa:",
                erro
            )

    # Retorna a resposta e as fontes ao frontend
    return {
        "resposta": resposta,
        "fontes": fontes
    }


# ==========================================
# FRONTEND
# ==========================================

frontend_dir = (
    Path(__file__).resolve().parent.parent / "frontend"
)

if frontend_dir.exists():
    app.mount(
        "/",
        StaticFiles(
            directory=str(frontend_dir),
            html=True
        ),
        name="frontend"
    )