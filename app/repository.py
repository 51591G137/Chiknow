from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone, timedelta
import json
import random
import logging

from . import models
from .cache import cache, invalidate_cache
from .utils import now_utc, normalize_text

logger = logging.getLogger(__name__)

# ============================================================================
# FUNCIONES HSK
# ============================================================================

@cache(ttl_seconds=300)  # ✅ Caché 5 minutos
def get_hsk_all(db: Session):
    """Obtiene todas las palabras HSK (cacheado)"""
    logger.debug("Cargando todas las palabras HSK")
    return db.query(models.HSK).all()

def get_hsk_by_id(db: Session, hsk_id: int):
    """Obtiene una palabra HSK por ID"""
    return db.query(models.HSK).filter(models.HSK.id == hsk_id).first()

def search_hsk(db: Session, query: str):
    """
    Busca en HSK por hanzi, pinyin o español
    ✅ FIX: SQL Injection prevenido con parametrización
    ✅ FIX: Usa normalize_text de utils
    """
    if not query or not query.strip():
        logger.warning("Búsqueda vacía recibida")
        return []
    
    try:
        # Sanitizar query
        query = query.strip()[:100]  # Limitar longitud
        search_pattern = f"%{query}%"
        query_normalized = normalize_text(query.lower())
        
        # Búsqueda exacta en todos los campos (segura con SQLAlchemy)
        results = db.query(models.HSK).filter(
            or_(
                models.HSK.hanzi.like(search_pattern),
                models.HSK.pinyin.like(search_pattern),
                models.HSK.espanol.like(search_pattern)
            )
        ).all()
        
        # Si no hay resultados Y la query tiene letras, buscar normalizando pinyin
        if not results and query_normalized and any(c.isalpha() for c in query_normalized):
            all_words = db.query(models.HSK).all()
            results = [
                word for word in all_words
                if word.pinyin and query_normalized in normalize_text(word.pinyin.lower())
            ]
        
        logger.info(f"Búsqueda '{query}': {len(results)} resultados")
        return results
        
    except Exception as e:
        logger.error(f"Error en búsqueda HSK: {e}", exc_info=True)
        return []

# ============================================================================
# FUNCIONES NOTAS
# ============================================================================

def get_nota_by_hsk_id(db: Session, hsk_id: int):
    """Obtiene la nota asociada a una palabra HSK"""
    return db.query(models.Notas).filter(models.Notas.hsk_id == hsk_id).first()

def create_or_update_nota(db: Session, hsk_id: int, nota_texto: str):
    """Crea o actualiza una nota para una palabra HSK"""
    try:
        nota_existente = get_nota_by_hsk_id(db, hsk_id)
        
        if nota_existente:
            nota_existente.nota = nota_texto
            nota_existente.updated_at = now_utc()  # ✅ FIX: Timezone consistente
            db.commit()
            db.refresh(nota_existente)
            logger.info(f"Nota actualizada para HSK {hsk_id}")
            return nota_existente
        else:
            nueva_nota = models.Notas(
                hsk_id=hsk_id,
                nota=nota_texto
            )
            db.add(nueva_nota)
            db.commit()
            db.refresh(nueva_nota)
            logger.info(f"Nota creada para HSK {hsk_id}")
            return nueva_nota
            
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creando/actualizando nota: {e}", exc_info=True)
        raise

def delete_nota(db: Session, hsk_id: int):
    """Elimina la nota de una palabra HSK"""
    try:
        nota = get_nota_by_hsk_id(db, hsk_id)
        if nota:
            db.delete(nota)
            db.commit()
            logger.info(f"Nota eliminada para HSK {hsk_id}")
            return True
        return False
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error eliminando nota: {e}", exc_info=True)
        raise

def get_all_notas(db: Session):
    """Obtiene todas las notas con información de HSK"""
    return db.query(models.Notas, models.HSK).join(
        models.HSK, models.Notas.hsk_id == models.HSK.id
    ).all()

# ============================================================================
# FUNCIONES DICCIONARIO
# ============================================================================

