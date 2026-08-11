from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from database import Base


class ConversaFeedback(Base):
    __tablename__ = "conversas_feedback"

    id = Column(Integer, primary_key=True, index=True)
    sessao_id = Column(String, index=True)
    mensagens = Column(String)
    consentimento = Column(Boolean, default=False)
    modelo = Column(String, nullable=True)
    criada_em = Column(DateTime, default=datetime.utcnow)