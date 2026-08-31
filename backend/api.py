from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, engine
from models import Log, Base
from chatbot import responder
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from models import Log
import os

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
    # Gera a resposta UMA vez
    resposta, prompt = responder(
        dados.pergunta,
        dados.historico
    )
    # Grava log da conversa
    if os.getenv("GRAVAR_CONVERSA") == "sim":
        log = Log(
            sessao_id=dados.sessao_id,
            prompt=prompt,
            pergunta=dados.pergunta,
            resposta=resposta
        )

        db.add(log)
        db.commit()
        db.close()
    return {
        "resposta": resposta
    }


# Monta frontend estático (index.html + assets) na raiz
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")