@cache(ttl_seconds=60)  # ✅ Caché 1 minuto (se actualiza frecuentemente)
def get_diccionario_hsk_ids(db: Session):
    """
    Retorna un set con los IDs de HSK que están en el diccionario
    ✅ OPTIMIZADO: Cacheado
    """
    logger.debug("Cargando IDs de diccionario")
    resultados = db.query(models.Diccionario.hsk_id).all()
    return {r.hsk_id for r in resultados}

def existe_en_diccionario(db: Session, hsk_id: int):
    """Verifica si una palabra HSK ya está en el diccionario"""
    return db.query(models.Diccionario).filter(
        models.Diccionario.hsk_id == hsk_id
    ).first() is not None

def create_diccionario_entry(db: Session, hsk_id: int):
    """Crea entrada en diccionario"""
    try:
        nueva_entrada = models.Diccionario(hsk_id=hsk_id, activo=True)
        db.add(nueva_entrada)
        db.commit()
        db.refresh(nueva_entrada)
        
        # ✅ Invalidar caché
        invalidate_cache("get_diccionario_hsk_ids")
        
        logger.info(f"Entrada creada en diccionario para HSK {hsk_id}")
        return nueva_entrada
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creando entrada en diccionario: {e}", exc_info=True)
        raise

def get_diccionario_entry_by_hsk_id(db: Session, hsk_id: int):
    """Obtiene la entrada del diccionario por hsk_id"""
    return db.query(models.Diccionario).filter(
        models.Diccionario.hsk_id == hsk_id
    ).first()

def delete_diccionario_entry(db: Session, diccionario_id: int):
    """Elimina una entrada del diccionario"""
    try:
        db.query(models.Diccionario).filter(
            models.Diccionario.id == diccionario_id
        ).delete()
        
        # ✅ Invalidar caché
        invalidate_cache("get_diccionario_hsk_ids")
        
        logger.info(f"Entrada eliminada del diccionario: {diccionario_id}")
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error eliminando entrada del diccionario: {e}", exc_info=True)
        raise

def activar_diccionario_entry(db: Session, hsk_id: int):
    """Activa una entrada del diccionario"""
    try:
        entry = db.query(models.Diccionario).filter(
            models.Diccionario.hsk_id == hsk_id
        ).first()
        if entry:
            entry.activo = True
            db.commit()
            logger.debug(f"Entrada activada en diccionario: HSK {hsk_id}")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error activando entrada: {e}", exc_info=True)
        raise

def desactivar_diccionario_entry(db: Session, hsk_id: int):
    """Desactiva una entrada del diccionario (cuando está cubierta por una frase)"""
    try:
        entry = db.query(models.Diccionario).filter(
            models.Diccionario.hsk_id == hsk_id
        ).first()
        if entry:
            entry.activo = False
            db.commit()
            logger.debug(f"Entrada desactivada en diccionario: HSK {hsk_id}")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error desactivando entrada: {e}", exc_info=True)
        raise

def get_all_diccionario_with_hsk(db: Session):
    """Obtiene todas las entradas del diccionario con información de HSK"""
    return db.query(models.Diccionario, models.HSK).join(
        models.HSK, models.Diccionario.hsk_id == models.HSK.id
    ).all()

def search_diccionario(db: Session, query: str):
    """Busca en el diccionario por hanzi, pinyin o español"""
    search_pattern = f"%{query}%"
    return db.query(models.Diccionario, models.HSK).join(
        models.HSK, models.Diccionario.hsk_id == models.HSK.id
    ).filter(
        or_(
            models.HSK.hanzi.like(search_pattern),
            models.HSK.pinyin.like(search_pattern),
            models.HSK.espanol.like(search_pattern)
        )
    ).all()

# ============================================================================
# FUNCIONES TARJETAS (MEJORADAS)
# ============================================================================

def create_tarjeta(db: Session, datos_tarjeta: dict):
    """Crea una tarjeta"""
    try:
        nueva_tarjeta = models.Tarjeta(**datos_tarjeta)
        db.add(nueva_tarjeta)
        db.flush()
        logger.debug(f"Tarjeta creada: {nueva_tarjeta.id}")
        return nueva_tarjeta
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creando tarjeta: {e}", exc_info=True)
        raise

