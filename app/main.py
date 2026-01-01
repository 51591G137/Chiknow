from fastapi import FastAPI, Depends, Request, Query, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text  # ✅ FIX CRÍTICO
import logging
import os

# Importamos nuestros módulos locales
from . import models, service, repository, database, schemas
from .config import config
from .logging_config import setup_logging_from_env
from .middleware import setup_middleware

# --- CAPA DE ARRANQUE ---
print("🔧 Inicializando aplicación Chiknow...")
print(f"📊 Entorno: {config.DB_ENVIRONMENT}")
print(f"📁 URL BD: {config.get_database_url()}")

# Intentar crear tablas con manejo de errores
try:
    print("🔄 Creando tablas si no existen...")
    database.Base.metadata.create_all(bind=database.engine)
    print("✅ Base de datos inicializada")
except Exception as e:
    print(f"⚠️  Advertencia al inicializar BD: {e}")
    print("ℹ️  Continuando sin tablas (puede que ya existan)")

# CREAR APP
app = FastAPI(title="Chiknow", version="1.1.0")

# ✅ Setup logging estructurado
logger = setup_logging_from_env()
logger.info("🚀 Chiknow iniciando...")

# ✅ Setup middleware (rate limiting, security headers, request logging)
setup_middleware(app, config)

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000", "https://tu-dominio.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rutas relativas al proyecto (un nivel arriba de app/)
base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
static_path = os.path.join(base_path, "static")
templates_path = os.path.join(base_path, "templates")

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# --- RUTAS DE NAVEGACIÓN (FRONTEND) ---

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

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

@app.get("/health")
def health_check(db: Session = Depends(database.get_db)):
    """Endpoint de salud mejorado para verificar que la app está funcionando"""
    health = {
        "status": "healthy",
        "environment": config.DB_ENVIRONMENT,
        "version": "1.1.0"
    }
    
    try:
        # Test de conexión a BD
        db.execute(text("SELECT 1"))
        health["database"] = "connected"
        
        # Stats adicionales
        health["stats"] = {
            "total_palabras": db.query(models.HSK).count(),
            "palabras_diccionario": db.query(models.Diccionario).count(),
            "tarjetas_activas": db.query(models.Tarjeta).filter(models.Tarjeta.activa == True).count()
        }
        
    except Exception as e:
        health["database"] = "error"
        health["database_error"] = str(e)
        if config.DB_ENVIRONMENT != "local":
            health["status"] = "unhealthy"
        logger.error(f"Health check failed: {e}")
    
    return health

# --- RUTAS DE API HSK ---

@app.get("/api/hsk")
async def api_listar_hsk(db: Session = Depends(database.get_db)):
    """
    Lista todas las palabras HSK con indicador de diccionario
    
    Returns:
        List[dict]: Lista de palabras con campos completos
    """
    try:
        logger.info("Solicitando lista completa de HSK")
        
        # Obtener datos
        palabras = repository.get_hsk_all(db)
        diccionario_ids = repository.get_diccionario_hsk_ids(db)
        
        # Construir respuesta
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
        
        logger.info(f"Devueltas {len(resultado)} palabras")
        return resultado
        
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos en api_listar_hsk: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cargar el vocabulario HSK"
        )
    except Exception as e:
        logger.error(f"Error inesperado en api_listar_hsk: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@app.get("/api/hsk/search")
async def api_buscar_hsk(query: str = Query(""), db: Session = Depends(database.get_db)):
    """Busca palabras HSK por hanzi, pinyin o español"""
    try:
        if not query or query.strip() == "":
            return await api_listar_hsk(db)
        
        # Validar query
        search_query = schemas.SearchQuery(query=query)
        
        palabras = repository.search_hsk(db, search_query.query)
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
        
        logger.info(f"Búsqueda '{query}': {len(resultado)} resultados")
        return resultado
        
    except ValueError as e:
        logger.warning(f"Query inválida: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except SQLAlchemyError as e:
        logger.error(f"Error en búsqueda: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en la búsqueda"
        )

@app.post("/api/hsk/add-traduccion/{hsk_id}")
async def api_añadir_traduccion(
    hsk_id: int, 
    traduccion: str = Query(...), 
    db: Session = Depends(database.get_db)
):
    """Añade una traducción alternativa a una palabra HSK"""
    try:
        resultado = service.añadir_traduccion_alternativa(db, hsk_id, traduccion)
        
        if "error" in resultado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=resultado["error"]
            )
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error añadiendo traducción: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al añadir traducción"
        )

# --- RUTAS DE API NOTAS ---

@app.get("/api/hsk/{hsk_id}/nota")
async def api_obtener_nota(hsk_id: int, db: Session = Depends(database.get_db)):
    """Obtiene la nota de una palabra HSK"""
    try:
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
    except Exception as e:
        logger.error(f"Error obteniendo nota: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener la nota"
        )

