from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import repository

def agregar_palabra_y_generar_tarjetas(db: Session, hsk_id: int):
    palabra = repository.get_hsk_by_id(db, hsk_id)
    if not palabra:
        return None
    
    # 1. Crear entrada en diccionario
    entrada_dict = repository.create_diccionario_entry(db, hsk_id)
    
    # 2. Definir las 6 reglas según la especificación
    reglas = [
        # 1: Hanzi + Pinyin (audio) -> Español
        (palabra.hanzi, palabra.pinyin, True, "Español"),
        
        # 2: Hanzi (sin audio) -> Español
        (palabra.hanzi, "", False, "Español"),
        
        # 3: Audio solo -> Español
        ("", "", True, "Español"),
        
        # 4: Español + Pinyin (audio) -> Hanzi
        (palabra.espanol, palabra.pinyin, True, "Hanzi"),
        
        # 5: Español (audio) -> Hanzi
        (palabra.espanol, "", True, "Hanzi"),
        
        # 6: Español (sin audio) -> Hanzi
        (palabra.espanol, "", False, "Hanzi"),
    ]
    
    # 3. Aplicar reglas y crear progreso inicial para cada tarjeta
    for m1, m2, aud, req in reglas:
        tarjeta = repository.create_tarjeta(db, {
            "hsk_id": palabra.id,
            "diccionario_id": entrada_dict.id,
            "mostrado1": m1 if m1 else None,
            "mostrado2": m2 if m2 else None,
            "audio": aud,
            "requerido": req
        })
        
        # Crear progreso inicial SM2 para esta tarjeta
        repository.get_or_create_progress(db, tarjeta.id)
    
    db.commit()
    return True

def eliminar_palabra_y_tarjetas(db: Session, hsk_id: int):
    """Elimina una palabra del diccionario y todas sus tarjetas asociadas"""
    entrada = repository.get_diccionario_entry_by_hsk_id(db, hsk_id)
    if not entrada:
        return False
    
    # Primero eliminamos las tarjetas
    repository.delete_tarjetas_by_diccionario_id(db, entrada.id)
    
    # Luego eliminamos la entrada del diccionario
    repository.delete_diccionario_entry(db, entrada.id)
    
    db.commit()
    return True

def obtener_diccionario_completo(db: Session):
    """Obtiene todas las palabras del diccionario con su información completa"""
    entradas = repository.get_all_diccionario_with_hsk(db)
    
    resultado = []
    for diccionario, hsk in entradas:
        resultado.append({
            "id": diccionario.id,
            "hsk_id": hsk.id,
            "numero": hsk.numero,
            "nivel": hsk.nivel,
            "hanzi": hsk.hanzi,
            "pinyin": hsk.pinyin,
            "espanol": hsk.espanol
        })
    
    return resultado

def buscar_en_diccionario(db: Session, query: str):
    """Busca palabras en el diccionario"""
    if not query or query.strip() == "":
        return obtener_diccionario_completo(db)
    
    entradas = repository.search_diccionario(db, query)
    
    resultado = []
    for diccionario, hsk in entradas:
        resultado.append({
            "id": diccionario.id,
            "hsk_id": hsk.id,
            "numero": hsk.numero,
            "nivel": hsk.nivel,
            "hanzi": hsk.hanzi,
            "pinyin": hsk.pinyin,
            "espanol": hsk.espanol
        })
    
    return resultado

def obtener_tarjetas_completas(db: Session):
    """Obtiene todas las tarjetas con información de la palabra"""
    tarjetas = repository.get_all_tarjetas_with_info(db)
    
    resultado = []
    for tarjeta, hsk in tarjetas:
        resultado.append({
            "id": tarjeta.id,
            "hsk_id": tarjeta.hsk_id,
            "diccionario_id": tarjeta.diccionario_id,
            "hanzi": hsk.hanzi,
            "pinyin": hsk.pinyin,
            "espanol": hsk.espanol,
            "mostrado1": tarjeta.mostrado1,
            "mostrado2": tarjeta.mostrado2,
            "audio": tarjeta.audio,
            "requerido": tarjeta.requerido
        })
    
    return resultado

def obtener_estadisticas_tarjetas(db: Session):
    """Obtiene estadísticas sobre las tarjetas"""
    total_tarjetas = repository.get_tarjetas_count(db)
    total_palabras = len(repository.get_diccionario_hsk_ids(db))
    
    return {
        "total_tarjetas": total_tarjetas,
        "total_palabras_diccionario": total_palabras,
        "tarjetas_por_palabra": 6 if total_palabras > 0 else 0
    }

# === SERVICIOS SM2 ===

def calcular_sm2(quality: int, easiness: float, repetitions: int, interval: int):
    """
    Implementación del algoritmo SM2
    
    Args:
        quality: Calidad de la respuesta (0-5)
        easiness: Factor de facilidad actual (EF)
        repetitions: Número de repeticiones consecutivas correctas
        interval: Intervalo actual en días
    
    Returns:
        tuple: (new_easiness, new_repetitions, new_interval)
    """
    # Calcular nuevo factor de facilidad (EF)
    new_easiness = easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    
    # El factor de facilidad no puede ser menor a 1.3
    if new_easiness < 1.3:
        new_easiness = 1.3
    
    # Si la respuesta fue correcta (quality >= 3)
    if quality >= 3:
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = int(interval * new_easiness)
        
        new_repetitions = repetitions + 1
    else:
        # Respuesta incorrecta: reiniciar
        new_repetitions = 0
        new_interval = 1
    
    return new_easiness, new_repetitions, new_interval