def delete_tarjetas_by_diccionario_id(db: Session, diccionario_id: int):
    """
    Elimina todas las tarjetas asociadas a una entrada del diccionario
    ✅ MEJORADO: Maneja correctamente las dependencias de foreign keys
    """
    try:
        # 1. Obtener todas las tarjetas asociadas
        tarjetas = db.query(models.Tarjeta).filter(
            models.Tarjeta.diccionario_id == diccionario_id
        ).all()
        
        if not tarjetas:
            return True
        
        logger.info(f"Eliminando {len(tarjetas)} tarjetas del diccionario {diccionario_id}")
        
        # 2. Para cada tarjeta, eliminar dependencias en orden
        for tarjeta in tarjetas:
            # 2a. Eliminar reviews (SM2Review)
            db.query(models.SM2Review).filter(
                models.SM2Review.tarjeta_id == tarjeta.id
            ).delete(synchronize_session=False)
            
            # 2b. Eliminar progreso (SM2Progress)
            db.query(models.SM2Progress).filter(
                models.SM2Progress.tarjeta_id == tarjeta.id
            ).delete(synchronize_session=False)
        
        # 3. Ahora sí eliminar las tarjetas
        db.query(models.Tarjeta).filter(
            models.Tarjeta.diccionario_id == diccionario_id
        ).delete(synchronize_session=False)
        
        # 4. Commit de todos los cambios
        db.commit()
        logger.info(f"Tarjetas eliminadas exitosamente")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar tarjetas: {e}", exc_info=True)
        raise

def delete_tarjetas_by_ejemplo_id(db: Session, ejemplo_id: int):
    """
    Elimina todas las tarjetas asociadas a un ejemplo
    ✅ MEJORADO: Maneja correctamente las dependencias de foreign keys
    """
    try:
        tarjetas = db.query(models.Tarjeta).filter(
            models.Tarjeta.ejemplo_id == ejemplo_id
        ).all()
        
        if not tarjetas:
            return True
        
        logger.info(f"Eliminando {len(tarjetas)} tarjetas del ejemplo {ejemplo_id}")
        
        for tarjeta in tarjetas:
            db.query(models.SM2Review).filter(
                models.SM2Review.tarjeta_id == tarjeta.id
            ).delete(synchronize_session=False)
            
            db.query(models.SM2Progress).filter(
                models.SM2Progress.tarjeta_id == tarjeta.id
            ).delete(synchronize_session=False)
        
        db.query(models.Tarjeta).filter(
            models.Tarjeta.ejemplo_id == ejemplo_id
        ).delete(synchronize_session=False)
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar tarjetas de ejemplo: {e}", exc_info=True)
        raise

def delete_tarjeta_by_id(db: Session, tarjeta_id: int):
    """
    Elimina una tarjeta específica con todas sus dependencias
    """
    try:
        db.query(models.SM2Review).filter(
            models.SM2Review.tarjeta_id == tarjeta_id
        ).delete(synchronize_session=False)
        
        db.query(models.SM2Progress).filter(
            models.SM2Progress.tarjeta_id == tarjeta_id
        ).delete(synchronize_session=False)
        
        db.query(models.Tarjeta).filter(
            models.Tarjeta.id == tarjeta_id
        ).delete(synchronize_session=False)
        
        db.commit()
        logger.info(f"Tarjeta {tarjeta_id} eliminada")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar tarjeta: {e}", exc_info=True)
        raise

def activar_tarjeta(db: Session, tarjeta_id: int):
    """Activa una tarjeta"""
    try:
        tarjeta = db.query(models.Tarjeta).filter(models.Tarjeta.id == tarjeta_id).first()
        if tarjeta:
            tarjeta.activa = True
            db.commit()
            logger.debug(f"Tarjeta {tarjeta_id} activada")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error activando tarjeta: {e}", exc_info=True)
        raise

def desactivar_tarjeta(db: Session, tarjeta_id: int):
    """Desactiva una tarjeta"""
    try:
        tarjeta = db.query(models.Tarjeta).filter(models.Tarjeta.id == tarjeta_id).first()
        if tarjeta:
            tarjeta.activa = False
            db.commit()
            logger.debug(f"Tarjeta {tarjeta_id} desactivada")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error desactivando tarjeta: {e}", exc_info=True)
        raise

