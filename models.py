from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from database import Base

class HSK(Base):
    __tablename__ = "hsk"
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer)
    nivel = Column(Integer)
    hanzi = Column(String)
    pinyin = Column(String)
    espanol = Column(String)

class Diccionario(Base):
    __tablename__ = "diccionario"
    id = Column(Integer, primary_key=True, index=True)
    hsk_id = Column(Integer, ForeignKey("hsk.id"))

class Tarjeta(Base):
    __tablename__ = "tarjetas"
    id = Column(Integer, primary_key=True, index=True)
    hsk_id = Column(Integer, ForeignKey("hsk.id"))
    diccionario_id = Column(Integer, ForeignKey("diccionario.id"))
    mostrado1 = Column(String, nullable=True)
    mostrado2 = Column(String, nullable=True)
    audio = Column(Boolean, default=False)
    requerido = Column(String)