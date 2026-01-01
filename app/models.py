from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, Text, CheckConstraint, Index
from sqlalchemy.orm import relationship
from .database import Base
from .utils import now_utc


class HSK(Base):
    __tablename__ = "hsk"
    
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, index=True)  # Índice para ordenamiento
    nivel = Column(Integer, index=True)   # Índice para filtros
    hanzi = Column(String, index=True)    # Índice para búsquedas
    pinyin = Column(String, index=True)   # Índice para búsquedas
    espanol = Column(String, index=True)  # Índice para búsquedas
    hanzi_alt = Column(String, nullable=True)
    pinyin_alt = Column(String, nullable=True)
    categoria = Column(String, nullable=True)
    ejemplo = Column(Text, nullable=True)
    significado_ejemplo = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint('nivel >= 1 AND nivel <= 6', name='check_nivel_valido'),
        Index('idx_hanzi_nivel', 'hanzi', 'nivel'),  # Índice compuesto
    )


class Notas(Base):
    """
    Tabla para almacenar notas personalizadas sobre palabras HSK
    """
    __tablename__ = "notas"
    id = Column(Integer, primary_key=True, index=True)
    hsk_id = Column(Integer, ForeignKey("hsk.id"))
    nota = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)


class Diccionario(Base):
    __tablename__ = "diccionario"
    id = Column(Integer, primary_key=True, index=True)
    hsk_id = Column(Integer, ForeignKey("hsk.id"), unique=True)
    activo = Column(Boolean, default=True)  # Se desactiva cuando una frase lo contiene y está dominada


class Tarjeta(Base):
    __tablename__ = "tarjetas"
    id = Column(Integer, primary_key=True, index=True)
    hsk_id = Column(Integer, ForeignKey("hsk.id"), nullable=True)
    diccionario_id = Column(Integer, ForeignKey("diccionario.id"), nullable=True)
    ejemplo_id = Column(Integer, ForeignKey("ejemplos.id"), nullable=True)
    mostrado1 = Column(String, nullable=True)
    mostrado2 = Column(String, nullable=True)
    audio = Column(Boolean, default=False)
    requerido = Column(String)
    activa = Column(Boolean, default=True)  # Se desactiva cuando dominada por frase superior


class Ejemplo(Base):
    """
    Frases de ejemplo que se activan cuando todos sus hanzi están dominados
    """
    __tablename__ = "ejemplos"
    id = Column(Integer, primary_key=True, index=True)
    hanzi = Column(Text)  # Frase completa en hanzi: "我喝茶"
    pinyin = Column(Text)  # Pinyin completo: "wǒ hē chá"
    espanol = Column(Text)  # Traducción: "Yo bebo té"
    nivel = Column(Integer, default=1)  # HSK nivel
    complejidad = Column(Integer, default=1)  # 1=simple, 2=medio, 3=complejo (para jerarquía)
    activado = Column(Boolean, default=False)  # Se activa cuando todos los hanzi están dominados
    en_diccionario = Column(Boolean, default=False)  # Usuario lo añadió al estudio
    created_at = Column(DateTime, default=now_utc)


class HSKEjemplo(Base):
    """
    Relación many-to-many entre HSK (hanzi individuales) y Ejemplos (frases)
    Permite saber qué hanzi componen cada frase
    """
    __tablename__ = "hsk_ejemplo"
    id = Column(Integer, primary_key=True, index=True)
    hsk_id = Column(Integer, ForeignKey("hsk.id"))
    ejemplo_id = Column(Integer, ForeignKey("ejemplos.id"))
    posicion = Column(Integer)  # Posición del hanzi en la frase (1, 2, 3...)
    

class EjemploJerarquia(Base):
    """
    Jerarquía de ejemplos: frases complejas que contienen frases simples
    Ej: "我喝茶在餐厅" contiene "我喝茶"
    """
    __tablename__ = "ejemplo_jerarquia"
    id = Column(Integer, primary_key=True, index=True)
    ejemplo_complejo_id = Column(Integer, ForeignKey("ejemplos.id"))  # Frase compleja
    ejemplo_simple_id = Column(Integer, ForeignKey("ejemplos.id"))    # Frase simple contenida
    created_at = Column(DateTime, default=now_utc)