@app.post("/api/hsk/{hsk_id}/nota")
async def api_guardar_nota(
    hsk_id: int, 
    request: schemas.NotaRequest, 
    db: Session = Depends(database.get_db)
):
    """Crea o actualiza la nota de una palabra HSK"""
    try:
        # Verificar que la palabra HSK existe
        palabra = repository.get_hsk_by_id(db, hsk_id)
        if not palabra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Palabra HSK no encontrada"
            )
        
        # Crear o actualizar nota
        nota = repository.create_or_update_nota(db, hsk_id, request.nota)
        
        return {
            "status": "ok",
            "message": "Nota guardada",
            "hsk_id": hsk_id,
            "nota": nota.nota
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error guardando nota: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar la nota"
        )

@app.delete("/api/hsk/{hsk_id}/nota")
async def api_eliminar_nota(hsk_id: int, db: Session = Depends(database.get_db)):
    """Elimina la nota de una palabra HSK"""
    try:
        exito = repository.delete_nota(db, hsk_id)
        
        if exito:
            return {
                "status": "ok",
                "message": "Nota eliminada"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró nota para eliminar"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando nota: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar la nota"
        )

@app.get("/api/notas")
async def api_listar_notas(db: Session = Depends(database.get_db)):
    """Lista todas las notas con información de HSK"""
    try:
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
        
    except Exception as e:
        logger.error(f"Error listando notas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar notas"
        )

# --- RUTAS DE API DICCIONARIO ---

@app.post("/api/diccionario/add/{hsk_id}")
async def api_agregar_diccionario(hsk_id: int, db: Session = Depends(database.get_db)):
    """Agrega una palabra al diccionario y genera tarjetas"""
    try:
        if repository.existe_en_diccionario(db, hsk_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La palabra ya está en el diccionario"
            )
        
        exito = service.agregar_palabra_y_generar_tarjetas(db, hsk_id)
        if not exito:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo procesar la palabra"
            )
        
        logger.info(f"Palabra {hsk_id} agregada al diccionario")
        return {"status": "ok", "message": "Palabra y 6 tarjetas creadas"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error agregando al diccionario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al agregar palabra al diccionario"
        )

@app.delete("/api/diccionario/remove/{hsk_id}")
async def api_eliminar_diccionario(hsk_id: int, db: Session = Depends(database.get_db)):
    """Elimina una palabra del diccionario"""
    try:
        exito = service.eliminar_palabra_y_tarjetas(db, hsk_id)
        if not exito:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se pudo eliminar la palabra"
            )
        
        logger.info(f"Palabra {hsk_id} eliminada del diccionario")
        return {"status": "ok", "message": "Palabra eliminada del diccionario"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando del diccionario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar del diccionario"
        )

@app.get("/api/diccionario")
async def api_ver_diccionario(db: Session = Depends(database.get_db)):
    """Obtiene todas las palabras del diccionario"""
    try:
        return service.obtener_diccionario_completo(db)
    except Exception as e:
        logger.error(f"Error obteniendo diccionario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener diccionario"
        )

@app.get("/api/diccionario/search")
async def api_buscar_diccionario(query: str = Query(""), db: Session = Depends(database.get_db)):
    """Busca en el diccionario"""
    try:
        return service.buscar_en_diccionario(db, query)
    except Exception as e:
        logger.error(f"Error buscando en diccionario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en la búsqueda"
        )

# --- RUTAS DE API EJEMPLOS ---

@app.get("/api/ejemplos/todos")
async def api_todos_ejemplos(db: Session = Depends(database.get_db)):
    """Obtiene TODOS los ejemplos de la base de datos"""
    try:
        return service.obtener_todos_ejemplos(db)
    except Exception as e:
        logger.error(f"Error obteniendo ejemplos: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener ejemplos"
        )

@app.get("/api/ejemplos/por-hanzi/{hsk_id}")
async def api_ejemplos_por_hanzi(hsk_id: int, db: Session = Depends(database.get_db)):
    """Obtiene ejemplos que contienen un hanzi específico"""
    try:
        return service.obtener_ejemplos_por_hanzi(db, hsk_id)
    except Exception as e:
        logger.error(f"Error obteniendo ejemplos por hanzi: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener ejemplos"
        )

@app.get("/api/ejemplos/disponibles")
async def api_ejemplos_disponibles(db: Session = Depends(database.get_db)):
    """Obtiene ejemplos activados que el usuario puede añadir"""
    try:
        return service.obtener_ejemplos_disponibles(db)
    except Exception as e:
        logger.error(f"Error obteniendo ejemplos disponibles: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener ejemplos disponibles"
        )

@app.get("/api/ejemplos/en-estudio")
async def api_ejemplos_en_estudio(db: Session = Depends(database.get_db)):
    """Obtiene ejemplos que el usuario está estudiando"""
    try:
        return service.obtener_ejemplos_en_estudio(db)
    except Exception as e:
        logger.error(f"Error obteniendo ejemplos en estudio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener ejemplos en estudio"
        )

@app.post("/api/ejemplos/add/{ejemplo_id}")
async def api_añadir_ejemplo(ejemplo_id: int, db: Session = Depends(database.get_db)):
    """Añade un ejemplo al estudio del usuario"""
    try:
        resultado = service.añadir_ejemplo_a_estudio(db, ejemplo_id)
        
        if "error" in resultado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=resultado["error"]
            )
        
        logger.info(f"Ejemplo {ejemplo_id} añadido al estudio")
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error añadiendo ejemplo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al añadir ejemplo"
        )

