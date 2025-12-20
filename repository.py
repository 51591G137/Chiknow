from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime
import models

# === FUNCIONES HSK ===
def get_hsk_all(db: Session):
    return db.query(models.HSK).all()

def get_hsk_by_id(db: Session, hsk_id: int):
    return db.query(models.HSK).filter(models.HSK.id == hsk_id).first()

def search_hsk(db: Session, query: str):
    """Busca en HSK por hanzi, pinyin o español"""
    search_pattern = f"%{query}%"
    return db.query(models.HSK).filter(
        or_(
            models.HSK.hanzi.like(search_pattern),
            models.HSK.pinyin.like(search_pattern),
            models.HSK.espanol.like(search_pattern)
        )
    ).all()

# === FUNCIONES DICCIONARIO ===
def get_diccionario_hsk_ids(db: Session):
    """Retorna un set con los IDs de HSK que están en el diccionario"""
    resultados = db.query(models.Diccionario.hsk_id).all()
    return {r.hsk_id for r in resultados}

def existe_en_diccionario(db: Session, hsk_id: int):
    """Verifica si una palabra HSK ya está en el diccionario"""
    return db.query(models.Diccionario).filter(models.Diccionario.hsk_id == hsk_id).first() is not None

def create_diccionario_entry(db: Session, hsk_id: int):
    nueva_entrada = models.Diccionario(hsk_id=hsk_id)
    db.add(nueva_entrada)
    db.commit()
    db.refresh(nueva_entrada)
    return nueva_entrada

def get_diccionario_entry_by_hsk_id(db: Session, hsk_id: int):
    """Obtiene la entrada del diccionario por hsk_id"""
    return db.query(models.Diccionario).filter(models.Diccionario.hsk_id == hsk_id).first()

def delete_diccionario_entry(db: Session, diccionario_id: int):
    """Elimina una entrada del diccionario"""
    db.query(models.Diccionario).filter(models.Diccionario.id == diccionario_id).delete()

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

# === FUNCIONES TARJETAS ===
def create_tarjeta(db: Session, datos_tarjeta: dict):
    nueva_tarjeta = models.Tarjeta(**datos_tarjeta)
    db.add(nueva_tarjeta)
    db.flush()  # Para obtener el ID sin hacer commit
    return nueva_tarjeta

def delete_tarjetas_by_diccionario_id(db: Session, diccionario_id: int):
    """Elimina todas las tarjetas asociadas a una entrada del diccionario"""
    db.query(models.Tarjeta).filter(models.Tarjeta.diccionario_id == diccionario_id).delete()

def get_all_tarjetas_with_info(db: Session):
    """Obtiene todas las tarjetas con información completa"""
    return db.query(models.Tarjeta, models.HSK).join(
        models.HSK, models.Tarjeta.hsk_id == models.HSK.id
    ).all()

def get_tarjetas_count(db: Session):
    """Cuenta el total de tarjetas"""
    return db.query(models.Tarjeta).count()

# === FUNCIONES SM2 ===

# --- Sesiones ---
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
        session.fecha_fin = datetime.utcnow()
        db.commit()
        db.refresh(session)
    return session

def get_sm2_session(db: Session, session_id: int):
    """Obtiene una sesión por ID"""
    return db.query(models.SM2Session).filter(models.SM2Session.id == session_id).first()

def get_recent_sessions(db: Session, limit: int = 10):
    """Obtiene las sesiones más recientes"""
    return db.query(models.SM2Session).order_by(models.SM2Session.fecha_inicio.desc()).limit(limit).all()

# --- Progress ---
def get_or_create_progress(db: Session, tarjeta_id: int):
    """Obtiene o crea el progreso de una tarjeta"""
    progress = db.query(models.SM2Progress).filter(models.SM2Progress.tarjeta_id == tarjeta_id).first()
    if not progress:
        progress = models.SM2Progress(tarjeta_id=tarjeta_id)
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress

def update_progress(db: Session, tarjeta_id: int, easiness: float, repetitions: int, interval: int, next_review: datetime):
    """Actualiza el progreso de una tarjeta"""
    progress = get_or_create_progress(db, tarjeta_id)
    progress.easiness_factor = easiness
    progress.repetitions = repetitions
    progress.interval = interval
    progress.next_review = next_review
    progress.last_review = datetime.utcnow()
    db.commit()
    return progress

def increment_progress_stats(db: Session, tarjeta_id: int, is_correct: bool):
    """Incrementa las estadísticas de una tarjeta"""
    progress = get_or_create_progress(db, tarjeta_id)
    progress.total_reviews += 1
    if is_correct:
        progress.correct_reviews += 1
    db.commit()
    return progress

def get_cards_due_for_review(db: Session, limit: int = None):
    """Obtiene tarjetas que necesitan revisión (fecha <= ahora)"""
    query = db.query(models.Tarjeta, models.HSK, models.SM2Progress).join(
        models.HSK, models.Tarjeta.hsk_id == models.HSK.id
    ).outerjoin(
        models.SM2Progress, models.Tarjeta.id == models.SM2Progress.tarjeta_id
    ).filter(
        or_(
            models.SM2Progress.next_review <= datetime.utcnow(),
            models.SM2Progress.next_review == None
        )
    ).order_by(models.SM2Progress.next_review.asc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()

def get_all_progress_with_cards(db: Session):
    """Obtiene todo el progreso con información de tarjetas"""
    return db.query(models.SM2Progress, models.Tarjeta, models.HSK).join(
        models.Tarjeta, models.SM2Progress.tarjeta_id == models.Tarjeta.id
    ).join(
        models.HSK, models.Tarjeta.hsk_id == models.HSK.id
    ).all()

# --- Reviews ---
def create_review(db: Session, tarjeta_id: int, session_id: int, quality: int, 
                  prev_easiness: float, new_easiness: float, 
                  prev_interval: int, new_interval: int):
    """Registra una revisión"""
    review = models.SM2Review(
        tarjeta_id=tarjeta_id,
        session_id=session_id,
        quality=quality,
        previous_easiness=prev_easiness,
        new_easiness=new_easiness,
        previous_interval=prev_interval,
        new_interval=new_interval
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

# === ESTADÍSTICAS ===
def get_sm2_statistics(db: Session):
    """Obtiene estadísticas generales del sistema SM2"""
    total_cards = db.query(models.Tarjeta).count()
    cards_with_progress = db.query(models.SM2Progress).count()
    cards_due = db.query(models.SM2Progress).filter(
        models.SM2Progress.next_review <= datetime.utcnow()
    ).count()
    total_reviews = db.query(models.SM2Review).count()
    
    return {
        "total_tarjetas": total_cards,
        "tarjetas_con_progreso": cards_with_progress,
        "tarjetas_pendientes_revision": cards_due,
        "total_revisiones": total_reviews
    }