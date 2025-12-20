from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime
from datetime import datetime
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

class SM2Session(Base):
    """Registro de sesiones de estudio SM2"""
    __tablename__ = "sm2_sessions"
    id = Column(Integer, primary_key=True, index=True)
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    tarjetas_estudiadas = Column(Integer, default=0)
    tarjetas_correctas = Column(Integer, default=0)
    tarjetas_incorrectas = Column(Integer, default=0)

class SM2Progress(Base):
    """
    Progreso de cada tarjeta según el algoritmo SM2
    
    Algoritmo SM2:
    - easiness_factor (EF): Factor de facilidad, inicia en 2.5
    - repetitions: Número de repeticiones consecutivas correctas
    - interval: Intervalo en días hasta la próxima revisión
    - next_review: Fecha de la próxima revisión
    """
    __tablename__ = "sm2_progress"
    id = Column(Integer, primary_key=True, index=True)
    tarjeta_id = Column(Integer, ForeignKey("tarjetas.id"), unique=True)
    
    # Parámetros SM2
    easiness_factor = Column(Float, default=2.5)  # Factor de facilidad (EF)
    repetitions = Column(Integer, default=0)      # Repeticiones consecutivas correctas
    interval = Column(Integer, default=0)         # Intervalo en días
    next_review = Column(DateTime, default=datetime.utcnow)  # Próxima revisión
    
    # Estadísticas
    total_reviews = Column(Integer, default=0)    # Total de revisiones
    correct_reviews = Column(Integer, default=0)  # Revisiones correctas
    last_review = Column(DateTime, nullable=True) # Última revisión
    created_at = Column(DateTime, default=datetime.utcnow)

class SM2Review(Base):
    """Historial de revisiones de cada tarjeta"""
    __tablename__ = "sm2_reviews"
    id = Column(Integer, primary_key=True, index=True)
    tarjeta_id = Column(Integer, ForeignKey("tarjetas.id"))
    session_id = Column(Integer, ForeignKey("sm2_sessions.id"))
    
    # Datos de la revisión
    quality = Column(Integer)  # 0-5 (calidad de la respuesta)
    # 0: Complete blackout
    # 1: Incorrect response; correct one remembered
    # 2: Incorrect response; correct one seemed easy to recall
    # 3: Correct response recalled with serious difficulty
    # 4: Correct response after hesitation
    # 5: Perfect response
    
    previous_easiness = Column(Float)
    new_easiness = Column(Float)
    previous_interval = Column(Integer)
    new_interval = Column(Integer)
    fecha = Column(DateTime, default=datetime.utcnow)