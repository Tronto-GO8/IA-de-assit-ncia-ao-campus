from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, engine
from models import Conversa, Mensagem as MensagemDB, Base
from chatbot import responder


app = FastAPI()


# Cria as tabelas
Base.metadata.create_all(bind=engine)


# Permite acesso do frontend
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
    sessao_id: str


# ---------- Chat ----------

@app.post("/chat")
def chat(
    dados: Pergunta,
    db: Session = Depends(get_db)
):

    # Verifica se a conversa já existe
    conversa = db.query(Conversa).filter(
        Conversa.sessao_id == dados.sessao_id
    ).first()

    # Se não existe, cria
    if conversa is None:
        conversa = Conversa(
            sessao_id=dados.sessao_id
        )

        db.add(conversa)
        db.commit()

    # Gera a resposta UMA vez
    resposta = responder(
        dados.pergunta,
        dados.historico
    )

    # Salva mensagem do usuário
    mensagem_usuario = MensagemDB(
        sessao_id=dados.sessao_id,
        autor="usuario",
        texto=dados.pergunta
    )

    db.add(mensagem_usuario)

    # Salva resposta da IA
    mensagem_ia = MensagemDB(
        sessao_id=dados.sessao_id,
        autor="bot",
        texto=resposta
    )

    db.add(mensagem_ia)

    # Salva tudo
    db.commit()

    return {
        "resposta": resposta
    }