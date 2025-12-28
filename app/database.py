from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import config
import os

# Obtener URL de base de datos según configuración
DATABASE_URL = config.get_database_url()

# Configurar conexión específica para cada tipo de BD
connect_args = {}
engine_params = {}

if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}
    engine_params = {
        "connect_args": connect_args
    }
elif "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL:
    # Para PostgreSQL, manejar parámetros específicos
    engine_params = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "echo": False
    }
    # Si estamos en Render, usar SSL si está disponible
    if os.getenv("RENDER", False):
        engine_params["connect_args"] = {"sslmode": "require"}

engine = create_engine(DATABASE_URL, **engine_params)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Inicializa la base de datos creando todas las tablas"""
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada")