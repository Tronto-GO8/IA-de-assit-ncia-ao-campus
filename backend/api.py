from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chatbot import responder

app = FastAPI()

# permite que o frontend acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Mensagem(BaseModel):
    autor: str
    texto: str

class Pergunta(BaseModel):
    pergunta: str
    historico: list[Mensagem] = []


@app.post("/chat")
def chat(dados: Pergunta):

    resposta = responder(
        dados.pergunta,
        dados.historico
    )

    return {
        "resposta": resposta
    }