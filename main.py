from fastapi import FastAPI, Depends, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os

# Importamos nuestros módulos locales
import models
import service
import repository
import database

# --- CAPA DE ARRANQUE ---
# Crear tablas si no existen
print("🔧 Inicializando base de datos...")
database.Base.metadata.create_all(bind=database.engine)
print("✅ Base de datos inicializada")

# CREAR APP
app = FastAPI(title="Chiknow", version="1.0.0")

# ... resto del código

base_path = os.path.dirname(os.path.realpath(__file__))
static_path = os.path.join(base_path, "static")
templates_path = os.path.join(base_path, "templates")

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# --- MODELOS DE DATOS (Pydantic) ---

class ReviewRequest(BaseModel):
    tarjeta_id: int
    session_id: int
    quality: int
    hanzi_fallados: Optional[List[str]] = None
    frase_fallada: bool = False
    respuesta_usuario: Optional[str] = None

class NotaRequest(BaseModel):
    nota: str

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

@app.get("/ejemplos")
def ejemplos_page(request: Request):
    return templates.TemplateResponse("ejemplos.html", {"request": request})

@app.get("/sm2")
def sm2_page(request: Request):
    return templates.TemplateResponse("sm2.html", {"request": request})

# --- RUTAS DE API HSK ---

@app.get("/api/hsk")
def api_listar_hsk(db: Session = Depends(database.get_db)):
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

@app.post("/api/hsk/add-traduccion/{hsk_id}")
def api_añadir_traduccion(hsk_id: int, traduccion: str = Query(...), db: Session = Depends(database.get_db)):
    """Añade una traducción alternativa a una palabra HSK"""
    return service.añadir_traduccion_alternativa(db, hsk_id, traduccion)

# --- RUTAS DE API NOTAS ---

@app.get("/api/hsk/{hsk_id}/nota")
def api_obtener_nota(hsk_id: int, db: Session = Depends(database.get_db)):
    """Obtiene la nota de una palabra HSK"""
    nota = repository.get_nota_by_hsk_id(db, hsk_id)
    
    if nota:
        return {
            "hsk_id": hsk_id,
            "nota": nota.nota,
            "created_at": nota.created_at.isoformat() if nota.created_at else None,
            "updated_at": nota.updated_at.isoformat() if nota.updated_at else None
        }
    else:
        return {
            "hsk_id": hsk_id,
            "nota": None
        }

@app.post("/api/hsk/{hsk_id}/nota")
def api_guardar_nota(hsk_id: int, request: NotaRequest, db: Session = Depends(database.get_db)):
    """Crea o actualiza la nota de una palabra HSK"""
    # Verificar que la palabra HSK existe
    palabra = repository.get_hsk_by_id(db, hsk_id)
    if not palabra:
        return {"error": "Palabra HSK no encontrada"}
    
    # Crear o actualizar nota
    nota = repository.create_or_update_nota(db, hsk_id, request.nota)
    
    return {
        "status": "ok",
        "message": "Nota guardada",
        "hsk_id": hsk_id,
        "nota": nota.nota
    }

@app.delete("/api/hsk/{hsk_id}/nota")
def api_eliminar_nota(hsk_id: int, db: Session = Depends(database.get_db)):
    """Elimina la nota de una palabra HSK"""
    exito = repository.delete_nota(db, hsk_id)
    
    if exito:
        return {
            "status": "ok",
            "message": "Nota eliminada"
        }
    else:
        return {
            "error": "No se encontró nota para eliminar"
        }

@app.get("/api/notas")
def api_listar_notas(db: Session = Depends(database.get_db)):
    """Lista todas las notas con información de HSK"""
    notas_data = repository.get_all_notas(db)
    
    resultado = []
    for nota, hsk in notas_data:
        resultado.append({
            "id": nota.id,
            "hsk_id": hsk.id,
            "hanzi": hsk.hanzi,
            "pinyin": hsk.pinyin,
            "espanol": hsk.espanol,
            "nota": nota.nota,
            "created_at": nota.created_at.isoformat() if nota.created_at else None,
            "updated_at": nota.updated_at.isoformat() if nota.updated_at else None
        })
    
    return resultado

# --- RUTAS DE API DICCIONARIO ---

@app.post("/api/diccionario/add/{hsk_id}")
def api_agregar_diccionario(hsk_id: int, db: Session = Depends(database.get_db)):
    if repository.existe_en_diccionario(db, hsk_id):
        return {"error": "La palabra ya está en el diccionario"}
    
    exito = service.agregar_palabra_y_generar_tarjetas(db, hsk_id)
    if not exito:
        return {"error": "No se pudo procesar la palabra"}
    
    return {"status": "ok", "message": "Palabra y 6 tarjetas creadas"}

@app.delete("/api/diccionario/remove/{hsk_id}")
def api_eliminar_diccionario(hsk_id: int, db: Session = Depends(database.get_db)):
    exito = service.eliminar_palabra_y_tarjetas(db, hsk_id)
    if not exito:
        return {"error": "No se pudo eliminar la palabra"}
    
    return {"status": "ok", "message": "Palabra eliminada del diccionario"}