def get_tarjetas_by_hsk_id(db: Session, hsk_id: int):
    """Obtiene todas las tarjetas de un hanzi específico"""
    return db.query(models.Tarjeta).filter(models.Tarjeta.hsk_id == hsk_id).all()

def get_all_tarjetas_with_info(db: Session):
    """Obtiene todas las tarjetas con información completa"""
    return db.query(models.Tarjeta, models.HSK).outerjoin(
        models.HSK, models.Tarjeta.hsk_id == models.HSK.id
    ).all()

def get_tarjetas_count(db: Session):
    """Cuenta el total de tarjetas"""
    return db.query(models.Tarjeta).count()

def limpiar_registros_huerfanos(db: Session):
    """
    Limpia registros huérfanos en la base de datos
    ✅ ÚTIL: Mantenimiento de BD
    """
    try:
        logger.info("🧹 Iniciando limpieza de registros huérfanos...")
        
        # 1. SM2Review sin tarjeta
        reviews_huerfanas = db.query(models.SM2Review).outerjoin(
            models.Tarjeta, models.SM2Review.tarjeta_id == models.Tarjeta.id
        ).filter(models.Tarjeta.id == None).count()
        
        if reviews_huerfanas > 0:
            db.query(models.SM2Review).outerjoin(
                models.Tarjeta, models.SM2Review.tarjeta_id == models.Tarjeta.id
            ).filter(models.Tarjeta.id == None).delete(synchronize_session=False)
            logger.info(f"   ✓ {reviews_huerfanas} reviews huérfanas eliminadas")
        
        # 2. SM2Progress sin tarjeta
        progress_huerfanos = db.query(models.SM2Progress).outerjoin(
            models.Tarjeta, models.SM2Progress.tarjeta_id == models.Tarjeta.id
        ).filter(models.Tarjeta.id == None).count()
        
        if progress_huerfanos > 0:
            db.query(models.SM2Progress).outerjoin(
                models.Tarjeta, models.SM2Progress.tarjeta_id == models.Tarjeta.id
            ).filter(models.Tarjeta.id == None).delete(synchronize_session=False)
            logger.info(f"   ✓ {progress_huerfanos} progress huérfanos eliminados")
        
        # 3. Tarjetas sin diccionario ni ejemplo
        tarjetas_huerfanas = db.query(models.Tarjeta).filter(
            models.Tarjeta.diccionario_id == None,
            models.Tarjeta.ejemplo_id == None
        ).count()
        
        if tarjetas_huerfanas > 0:
            for tarjeta in db.query(models.Tarjeta).filter(
                models.Tarjeta.diccionario_id == None,
                models.Tarjeta.ejemplo_id == None
            ).all():
                delete_tarjeta_by_id(db, tarjeta.id)
            logger.info(f"   ✓ {tarjetas_huerfanas} tarjetas huérfanas eliminadas")
        
        db.commit()
        logger.info("✅ Limpieza completada")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error durante limpieza: {e}", exc_info=True)
        return False

# ============================================================================
# FUNCIONES EJEMPLOS
# ============================================================================

def create_ejemplo(db: Session, hanzi: str, pinyin: str, espanol: str, nivel: int = 1, complejidad: int = 1):
    """Crea un nuevo ejemplo/frase"""
    try:
        ejemplo = models.Ejemplo(
            hanzi=hanzi,
            pinyin=pinyin,
            espanol=espanol,
            nivel=nivel,
            complejidad=complejidad,
            activado=False,
            en_diccionario=False
        )
        db.add(ejemplo)
        db.commit()
        db.refresh(ejemplo)
        logger.info(f"Ejemplo creado: {hanzi}")
        return ejemplo
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creando ejemplo: {e}", exc_info=True)
        raise

def get_ejemplo_by_id(db: Session, ejemplo_id: int):
    """Obtiene un ejemplo por ID"""
    return db.query(models.Ejemplo).filter(models.Ejemplo.id == ejemplo_id).first()

def get_all_ejemplos(db: Session):
    """Obtiene todos los ejemplos"""
    return db.query(models.Ejemplo).all()

def get_ejemplos_activados(db: Session):
    """Obtiene ejemplos que están activados (todos sus hanzi dominados)"""
    return db.query(models.Ejemplo).filter(models.Ejemplo.activado == True).all()

