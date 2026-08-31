from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime

from database import Base
'''class Conversa(Base):
    __tablename__ = "conversas"

    id = Column(Integer, primary_key=True)
    sessao_id = Column(String, unique=True, index=True)
    criada_em = Column(DateTime, default=datetime.utcnow)


class Mensagem(Base):
    __tablename__ = "mensagens"

    id = Column(Integer, primary_key=True)
    sessao_id = Column(String, index=True)
    autor = Column(String)
    texto = Column(Text)
    criada_em = Column(DateTime, default=datetime.utcnow)
'''

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True)
    sessao_id = Column(String, index=True)
    prompt = Column(Text)
    pergunta = Column(Text)
    resposta = Column(Text)
    criada_em = Column(DateTime, default=datetime.utcnow)