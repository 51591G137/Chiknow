from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

# Importamos nuestros módulos locales
import models
import service
import repository
import database

# --- CAPA DE ARRANQUE ---
# Crea las tablas si no existen basándose en los modelos
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# Calculamos la ruta absoluta para evitar errores de "Directorio no encontrado"
base_path = os.path.dirname(os.path.realpath(__file__))
static_path = os.path.join(base_path, "static")
templates_path = os.path.join(base_path, "templates")

# Montar archivos estáticos (CSS, JS, Imágenes)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Configurar el motor de plantillas HTML
templates = Jinja2Templates(directory=templates_path)

# --- RUTAS DE NAVEGACIÓN (FRONTEND) ---

@app.get("/")
def home(request: Request):
    # Pasamos el request necesario para que Jinja2 funcione correctamente
    return templates.TemplateResponse("index.html", {"request": request})

# --- RUTAS DE API (BACKEND) ---

@app.get("/api/hsk")
def api_listar_hsk(db: Session = Depends(database.get_db)):
    return repository.get_hsk_all(db)

@app.post("/api/diccionario/add/{hsk_id}")
def api_agregar_diccionario(hsk_id: int, db: Session = Depends(database.get_db)):
    exito = service.agregar_palabra_y_generar_tarjetas(db, hsk_id)
    if not exito:
        return {"error": "No se pudo procesar la palabra"}
    return {"status": "ok", "message": "Palabra y 8 tarjetas creadas"}

@app.get("/api/tarjetas")
def api_ver_tarjetas(db: Session = Depends(database.get_db)):
    # Traemos todas las tarjetas generadas
    return db.query(models.Tarjeta).all()