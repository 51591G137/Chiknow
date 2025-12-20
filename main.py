from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles # <--- Nueva importación
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ... (Todo el código de base de datos que ya tenías se queda igual) ...
URL_BASE_DATOS = "sqlite:///./test.db"
engine = create_engine(URL_BASE_DATOS, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Tarea(Base):
    __tablename__ = "tareas"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/api/mensaje")
def leer_raiz():
    return {"mensaje": "¡Servidor Python respondiendo a tu clic!"}

# IMPORTANTE: Esta línea debe ir al final de las rutas
app.mount("/", StaticFiles(directory="static", html=True), name="static")