from fastapi import FastAPI, Depends, Request, Query
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
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/diccionario")
def diccionario_page(request: Request):
    return templates.TemplateResponse("diccionario.html", {"request": request})

@app.get("/tarjetas")
def tarjetas_page(request: Request):
    return templates.TemplateResponse("tarjetas.html", {"request": request})

@app.get("/sm2")
def sm2_page(request: Request):
    return templates.TemplateResponse("sm2.html", {"request": request})

# --- RUTAS DE API HSK ---

@app.get("/api/hsk")
def api_listar_hsk(db: Session = Depends(database.get_db)):
    """Lista todas las palabras HSK con información de si están en el diccionario"""
    palabras = repository.get_hsk_all(db)
    diccionario_ids = repository.get_diccionario_hsk_ids(db)
    
    resultado = []
    for palabra in palabras:
        resultado.append({
            "id": palabra.id,
            "numero": palabra.numero,
            "nivel": palabra.nivel,
            "hanzi": palabra.hanzi,
            "pinyin": palabra.pinyin,
            "espanol": palabra.espanol,
            "en_diccionario": palabra.id in diccionario_ids
        })
    
    return resultado

@app.get("/api/hsk/search")
def api_buscar_hsk(query: str = Query(""), db: Session = Depends(database.get_db)):
    """Busca palabras en HSK por hanzi, pinyin o español"""
    if not query or query.strip() == "":
        return api_listar_hsk(db)
    
    palabras = repository.search_hsk(db, query)
    diccionario_ids = repository.get_diccionario_hsk_ids(db)
    
    resultado = []
    for palabra in palabras:
        resultado.append({
            "id": palabra.id,
            "numero": palabra.numero,
            "nivel": palabra.nivel,
            "hanzi": palabra.hanzi,
            "pinyin": palabra.pinyin,
            "espanol": palabra.espanol,
            "en_diccionario": palabra.id in diccionario_ids
        })
    
    return resultado

# --- RUTAS DE API DICCIONARIO ---

@app.post("/api/diccionario/add/{hsk_id}")
def api_agregar_diccionario(hsk_id: int, db: Session = Depends(database.get_db)):
    """Agrega una palabra al diccionario y genera las 6 tarjetas de estudio"""
    if repository.existe_en_diccionario(db, hsk_id):
        return {"error": "La palabra ya está en el diccionario"}
    
    exito = service.agregar_palabra_y_generar_tarjetas(db, hsk_id)
    if not exito:
        return {"error": "No se pudo procesar la palabra"}
    
    return {"status": "ok", "message": "Palabra y 6 tarjetas creadas"}

@app.delete("/api/diccionario/remove/{hsk_id}")
def api_eliminar_diccionario(hsk_id: int, db: Session = Depends(database.get_db)):
    """Elimina una palabra del diccionario y todas sus tarjetas asociadas"""
    exito = service.eliminar_palabra_y_tarjetas(db, hsk_id)
    if not exito:
        return {"error": "No se pudo eliminar la palabra"}
    
    return {"status": "ok", "message": "Palabra eliminada del diccionario"}

@app.get("/api/diccionario")
def api_ver_diccionario(db: Session = Depends(database.get_db)):
    """Lista todas las palabras en el diccionario con su información completa"""
    return service.obtener_diccionario_completo(db)

@app.get("/api/diccionario/search")
def api_buscar_diccionario(query: str = Query(""), db: Session = Depends(database.get_db)):
    """Busca en el diccionario por hanzi, pinyin o español"""
    return service.buscar_en_diccionario(db, query)

# --- RUTAS DE API TARJETAS ---

@app.get("/api/tarjetas")
def api_ver_tarjetas(db: Session = Depends(database.get_db)):
    """Lista todas las tarjetas generadas con información de la palabra"""
    return service.obtener_tarjetas_completas(db)

@app.get("/api/tarjetas/estadisticas")
def api_estadisticas_tarjetas(db: Session = Depends(database.get_db)):
    """Obtiene estadísticas sobre las tarjetas"""
    return service.obtener_estadisticas_tarjetas(db)

# --- RUTAS DE API SM2 ---

@app.post("/api/sm2/session/start")
def api_iniciar_sesion(db: Session = Depends(database.get_db)):
    """Inicia una nueva sesión de estudio SM2"""
    return service.iniciar_sesion_estudio(db)

@app.get("/api/sm2/cards/due")
def api_tarjetas_pendientes(limite: int = Query(20), db: Session = Depends(database.get_db)):
    """Obtiene tarjetas pendientes de revisión"""
    return service.obtener_tarjetas_para_estudiar(db, limite)

@app.post("/api/sm2/review")
def api_procesar_respuesta(
    tarjeta_id: int,
    session_id: int,
    quality: int,
    db: Session = Depends(database.get_db)
):
    """
    Procesa una respuesta del usuario
    quality: 0-5 (0=no recordada, 5=perfecta)
    """
    if quality < 0 or quality > 5:
        return {"error": "Quality debe estar entre 0 y 5"}
    
    return service.procesar_respuesta(db, tarjeta_id, session_id, quality)

@app.post("/api/sm2/session/end/{session_id}")
def api_finalizar_sesion(session_id: int, db: Session = Depends(database.get_db)):
    """Finaliza una sesión de estudio"""
    return service.finalizar_sesion_estudio(db, session_id)

@app.get("/api/sm2/statistics")
def api_estadisticas_sm2(db: Session = Depends(database.get_db)):
    """Obtiene estadísticas generales del sistema SM2"""
    return service.obtener_estadisticas_sm2(db)

@app.get("/api/sm2/progress")
def api_progreso_detallado(db: Session = Depends(database.get_db)):
    """Obtiene el progreso detallado de todas las tarjetas"""
    return service.obtener_progreso_detallado(db)