def iniciar_sesion_estudio(db: Session):
    """Inicia una nueva sesión de estudio"""
    session = repository.create_sm2_session(db)
    return {
        "session_id": session.id,
        "fecha_inicio": session.fecha_inicio.isoformat()
    }

def obtener_tarjetas_para_estudiar(db: Session, limite: int = 20):
    """
    Obtiene tarjetas que necesitan revisión
    Prioriza tarjetas vencidas y nuevas
    """
    tarjetas_data = repository.get_cards_due_for_review(db, limite)
    
    resultado = []
    for tarjeta, hsk, progress in tarjetas_data:
        resultado.append({
            "tarjeta_id": tarjeta.id,
            "hanzi": hsk.hanzi,
            "pinyin": hsk.pinyin,
            "espanol": hsk.espanol,
            "mostrado1": tarjeta.mostrado1,
            "mostrado2": tarjeta.mostrado2,
            "audio": tarjeta.audio,
            "requerido": tarjeta.requerido,
            "es_nueva": progress is None or progress.total_reviews == 0,
            "repeticiones": progress.repetitions if progress else 0,
            "facilidad": progress.easiness_factor if progress else 2.5,
            "proxima_revision": progress.next_review.isoformat() if progress else None
        })
    
    return resultado

def procesar_respuesta(db: Session, tarjeta_id: int, session_id: int, quality: int):
    """
    Procesa la respuesta del usuario y actualiza el progreso según SM2
    
    Args:
        tarjeta_id: ID de la tarjeta
        session_id: ID de la sesión actual
        quality: Calidad de la respuesta (0-5)
    """
    # Obtener progreso actual
    progress = repository.get_or_create_progress(db, tarjeta_id)
    
    # Guardar valores anteriores
    prev_easiness = progress.easiness_factor
    prev_interval = progress.interval
    prev_repetitions = progress.repetitions
    
    # Calcular nuevos valores con SM2
    new_easiness, new_repetitions, new_interval = calcular_sm2(
        quality, prev_easiness, prev_repetitions, prev_interval
    )
    
    # Calcular fecha de próxima revisión
    next_review = datetime.utcnow() + timedelta(days=new_interval)
    
    # Actualizar progreso
    repository.update_progress(db, tarjeta_id, new_easiness, new_repetitions, new_interval, next_review)
    
    # Actualizar estadísticas
    is_correct = quality >= 3
    repository.increment_progress_stats(db, tarjeta_id, is_correct)
    
    # Registrar revisión
    repository.create_review(
        db, tarjeta_id, session_id, quality,
        prev_easiness, new_easiness,
        prev_interval, new_interval
    )
    
    return {
        "success": True,
        "nueva_facilidad": round(new_easiness, 2),
        "nuevo_intervalo": new_interval,
        "proxima_revision": next_review.isoformat(),
        "es_correcta": is_correct
    }

def finalizar_sesion_estudio(db: Session, session_id: int):
    """Finaliza una sesión de estudio y calcula estadísticas"""
    reviews = repository.get_reviews_by_session(db, session_id)
    
    estudiadas = len(reviews)
    correctas = sum(1 for r in reviews if r.quality >= 3)
    incorrectas = estudiadas - correctas
    
    session = repository.update_sm2_session(db, session_id, estudiadas, correctas, incorrectas)
    
    return {
        "session_id": session_id,
        "tarjetas_estudiadas": estudiadas,
        "correctas": correctas,
        "incorrectas": incorrectas,
        "porcentaje_acierto": round((correctas / estudiadas * 100) if estudiadas > 0 else 0, 1)
    }

def obtener_estadisticas_sm2(db: Session):
    """Obtiene estadísticas generales del sistema SM2"""
    stats = repository.get_sm2_statistics(db)
    
    # Tarjetas nuevas (sin progreso)
    tarjetas_nuevas = stats["total_tarjetas"] - stats["tarjetas_con_progreso"]
    
    return {
        "total_tarjetas": stats["total_tarjetas"],
        "tarjetas_estudiadas": stats["tarjetas_con_progreso"],
        "tarjetas_nuevas": tarjetas_nuevas,
        "tarjetas_pendientes_hoy": stats["tarjetas_pendientes_revision"],
        "total_revisiones": stats["total_revisiones"]
    }

def obtener_progreso_detallado(db: Session):
    """Obtiene el progreso detallado de todas las tarjetas"""
    progreso_data = repository.get_all_progress_with_cards(db)
    
    resultado = []
    for progress, tarjeta, hsk in progreso_data:
        resultado.append({
            "tarjeta_id": tarjeta.id,
            "hanzi": hsk.hanzi,
            "pinyin": hsk.pinyin,
            "espanol": hsk.espanol,
            "facilidad": round(progress.easiness_factor, 2),
            "repeticiones": progress.repetitions,
            "intervalo_dias": progress.interval,
            "proxima_revision": progress.next_review.isoformat(),
            "total_revisiones": progress.total_reviews,
            "revisiones_correctas": progress.correct_reviews,
            "tasa_acierto": round((progress.correct_reviews / progress.total_reviews * 100) 
                                  if progress.total_reviews > 0 else 0, 1),
            "ultima_revision": progress.last_review.isoformat() if progress.last_review else None
        })
    
    return resultado