def get_ejemplos_en_diccionario(db: Session):
    """Obtiene ejemplos añadidos al diccionario por el usuario"""
    return db.query(models.Ejemplo).filter(models.Ejemplo.en_diccionario == True).all()

def activar_ejemplo(db: Session, ejemplo_id: int, motivo: str, hanzi_ids: list):
    """Activa un ejemplo y registra la activación"""
    try:
        ejemplo = db.query(models.Ejemplo).filter(models.Ejemplo.id == ejemplo_id).first()
        if ejemplo:
            ejemplo.activado = True
            db.commit()
            
            activacion = models.EjemploActivacion(
                ejemplo_id=ejemplo_id,
                motivo=motivo,
                hanzi_ids=json.dumps(hanzi_ids)
            )
            db.add(activacion)
            db.commit()
            logger.info(f"Ejemplo {ejemplo_id} activado: {motivo}")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error activando ejemplo: {e}", exc_info=True)
        raise

def añadir_ejemplo_a_diccionario(db: Session, ejemplo_id: int):
    """Añade un ejemplo al diccionario del usuario"""
    try:
        ejemplo = db.query(models.Ejemplo).filter(models.Ejemplo.id == ejemplo_id).first()
        if ejemplo:
            ejemplo.en_diccionario = True
            db.commit()
            logger.info(f"Ejemplo {ejemplo_id} añadido al diccionario")
            return True
        return False
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error añadiendo ejemplo al diccionario: {e}", exc_info=True)
        raise

def quitar_ejemplo_de_diccionario(db: Session, ejemplo_id: int):
    """Quita un ejemplo del diccionario del usuario"""
    try:
        ejemplo = db.query(models.Ejemplo).filter(models.Ejemplo.id == ejemplo_id).first()
        if ejemplo:
            ejemplo.en_diccionario = False
            db.commit()
            logger.info(f"Ejemplo {ejemplo_id} quitado del diccionario")
            return True
        return False
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error quitando ejemplo del diccionario: {e}", exc_info=True)
        raise

# ============================================================================
# FUNCIONES HSK-EJEMPLO (Relación many-to-many)
# ============================================================================

def create_hsk_ejemplo_relacion(db: Session, hsk_id: int, ejemplo_id: int, posicion: int):
    """Crea relación entre un hanzi y un ejemplo"""
    relacion = models.HSKEjemplo(
        hsk_id=hsk_id,
        ejemplo_id=ejemplo_id,
        posicion=posicion
    )
    db.add(relacion)
    db.commit()
    return relacion

def get_hanzi_de_ejemplo(db: Session, ejemplo_id: int):
    """Obtiene todos los hanzi que componen un ejemplo (ordenados por posición)"""
    return db.query(models.HSKEjemplo, models.HSK).join(
        models.HSK, models.HSKEjemplo.hsk_id == models.HSK.id
    ).filter(
        models.HSKEjemplo.ejemplo_id == ejemplo_id
    ).order_by(models.HSKEjemplo.posicion).all()

def get_ejemplos_de_hanzi(db: Session, hsk_id: int):
    """Obtiene todos los ejemplos que contienen un hanzi específico"""
    return db.query(models.HSKEjemplo, models.Ejemplo).join(
        models.Ejemplo, models.HSKEjemplo.ejemplo_id == models.Ejemplo.id
    ).filter(
        models.HSKEjemplo.hsk_id == hsk_id
    ).all()

# ============================================================================
# FUNCIONES JERARQUÍA DE EJEMPLOS
# ============================================================================

def create_jerarquia_ejemplo(db: Session, ejemplo_complejo_id: int, ejemplo_simple_id: int):
    """Crea relación de jerarquía entre ejemplos"""
    jerarquia = models.EjemploJerarquia(
        ejemplo_complejo_id=ejemplo_complejo_id,
        ejemplo_simple_id=ejemplo_simple_id
    )
    db.add(jerarquia)
    db.commit()
    return jerarquia