class SM2Session(Base):
    """Registro de sesiones de estudio SM2"""
    __tablename__ = "sm2_sessions"
    id = Column(Integer, primary_key=True, index=True)
    fecha_inicio = Column(DateTime, default=now_utc)
    fecha_fin = Column(DateTime, nullable=True)
    tarjetas_estudiadas = Column(Integer, default=0)
    tarjetas_correctas = Column(Integer, default=0)
    tarjetas_incorrectas = Column(Integer, default=0)


class SM2Progress(Base):
    """
    Progreso de cada tarjeta según el algoritmo SM2
    
    Estados de dominio:
    - nuevo: nunca estudiada
    - aprendiendo: en proceso (repetitions < 3)
    - dominada: bien establecida (repetitions >= 3 y interval >= 21)
    - madura: muy espaciada (interval >= 60)
    """
    __tablename__ = "sm2_progress"
    id = Column(Integer, primary_key=True, index=True)
    tarjeta_id = Column(Integer, ForeignKey("tarjetas.id"), unique=True)
    
    # Parámetros SM2
    easiness_factor = Column(Float, default=2.5)
    repetitions = Column(Integer, default=0)
    interval = Column(Integer, default=0)
    next_review = Column(DateTime, default=now_utc)
    
    # Estado de dominio
    estado = Column(String, default="nuevo")  # nuevo, aprendiendo, dominada, madura
    
    # Estadísticas
    total_reviews = Column(Integer, default=0)
    correct_reviews = Column(Integer, default=0)
    last_review = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_utc)
    
    # ✅ NUEVO: Optimistic locking para prevenir race conditions
    version = Column(Integer, default=1, nullable=False)
    
    __table_args__ = (
        Index('idx_next_review', 'next_review'),  # Para queries rápidas
        Index('idx_estado', 'estado'),  # Para filtros por estado
    )


class SM2Review(Base):
    """
    Historial de revisiones de cada tarjeta
    
    Para ejemplos, se puede registrar qué hanzi específicos fallaron
    """
    __tablename__ = "sm2_reviews"
    id = Column(Integer, primary_key=True, index=True)
    tarjeta_id = Column(Integer, ForeignKey("tarjetas.id"))
    session_id = Column(Integer, ForeignKey("sm2_sessions.id"))
    
    # Datos de la revisión
    quality = Column(Integer)  # 0-2: 0=Again, 1=Hard, 2=Easy
    
    respuesta_usuario = Column(Text, nullable=True)
    previous_easiness = Column(Float)
    new_easiness = Column(Float)
    previous_interval = Column(Integer)
    new_interval = Column(Integer)
    previous_estado = Column(String)
    new_estado = Column(String)
    
    # Para tarjetas de ejemplo: hanzi que fallaron
    hanzi_fallados = Column(Text, nullable=True)  # JSON: ["我", "茶"] o None
    frase_fallada = Column(Boolean, default=False)  # True si falló la estructura de la frase
    
    fecha = Column(DateTime, default=now_utc)
    
    __table_args__ = (
        Index('idx_fecha', 'fecha'),  # Para estadísticas por fecha
        Index('idx_tarjeta_fecha', 'tarjeta_id', 'fecha'),  # Para historial de tarjeta
    )


class EjemploActivacion(Base):
    """
    Log de activaciones de ejemplos
    Registra cuándo y por qué se activó un ejemplo
    """
    __tablename__ = "ejemplo_activacion"
    id = Column(Integer, primary_key=True, index=True)
    ejemplo_id = Column(Integer, ForeignKey("ejemplos.id"))
    fecha_activacion = Column(DateTime, default=now_utc)
    motivo = Column(String)  # "hanzi_dominados", "manual"
    hanzi_ids = Column(Text)  # JSON con IDs de hanzi que estaban dominados