@app.delete("/api/ejemplos/remove/{ejemplo_id}")
async def api_quitar_ejemplo(ejemplo_id: int, db: Session = Depends(database.get_db)):
    """Quita un ejemplo del estudio"""
    try:
        resultado = repository.quitar_ejemplo_de_diccionario(db, ejemplo_id)
        if not resultado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se pudo eliminar el ejemplo"
            )
        
        # Eliminar tarjetas asociadas
        repository.delete_tarjetas_by_ejemplo_id(db, ejemplo_id)
        db.commit()
        
        logger.info(f"Ejemplo {ejemplo_id} eliminado")
        return {"status": "ok", "message": "Ejemplo eliminado"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando ejemplo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar ejemplo"
        )

@app.post("/api/ejemplos/create")
async def api_crear_ejemplo(
    ejemplo: schemas.EjemploCreate,
    db: Session = Depends(database.get_db)
):
    """Crea un nuevo ejemplo"""
    try:
        resultado = service.crear_ejemplo_completo(
            db, 
            ejemplo.hanzi, 
            ejemplo.pinyin, 
            ejemplo.espanol, 
            ejemplo.hanzi_ids, 
            ejemplo.nivel, 
            ejemplo.complejidad
        )
        
        logger.info(f"Ejemplo creado: {ejemplo.hanzi}")
        return {
            "status": "ok",
            "ejemplo_id": resultado.id,
            "activado": resultado.activado
        }
        
    except Exception as e:
        logger.error(f"Error creando ejemplo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear ejemplo"
        )

# --- RUTAS DE API TARJETAS ---

@app.get("/api/tarjetas")
async def api_ver_tarjetas(db: Session = Depends(database.get_db)):
    """Obtiene todas las tarjetas"""
    try:
        return service.obtener_tarjetas_completas(db)
    except Exception as e:
        logger.error(f"Error obteniendo tarjetas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener tarjetas"
        )

@app.get("/api/tarjetas/estadisticas")
async def api_estadisticas_tarjetas(db: Session = Depends(database.get_db)):
    """Obtiene estadísticas de tarjetas"""
    try:
        return service.obtener_estadisticas_tarjetas(db)
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas"
        )

# --- RUTAS DE API SM2 ---

@app.post("/api/sm2/session/start")
async def api_iniciar_sesion(db: Session = Depends(database.get_db)):
    """Inicia una nueva sesión de estudio"""
    try:
        resultado = service.iniciar_sesion_estudio(db)
        logger.info(f"Sesión SM2 iniciada: {resultado['session_id']}")
        return resultado
    except Exception as e:
        logger.error(f"Error iniciando sesión: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al iniciar sesión"
        )

@app.get("/api/sm2/cards/due")
async def api_tarjetas_pendientes(
    limite: int = Query(20, ge=1, le=100), 
    db: Session = Depends(database.get_db)
):
    """Obtiene tarjetas pendientes de revisión"""
    try:
        return service.obtener_tarjetas_para_estudiar(db, limite)
    except Exception as e:
        logger.error(f"Error obteniendo tarjetas pendientes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener tarjetas"
        )

@app.post("/api/sm2/review")
async def api_procesar_respuesta(
    review: schemas.ReviewRequest,
    db: Session = Depends(database.get_db)
):
    """
    Procesa una respuesta del usuario
    quality: 0-2 (0=Again, 1=Hard, 2=Easy)
    """
    try:
        resultado = service.procesar_respuesta(
            db, 
            review.tarjeta_id, 
            review.session_id, 
            review.quality, 
            review.hanzi_fallados, 
            review.frase_fallada,
            review.respuesta_usuario
        )
        
        if "error" in resultado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=resultado["error"]
            )
        
        logger.debug(f"Respuesta procesada - Tarjeta: {review.tarjeta_id}, Quality: {review.quality}")
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando respuesta: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar respuesta"
        )

@app.post("/api/sm2/session/end/{session_id}")
async def api_finalizar_sesion(session_id: int, db: Session = Depends(database.get_db)):
    """Finaliza una sesión de estudio"""
    try:
        resultado = service.finalizar_sesion_estudio(db, session_id)
        logger.info(f"Sesión {session_id} finalizada - {resultado['tarjetas_estudiadas']} tarjetas")
        return resultado
    except Exception as e:
        logger.error(f"Error finalizando sesión: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al finalizar sesión"
        )

@app.get("/api/sm2/statistics")
async def api_estadisticas_sm2(db: Session = Depends(database.get_db)):
    """Obtiene estadísticas del sistema SM2"""
    try:
        return service.obtener_estadisticas_sm2(db)
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas SM2: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas"
        )

@app.get("/api/sm2/progress")
async def api_progreso_detallado(db: Session = Depends(database.get_db)):
    """Obtiene progreso detallado de todas las tarjetas"""
    try:
        return service.obtener_progreso_detallado(db)
    except Exception as e:
        logger.error(f"Error obteniendo progreso: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener progreso"
        )

logger.info("✅ Chiknow completamente inicializado")