from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from datetime import datetime, timezone, timedelta
created_at = datetime.now(timezone.utc)
from . import models  # <- IMPORTACIÓN RELATIVA
import json
import random
import unicodedata


# ============================================================================
# FUNCIONES HSK
# ============================================================================

def get_hsk_all(db: Session):
    return db.query(models.HSK).all()

def get_hsk_by_id(db: Session, hsk_id: int):
    return db.query(models.HSK).filter(models.HSK.id == hsk_id).first()

def normalize_text(text: str) -> str:
    """Normaliza texto removiendo acentos"""
    if not text:
        return ""
    # NFD = Decompose, Mn = Nonspacing marks (acentos)
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')

def search_hsk(db: Session, query: str):
    """Busca en HSK por hanzi, pinyin o español (normaliza acentos)"""
    if not query or not query.strip():
        return []
    
    # Función helper para normalizar texto (quitar acentos)
    def normalize(text):
        if not text:
            return ""
        nfd = unicodedata.normalize('NFD', text)
        return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    
    search_pattern = f"%{query}%"
    query_normalized = normalize(query.lower())
    
    # Primero buscar exacto en todos los campos
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
            if word.pinyin and query_normalized in normalize(word.pinyin.lower())
        ]
    
    return results

# ============================================================================
# FUNCIONES NOTAS
# ============================================================================

def get_nota_by_hsk_id(db: Session, hsk_id: int):
    """Obtiene la nota asociada a una palabra HSK"""
    return db.query(models.Notas).filter(models.Notas.hsk_id == hsk_id).first()

def create_or_update_nota(db: Session, hsk_id: int, nota_texto: str):
    """Crea o actualiza una nota para una palabra HSK"""
    nota_existente = get_nota_by_hsk_id(db, hsk_id)
    
    if nota_existente:
        # Actualizar
        nota_existente.nota = nota_texto
        nota_existente.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(nota_existente)
        return nota_existente
    else:
        # Crear
        nueva_nota = models.Notas(
            hsk_id=hsk_id,
            nota=nota_texto
        )
        db.add(nueva_nota)
        db.commit()
        db.refresh(nueva_nota)
        return nueva_nota

def delete_nota(db: Session, hsk_id: int):
    """Elimina la nota de una palabra HSK"""
    nota = get_nota_by_hsk_id(db, hsk_id)
    if nota:
        db.delete(nota)
        db.commit()
        return True
    return False

def get_all_notas(db: Session):
    """Obtiene todas las notas con información de HSK"""
    return db.query(models.Notas, models.HSK).join(
        models.HSK, models.Notas.hsk_id == models.HSK.id
    ).all()

# ============================================================================
# FUNCIONES DICCIONARIO
# ============================================================================

def get_diccionario_hsk_ids(db: Session):
    """Retorna un set con los IDs de HSK que están en el diccionario"""
    resultados = db.query(models.Diccionario.hsk_id).all()
    return {r.hsk_id for r in resultados}

def existe_en_diccionario(db: Session, hsk_id: int):
    """Verifica si una palabra HSK ya está en el diccionario"""
    return db.query(models.Diccionario).filter(models.Diccionario.hsk_id == hsk_id).first() is not None

def create_diccionario_entry(db: Session, hsk_id: int):
    nueva_entrada = models.Diccionario(hsk_id=hsk_id, activo=True)
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

def activar_diccionario_entry(db: Session, hsk_id: int):
    """Activa una entrada del diccionario"""
    entry = db.query(models.Diccionario).filter(models.Diccionario.hsk_id == hsk_id).first()
    if entry:
        entry.activo = True
        db.commit()

def desactivar_diccionario_entry(db: Session, hsk_id: int):
    """Desactiva una entrada del diccionario (cuando está cubierta por una frase)"""
    entry = db.query(models.Diccionario).filter(models.Diccionario.hsk_id == hsk_id).first()
    if entry:
        entry.activo = False
        db.commit()

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
# FUNCIONES TARJETAS
# ============================================================================