@app.get("/api/diccionario")
def api_ver_diccionario(db: Session = Depends(database.get_db)):
    return service.obtener_diccionario_completo(db)

@app.get("/api/diccionario/search")
def api_buscar_diccionario(query: str = Query(""), db: Session = Depends(database.get_db)):
    return service.buscar_en_diccionario(db, query)

# --- RUTAS DE API EJEMPLOS ---

@app.get("/api/ejemplos/todos")
def api_todos_ejemplos(db: Session = Depends(database.get_db)):
    """Obtiene TODOS los ejemplos de la base de datos"""
    return service.obtener_todos_ejemplos(db)

@app.get("/api/ejemplos/por-hanzi/{hsk_id}")
def api_ejemplos_por_hanzi(hsk_id: int, db: Session = Depends(database.get_db)):
    """Obtiene ejemplos que contienen un hanzi específico"""
    return service.obtener_ejemplos_por_hanzi(db, hsk_id)

@app.get("/api/ejemplos/disponibles")
def api_ejemplos_disponibles(db: Session = Depends(database.get_db)):
    """Obtiene ejemplos activados que el usuario puede añadir"""
    return service.obtener_ejemplos_disponibles(db)

@app.get("/api/ejemplos/en-estudio")
def api_ejemplos_en_estudio(db: Session = Depends(database.get_db)):
    """Obtiene ejemplos que el usuario está estudiando"""
    return service.obtener_ejemplos_en_estudio(db)

@app.post("/api/ejemplos/add/{ejemplo_id}")
def api_añadir_ejemplo(ejemplo_id: int, db: Session = Depends(database.get_db)):
    """Añade un ejemplo al estudio del usuario"""
    return service.añadir_ejemplo_a_estudio(db, ejemplo_id)

@app.delete("/api/ejemplos/remove/{ejemplo_id}")
def api_quitar_ejemplo(ejemplo_id: int, db: Session = Depends(database.get_db)):
    """Quita un ejemplo del estudio"""
    resultado = repository.quitar_ejemplo_de_diccionario(db, ejemplo_id)
    if resultado:
        # Eliminar tarjetas asociadas
        repository.delete_tarjetas_by_ejemplo_id(db, ejemplo_id)
        db.commit()
        return {"status": "ok", "message": "Ejemplo eliminado"}
    return {"error": "No se pudo eliminar el ejemplo"}

@app.post("/api/ejemplos/create")
def api_crear_ejemplo(
    hanzi: str,
    pinyin: str,
    espanol: str,
    hanzi_ids: List[int],
    nivel: int = 1,
    complejidad: int = 1,
    db: Session = Depends(database.get_db)
):
    """Crea un nuevo ejemplo"""
    ejemplo = service.crear_ejemplo_completo(db, hanzi, pinyin, espanol, hanzi_ids, nivel, complejidad)
    return {
        "status": "ok",
        "ejemplo_id": ejemplo.id,
        "activado": ejemplo.activado
    }

# --- RUTAS DE API TARJETAS ---

@app.get("/api/tarjetas")
def api_ver_tarjetas(db: Session = Depends(database.get_db)):
    return service.obtener_tarjetas_completas(db)

@app.get("/api/tarjetas/estadisticas")
def api_estadisticas_tarjetas(db: Session = Depends(database.get_db)):
    return service.obtener_estadisticas_tarjetas(db)

# --- RUTAS DE API SM2 ---

@app.post("/api/sm2/session/start")
def api_iniciar_sesion(db: Session = Depends(database.get_db)):
    return service.iniciar_sesion_estudio(db)

@app.get("/api/sm2/cards/due")
def api_tarjetas_pendientes(limite: int = Query(20), db: Session = Depends(database.get_db)):
    return service.obtener_tarjetas_para_estudiar(db, limite)

@app.post("/api/sm2/review")
def api_procesar_respuesta(
    review: ReviewRequest,
    db: Session = Depends(database.get_db)
):
    """
    Procesa una respuesta del usuario
    quality: 0-2 (0=Again, 1=Hard, 2=Easy)
    """
    if review.quality < 0 or review.quality > 2:
        return {"error": "Quality debe estar entre 0 y 2"}
    
    return service.procesar_respuesta(
        db, 
        review.tarjeta_id, 
        review.session_id, 
        review.quality, 
        review.hanzi_fallados, 
        review.frase_fallada,
        review.respuesta_usuario
    )

@app.post("/api/sm2/session/end/{session_id}")
def api_finalizar_sesion(session_id: int, db: Session = Depends(database.get_db)):
    return service.finalizar_sesion_estudio(db, session_id)

@app.get("/api/sm2/statistics")
def api_estadisticas_sm2(db: Session = Depends(database.get_db)):
    return service.obtener_estadisticas_sm2(db)

@app.get("/api/sm2/progress")
def api_progreso_detallado(db: Session = Depends(database.get_db)):
    return service.obtener_progreso_detallado(db)