def get_ejemplos_simples_contenidos(db: Session, ejemplo_complejo_id: int):
    """Obtiene ejemplos simples contenidos en un ejemplo complejo"""
    return db.query(models.EjemploJerarquia, models.Ejemplo).join(
        models.Ejemplo, models.EjemploJerarquia.ejemplo_simple_id == models.Ejemplo.id
    ).filter(
        models.EjemploJerarquia.ejemplo_complejo_id == ejemplo_complejo_id
    ).all()

def get_ejemplos_complejos_que_contienen(db: Session, ejemplo_simple_id: int):
    """Obtiene ejemplos complejos que contienen un ejemplo simple"""
    return db.query(models.EjemploJerarquia, models.Ejemplo).join(
        models.Ejemplo, models.EjemploJerarquia.ejemplo_complejo_id == models.Ejemplo.id
    ).filter(
        models.EjemploJerarquia.ejemplo_simple_id == ejemplo_simple_id
    ).all()

# ============================================================================
# FUNCIONES SM2
# ============================================================================

def create_sm2_session(db: Session):
    """Crea una nueva sesión de estudio"""
    session = models.SM2Session()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def update_sm2_session(db: Session, session_id: int, estudiadas: int, correctas: int, incorrectas: int):
    """Actualiza estadísticas de una sesión"""
    session = db.query(models.SM2Session).filter(models.SM2Session.id == session_id).first()
    if session:
        session.tarjetas_estudiadas = estudiadas
        session.tarjetas_correctas = correctas
        session.tarjetas_incorrectas = incorrectas
        session.fecha_fin = now_utc()  # ✅ FIX: Timezone consistente
        db.commit()
        db.refresh(session)
    return session

def get_sm2_session(db: Session, session_id: int):
    """Obtiene una sesión por ID"""
    return db.query(models.SM2Session).filter(models.SM2Session.id == session_id).first()

def get_recent_sessions(db: Session, limit: int = 10):
    """Obtiene las sesiones más recientes"""
    return db.query(models.SM2Session).order_by(models.SM2Session.fecha_inicio.desc()).limit(limit).all()

# ============================================================================
# FUNCIONES SM2 PROGRESS
# ============================================================================

def get_or_create_progress(db: Session, tarjeta_id: int):
    """Obtiene o crea el progreso de una tarjeta"""
    progress = db.query(models.SM2Progress).filter(models.SM2Progress.tarjeta_id == tarjeta_id).first()
    if not progress:
        progress = models.SM2Progress(tarjeta_id=tarjeta_id)
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress

def update_progress(db: Session, tarjeta_id: int, easiness: float, repetitions: int, 
                   interval: int, next_review: datetime, estado: str):
    """
    Actualiza el progreso de una tarjeta
    ✅ MEJORADO: Con locking para prevenir race conditions
    """
    try:
        # ✅ Pessimistic lock
        progress = db.query(models.SM2Progress).filter(
            models.SM2Progress.tarjeta_id == tarjeta_id
        ).with_for_update().first()
        
        if not progress:
            progress = models.SM2Progress(tarjeta_id=tarjeta_id)
            db.add(progress)
        
        progress.easiness_factor = easiness
        progress.repetitions = repetitions
        progress.interval = interval
        progress.next_review = next_review
        progress.estado = estado
        progress.last_review = now_utc()  # ✅ FIX: Timezone consistente
        
        # ✅ Optimistic locking
        progress.version += 1
        
        db.flush()  # Usar flush en lugar de commit
        logger.debug(f"Progreso actualizado para tarjeta {tarjeta_id}")
        return progress
        
    except Exception as e:
        logger.error(f"Error updating progress: {e}", exc_info=True)
        raise

def increment_progress_stats(db: Session, tarjeta_id: int, is_correct: bool):
    """Incrementa las estadísticas de una tarjeta"""
    progress = get_or_create_progress(db, tarjeta_id)
    progress.total_reviews += 1
    if is_correct:
        progress.correct_reviews += 1
    db.commit()
    return progress

