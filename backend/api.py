from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json

from database import get_db, engine
from models import ConversaFeedback, Base
from chatbot import responder

app = FastAPI()

# cria as tabelas
Base.metadata.create_all(bind=engine)

# permite acesso do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Schemas ----------

class Mensagem(BaseModel):
    autor: str
    texto: str

class Pergunta(BaseModel):
    pergunta: str
    historico: list[Mensagem] = []

class FeedbackConversa(BaseModel):
    sessao_id: str | None = None
    mensagens: list[Mensagem]
    consentimento: bool
    modelo: str | None = None

# ---------- Chat ----------

@app.post("/chat")
def chat(dados: Pergunta):

    resposta = responder(
        dados.pergunta,
        dados.historico
    )

    return {
        "resposta": resposta
    }

# ---------- Feedback ----------

@app.post("/feedback")
def salvar_feedback(
    dados: FeedbackConversa,
    db: Session = Depends(get_db)
):

    if not dados.consentimento:
        return {"salvo": False}

    conversa = ConversaFeedback(
        sessao_id=dados.sessao_id,
        mensagens=json.dumps(
            [m.model_dump() for m in dados.mensagens],
            ensure_ascii=False
        ),
        consentimento=True,
        modelo=dados.modelo
    )

    db.add(conversa)
    db.commit()
    db.refresh(conversa)

    return {
        "salvo": True,
        "id": conversa.id
    }