def create_tarjeta(db: Session, datos_tarjeta: dict):
    nueva_tarjeta = models.Tarjeta(**datos_tarjeta)
    db.add(nueva_tarjeta)
    db.flush()
    return nueva_tarjeta

def delete_tarjetas_by_diccionario_id(db: Session, diccionario_id: int):
    """Elimina todas las tarjetas asociadas a una entrada del diccionario"""
    db.query(models.Tarjeta).filter(models.Tarjeta.diccionario_id == diccionario_id).delete()

def delete_tarjetas_by_ejemplo_id(db: Session, ejemplo_id: int):
    """Elimina todas las tarjetas asociadas a un ejemplo"""
    db.query(models.Tarjeta).filter(models.Tarjeta.ejemplo_id == ejemplo_id).delete()

def activar_tarjeta(db: Session, tarjeta_id: int):
    """Activa una tarjeta"""
    tarjeta = db.query(models.Tarjeta).filter(models.Tarjeta.id == tarjeta_id).first()
    if tarjeta:
        tarjeta.activa = True
        db.commit()

def desactivar_tarjeta(db: Session, tarjeta_id: int):
    """Desactiva una tarjeta"""
    tarjeta = db.query(models.Tarjeta).filter(models.Tarjeta.id == tarjeta_id).first()
    if tarjeta:
        tarjeta.activa = False
        db.commit()

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

# ============================================================================
# FUNCIONES EJEMPLOS
# ============================================================================

def create_ejemplo(db: Session, hanzi: str, pinyin: str, espanol: str, nivel: int = 1, complejidad: int = 1):
    """Crea un nuevo ejemplo/frase"""
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
    return ejemplo

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
    ejemplo = db.query(models.Ejemplo).filter(models.Ejemplo.id == ejemplo_id).first()
    if ejemplo:
        ejemplo.activado = True
        db.commit()
        
        # Registrar activación
        activacion = models.EjemploActivacion(
            ejemplo_id=ejemplo_id,
            motivo=motivo,
            hanzi_ids=json.dumps(hanzi_ids)
        )
        db.add(activacion)
        db.commit()

def añadir_ejemplo_a_diccionario(db: Session, ejemplo_id: int):
    """Añade un ejemplo al diccionario del usuario"""
    ejemplo = db.query(models.Ejemplo).filter(models.Ejemplo.id == ejemplo_id).first()
    if ejemplo:
        ejemplo.en_diccionario = True
        db.commit()
        return True
    return False

def quitar_ejemplo_de_diccionario(db: Session, ejemplo_id: int):
    """Quita un ejemplo del diccionario del usuario"""
    ejemplo = db.query(models.Ejemplo).filter(models.Ejemplo.id == ejemplo_id).first()
    if ejemplo:
        ejemplo.en_diccionario = False
        db.commit()
        return True
    return False

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
        session.fecha_fin = datetime.now(timezone.utc)
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
    """Actualiza el progreso de una tarjeta"""
    progress = get_or_create_progress(db, tarjeta_id)
    progress.easiness_factor = easiness
    progress.repetitions = repetitions
    progress.interval = interval
    progress.next_review = next_review
    progress.estado = estado
    progress.last_review = datetime.now(timezone.utc)
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
            models.SM2Progress.next_review <= datetime.now(timezone.utc),
            models.SM2Progress.next_review == None
        )
    ).all()
    
    # NUEVO: Mezclar aleatoriamente
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
        models.SM2Progress.next_review <= datetime.now(timezone.utc)
    ).count()
    total_reviews = db.query(models.SM2Review).count()
    
    return {
        "total_tarjetas": total_cards,
        "tarjetas_con_progreso": cards_with_progress,
        "tarjetas_pendientes_revision": cards_due,
        "total_revisiones": total_reviews
    }