def get_cards_due_for_review(db: Session, limite: int = None):
    """Obtiene tarjetas ACTIVAS que necesitan revisión (ORDEN ALEATORIO)"""
    query = db.query(models.Tarjeta, models.HSK, models.SM2Progress, models.Ejemplo).outerjoin(
        models.HSK, models.Tarjeta.hsk_id == models.HSK.id
    ).outerjoin(
        models.Ejemplo, models.Tarjeta.ejemplo_id == models.Ejemplo.id
    ).outerjoin(
        models.SM2Progress, models.Tarjeta.id == models.SM2Progress.tarjeta_id
    ).filter(
        models.Tarjeta.activa == True
    ).filter(
        or_(
            models.SM2Progress.next_review <= now_utc(),  # ✅ FIX: Timezone consistente
            models.SM2Progress.next_review == None
        )
    ).all()
    
    # Mezclar aleatoriamente
    tarjetas_list = list(query)
    random.shuffle(tarjetas_list)
    
    # Aplicar límite después de mezclar
    if limite:
        tarjetas_list = tarjetas_list[:limite]
    
    return tarjetas_list

def get_all_progress_with_cards(db: Session):
    """Obtiene todo el progreso con información de tarjetas"""
    return db.query(models.SM2Progress, models.Tarjeta, models.HSK).join(
        models.Tarjeta, models.SM2Progress.tarjeta_id == models.Tarjeta.id
    ).outerjoin(
        models.HSK, models.Tarjeta.hsk_id == models.HSK.id
    ).all()

def get_progress_by_tarjeta(db: Session, tarjeta_id: int):
    """Obtiene el progreso de una tarjeta específica"""
    return db.query(models.SM2Progress).filter(models.SM2Progress.tarjeta_id == tarjeta_id).first()

def esta_hanzi_dominado(db: Session, hsk_id: int):
    """
    Verifica si un hanzi está dominado (todas sus tarjetas en estado 'dominada' o 'madura')
    """
    tarjetas = get_tarjetas_by_hsk_id(db, hsk_id)
    
    if not tarjetas:
        return False
    
    for tarjeta in tarjetas:
        progress = get_progress_by_tarjeta(db, tarjeta.id)
        if not progress or progress.estado not in ['dominada', 'madura']:
            return False
    
    return True

# ============================================================================
# FUNCIONES SM2 REVIEWS
# ============================================================================

def create_review(db: Session, tarjeta_id: int, session_id: int, quality: int, 
                  prev_easiness: float, new_easiness: float, 
                  prev_interval: int, new_interval: int,
                  prev_estado: str, new_estado: str,
                  hanzi_fallados: list = None, frase_fallada: bool = False,
                  respuesta_usuario: str = None):
    review = models.SM2Review(
        tarjeta_id=tarjeta_id,
        session_id=session_id,
        quality=quality,
        respuesta_usuario=respuesta_usuario,
        previous_easiness=prev_easiness,
        new_easiness=new_easiness,
        previous_interval=prev_interval,
        new_interval=new_interval,
        previous_estado=prev_estado,
        new_estado=new_estado,
        hanzi_fallados=json.dumps(hanzi_fallados) if hanzi_fallados else None,
        frase_fallada=frase_fallada
    )
    db.add(review)
    db.commit()
    return review

def get_reviews_by_tarjeta(db: Session, tarjeta_id: int):
    """Obtiene el historial de revisiones de una tarjeta"""
    return db.query(models.SM2Review).filter(
        models.SM2Review.tarjeta_id == tarjeta_id
    ).order_by(models.SM2Review.fecha.desc()).all()

def get_reviews_by_session(db: Session, session_id: int):
    """Obtiene todas las revisiones de una sesión"""
    return db.query(models.SM2Review).filter(
        models.SM2Review.session_id == session_id
    ).all()

# ============================================================================
# FUNCIONES ESTADÍSTICAS
# ============================================================================

def get_sm2_statistics(db: Session):
    """Obtiene estadísticas generales del sistema SM2"""
    total_cards = db.query(models.Tarjeta).filter(models.Tarjeta.activa == True).count()
    cards_with_progress = db.query(models.SM2Progress).count()
    cards_due = db.query(models.SM2Progress).filter(
        models.SM2Progress.next_review <= now_utc()  # ✅ FIX: Timezone consistente
    ).count()
    total_reviews = db.query(models.SM2Review).count()
    
    return {
        "total_tarjetas": total_cards,
        "tarjetas_con_progreso": cards_with_progress,
        "tarjetas_pendientes_revision": cards_due,
        "total_revisiones": total_reviews
    }