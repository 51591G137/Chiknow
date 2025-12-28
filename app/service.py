from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from . import repository
from . import models
import json

# ============================================================================
# FUNCIONES DICCIONARIO
# ============================================================================

def agregar_palabra_y_generar_tarjetas(db: Session, hsk_id: int):
    palabra = repository.get_hsk_by_id(db, hsk_id)
    if not palabra:
        return None
    
    # 1. Crear entrada en diccionario
    entrada_dict = repository.create_diccionario_entry(db, hsk_id)
    
    # 2. Definir las 6 reglas
    reglas = [
        (palabra.hanzi, palabra.pinyin, True, palabra.espanol),
        (palabra.hanzi, "", False, palabra.espanol),
        ("", "", True, palabra.espanol),
        (palabra.espanol, palabra.pinyin, True, palabra.hanzi),
        (palabra.espanol, "", True, palabra.hanzi),
        (palabra.espanol, "", False, palabra.hanzi),
    ]
    
    # 3. Crear tarjetas y progreso inicial
    for m1, m2, aud, req in reglas:
        tarjeta = repository.create_tarjeta(db, {
            "hsk_id": palabra.id,
            "diccionario_id": entrada_dict.id,
            "ejemplo_id": None,
            "mostrado1": m1 if m1 else None,
            "mostrado2": m2 if m2 else None,
            "audio": aud,
            "requerido": req,
            "activa": True
        })
        repository.get_or_create_progress(db, tarjeta.id)
    
    db.commit()
    
    # 4. Verificar si este hanzi activa algún ejemplo
    verificar_y_activar_ejemplos(db)
    
    return True

def eliminar_palabra_y_tarjetas(db: Session, hsk_id: int):
    """Elimina una palabra del diccionario y todas sus tarjetas asociadas"""
    entrada = repository.get_diccionario_entry_by_hsk_id(db, hsk_id)
    if not entrada:
        return False
    
    repository.delete_tarjetas_by_diccionario_id(db, entrada.id)
    repository.delete_diccionario_entry(db, entrada.id)
    
    db.commit()
    return True

def obtener_diccionario_completo(db: Session):
    """Obtiene todas las palabras del diccionario"""
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
            "espanol": hsk.espanol,
            "activo": diccionario.activo
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
            "espanol": hsk.espanol,
            "activo": diccionario.activo
        })
    
    return resultado

def añadir_traduccion_alternativa(db: Session, hsk_id: int, traduccion: str):
    palabra = repository.get_hsk_by_id(db, hsk_id)
    
    if not palabra:
        return {"error": "Palabra no encontrada"}
    
    traducciones_actuales = [t.strip() for t in palabra.espanol.split(',')]
    traduccion_limpia = traduccion.strip()
    
    if traduccion_limpia in traducciones_actuales:
        return {"error": "La traducción ya existe"}
    
    # Añadir traducción
    nuevo_espanol = palabra.espanol + ", " + traduccion_limpia
    palabra.espanol = nuevo_espanol
    db.commit()
    
    # Actualizar todas las tarjetas asociadas a esta palabra
    actualizar_tarjetas_por_hsk_id(db, hsk_id, nuevo_espanol)
    
    return {
        "status": "ok",
        "message": "Traducción añadida",
        "espanol": nuevo_espanol
    }

def actualizar_tarjetas_por_hsk_id(db: Session, hsk_id: int, nuevo_requerido: str):
    """
    Actualiza el campo 'requerido' de todas las tarjetas asociadas a un hsk_id
    manteniendo el progreso SM2 y los IDs originales
    """
    # Buscar todas las tarjetas asociadas a este hsk_id
    tarjetas = db.query(models.Tarjeta).filter(
        models.Tarjeta.hsk_id == hsk_id
    ).all()
    
    for tarjeta in tarjetas:
        # Determinar el nuevo valor para 'requerido' basado en el tipo de tarjeta
        if tarjeta.mostrado1 and tarjeta.mostrado1 == tarjeta.requerido:
            # Tarjeta de tipo: Español → Hanzi (requerido es hanzi, no cambiar)
            pass  # No cambiar, el hanzi sigue siendo el mismo
        elif tarjeta.mostrado1 and any(trad in tarjeta.mostrado1 for trad in ['espanol', 'español']):
            # Tarjeta de tipo: Hanzi → Español (requerido es español, actualizar)
            tarjeta.requerido = nuevo_requerido
        elif not tarjeta.mostrado1 and not tarjeta.mostrado2 and tarjeta.audio:
            # Tarjeta de tipo: Audio → Español (requerido es español, actualizar)
            tarjeta.requerido = nuevo_requerido
    
    db.commit()

# ============================================================================
# FUNCIONES EJEMPLOS
# ============================================================================

def crear_ejemplo_completo(db: Session, hanzi: str, pinyin: str, espanol: str, 
                          hanzi_ids: list, nivel: int = 1, complejidad: int = 1):
    """
    Crea un ejemplo completo con sus relaciones a hanzi
    
    Args:
        hanzi_ids: lista de IDs de HSK que componen la frase en orden
    """
    # 1. Crear el ejemplo
    ejemplo = repository.create_ejemplo(db, hanzi, pinyin, espanol, nivel, complejidad)
    
    # 2. Crear relaciones con los hanzi
    for posicion, hsk_id in enumerate(hanzi_ids, start=1):
        repository.create_hsk_ejemplo_relacion(db, hsk_id, ejemplo.id, posicion)
    
    # 3. Verificar si debe activarse automáticamente
    verificar_y_activar_ejemplo_individual(db, ejemplo.id)
    
    db.commit()
    return ejemplo

def verificar_y_activar_ejemplos(db: Session):
    """
    Verifica todos los ejemplos y activa aquellos cuyos hanzi están dominados
    """
    ejemplos = db.query(models.Ejemplo).filter(
        models.Ejemplo.activado == False
    ).all()
    
    for ejemplo in ejemplos:
        verificar_y_activar_ejemplo_individual(db, ejemplo.id)

def verificar_y_activar_ejemplo_individual(db: Session, ejemplo_id: int):
    """
    Verifica si un ejemplo debe activarse (todos sus hanzi están dominados)
    """
    # Obtener todos los hanzi del ejemplo
    hanzi_relaciones = repository.get_hanzi_de_ejemplo(db, ejemplo_id)
    
    if not hanzi_relaciones:
        return False
    
    # Verificar si todos los hanzi están dominados
    hanzi_ids = []
    todos_dominados = True
    
    for relacion, hsk in hanzi_relaciones:
        hanzi_ids.append(hsk.id)
        if not repository.esta_hanzi_dominado(db, hsk.id):
            todos_dominados = False
            break
    
    # Si todos están dominados, activar el ejemplo
    if todos_dominados:
        repository.activar_ejemplo(db, ejemplo_id, "hanzi_dominados", hanzi_ids)
        return True
    
    return False

def añadir_ejemplo_a_estudio(db: Session, ejemplo_id: int):
    """
    Añade un ejemplo al estudio del usuario (genera tarjetas)
    """
    ejemplo = repository.get_ejemplo_by_id(db, ejemplo_id)
    if not ejemplo or not ejemplo.activado:
        return {"error": "El ejemplo no está activado o no existe"}
    
    # Marcar como en diccionario
    repository.añadir_ejemplo_a_diccionario(db, ejemplo_id)
    
    # Generar las 6 tarjetas para el ejemplo
    reglas = [
        (ejemplo.hanzi, ejemplo.pinyin, True, ejemplo.espanol),
        (ejemplo.hanzi, "", False, ejemplo.espanol),
        ("", "", True, ejemplo.espanol),
        (ejemplo.espanol, ejemplo.pinyin, True, ejemplo.hanzi),
        (ejemplo.espanol, "", True, ejemplo.hanzi),
        (ejemplo.espanol, "", False, ejemplo.hanzi),
    ]
    
    for m1, m2, aud, req in reglas:
        tarjeta = repository.create_tarjeta(db, {
            "hsk_id": None,
            "diccionario_id": None,
            "ejemplo_id": ejemplo.id,
            "mostrado1": m1 if m1 else None,
            "mostrado2": m2 if m2 else None,
            "audio": aud,
            "requerido": req,
            "activa": True
        })
        repository.get_or_create_progress(db, tarjeta.id)
    
    db.commit()
    
    # Verificar jerarquía y desactivar tarjetas de hanzi si procede
    gestionar_desactivacion_por_ejemplo(db, ejemplo_id)
    
    return {"status": "ok", "message": "Ejemplo añadido al estudio"}

def gestionar_desactivacion_por_ejemplo(db: Session, ejemplo_id: int):
    """
    Cuando un ejemplo está dominado, desactiva las tarjetas de sus hanzi componentes
    """
    # Obtener hanzi del ejemplo
    hanzi_relaciones = repository.get_hanzi_de_ejemplo(db, ejemplo_id)
    
    # Verificar si el ejemplo está dominado
    ejemplo = repository.get_ejemplo_by_id(db, ejemplo_id)
    if not esta_ejemplo_dominado(db, ejemplo_id):
        return
    
    # Desactivar tarjetas de cada hanzi
    for relacion, hsk in hanzi_relaciones:
        # Desactivar entrada en diccionario
        repository.desactivar_diccionario_entry(db, hsk.id)
        
        # Desactivar todas las tarjetas del hanzi
        tarjetas = repository.get_tarjetas_by_hsk_id(db, hsk.id)
        for tarjeta in tarjetas:
            repository.desactivar_tarjeta(db, tarjeta.id)
    
    # Gestionar jerarquía: desactivar ejemplos simples contenidos
    ejemplos_simples = repository.get_ejemplos_simples_contenidos(db, ejemplo_id)
    for jerarquia, ejemplo_simple in ejemplos_simples:
        # Desactivar tarjetas del ejemplo simple
        tarjetas_simple = db.query(models.Tarjeta).filter(
            models.Tarjeta.ejemplo_id == ejemplo_simple.id
        ).all()
        for tarjeta in tarjetas_simple:
            repository.desactivar_tarjeta(db, tarjeta.id)

def esta_ejemplo_dominado(db: Session, ejemplo_id: int):
    """
    Verifica si un ejemplo está dominado (todas sus tarjetas en estado dominada/madura)
    """
    tarjetas = db.query(models.Tarjeta).filter(
        models.Tarjeta.ejemplo_id == ejemplo_id
    ).all()
    
    if not tarjetas:
        return False
    
    for tarjeta in tarjetas:
        progress = repository.get_progress_by_tarjeta(db, tarjeta.id)
        if not progress or progress.estado not in ['dominada', 'madura']:
            return False
    
    return True

def reactivar_hanzi_desde_ejemplo(db: Session, ejemplo_id: int, hanzi_fallados: list):
    """
    Reactiva las tarjetas de hanzi específicos que fallaron en un ejemplo
    
    Args:
        hanzi_fallados: lista de hanzi (caracteres) que fallaron
    """
    # Obtener todos los hanzi del ejemplo
    hanzi_relaciones = repository.get_hanzi_de_ejemplo(db, ejemplo_id)
    
    for relacion, hsk in hanzi_relaciones:
        if hsk.hanzi in hanzi_fallados:
            # Reactivar entrada en diccionario
            repository.activar_diccionario_entry(db, hsk.id)
            
            # Reactivar todas las tarjetas del hanzi
            tarjetas = repository.get_tarjetas_by_hsk_id(db, hsk.id)
            for tarjeta in tarjetas:
                repository.activar_tarjeta(db, tarjeta.id)
                
                # Reiniciar progreso de la tarjeta
                progress = repository.get_progress_by_tarjeta(db, tarjeta.id)
                if progress:
                    repository.update_progress(
                        db, tarjeta.id, 
                        easiness=2.5, 
                        repetitions=0, 
                        interval=0,
                        next_review=datetime.utcnow(),
                        estado="aprendiendo"
                    )
    
    db.commit()

def obtener_ejemplos_disponibles(db: Session):
    """Obtiene ejemplos activados que el usuario puede añadir"""
    ejemplos = repository.get_ejemplos_activados(db)
    
    resultado = []
    for ejemplo in ejemplos:
        # Obtener hanzi componentes
        hanzi_relaciones = repository.get_hanzi_de_ejemplo(db, ejemplo.id)
        hanzi_lista = [hsk.hanzi for rel, hsk in hanzi_relaciones]
        
        resultado.append({
            "id": ejemplo.id,
            "hanzi": ejemplo.hanzi,
            "pinyin": ejemplo.pinyin,
            "espanol": ejemplo.espanol,
            "nivel": ejemplo.nivel,
            "complejidad": ejemplo.complejidad,
            "en_diccionario": ejemplo.en_diccionario,
            "hanzi_componentes": hanzi_lista
        })
    
    return resultado

def obtener_ejemplos_en_estudio(db: Session):
    """Obtiene ejemplos que el usuario está estudiando"""
    ejemplos = repository.get_ejemplos_en_diccionario(db)
    
    resultado = []
    for ejemplo in ejemplos:
        # Obtener progreso
        tarjetas = db.query(models.Tarjeta).filter(
            models.Tarjeta.ejemplo_id == ejemplo.id
        ).all()
        
        dominado = esta_ejemplo_dominado(db, ejemplo.id) if tarjetas else False
        
        resultado.append({
            "id": ejemplo.id,
            "hanzi": ejemplo.hanzi,
            "pinyin": ejemplo.pinyin,
            "espanol": ejemplo.espanol,
            "nivel": ejemplo.nivel,
            "complejidad": ejemplo.complejidad,
            "dominado": dominado,
            "num_tarjetas": len(tarjetas)
        })
    
    return resultado

def obtener_todos_ejemplos(db: Session):
    ejemplos = db.query(models.Ejemplo).all()
    
    resultado = []
    for ejemplo in ejemplos:
        hanzi_relaciones = repository.get_hanzi_de_ejemplo(db, ejemplo.id)
        hanzi_lista = [hsk.hanzi for rel, hsk in hanzi_relaciones]
        
        num_tarjetas = db.query(models.Tarjeta).filter(
            models.Tarjeta.ejemplo_id == ejemplo.id
        ).count()
        
        resultado.append({
            "id": ejemplo.id,
            "hanzi": ejemplo.hanzi,
            "pinyin": ejemplo.pinyin,
            "espanol": ejemplo.espanol,
            "nivel": ejemplo.nivel,
            "complejidad": ejemplo.complejidad,
            "activado": ejemplo.activado,
            "en_diccionario": ejemplo.en_diccionario,
            "hanzi_componentes": hanzi_lista,
            "num_tarjetas": num_tarjetas
        })
    
    return resultado

def obtener_ejemplos_por_hanzi(db: Session, hsk_id: int):
    relaciones = db.query(models.HSKEjemplo, models.Ejemplo).join(
        models.Ejemplo, models.HSKEjemplo.ejemplo_id == models.Ejemplo.id
    ).filter(
        models.HSKEjemplo.hsk_id == hsk_id
    ).all()
    
    resultado = []
    for rel, ejemplo in relaciones:
        hanzi_relaciones = repository.get_hanzi_de_ejemplo(db, ejemplo.id)
        hanzi_lista = [hsk.hanzi for rel_inner, hsk in hanzi_relaciones]
        
        resultado.append({
            "id": ejemplo.id,
            "hanzi": ejemplo.hanzi,
            "pinyin": ejemplo.pinyin,
            "espanol": ejemplo.espanol,
            "nivel": ejemplo.nivel,
            "complejidad": ejemplo.complejidad,
            "activado": ejemplo.activado,
            "en_diccionario": ejemplo.en_diccionario,
            "hanzi_componentes": hanzi_lista
        })
    
    return resultado

# ============================================================================
# FUNCIONES TARJETAS
# ============================================================================

def obtener_tarjetas_completas(db: Session):
    """Obtiene todas las tarjetas con información"""
    tarjetas = repository.get_all_tarjetas_with_info(db)
    
    resultado = []
    for tarjeta, hsk in tarjetas:
        # Solo procesar tarjetas de palabras (no ejemplos por ahora)
        if tarjeta.hsk_id and hsk:
            resultado.append({
                "id": tarjeta.id,
                "hsk_id": tarjeta.hsk_id,
                "diccionario_id": tarjeta.diccionario_id,
                "ejemplo_id": tarjeta.ejemplo_id,
                "hanzi": hsk.hanzi,
                "pinyin": hsk.pinyin,
                "espanol": hsk.espanol,
                "mostrado1": tarjeta.mostrado1,
                "mostrado2": tarjeta.mostrado2,
                "audio": tarjeta.audio,
                "requerido": tarjeta.requerido,
                "activa": tarjeta.activa
            })
    
    return resultado

def obtener_estadisticas_tarjetas(db: Session):
    """Obtiene estadísticas sobre las tarjetas"""
    total_tarjetas = repository.get_tarjetas_count(db)
    total_palabras = len(repository.get_diccionario_hsk_ids(db))
    total_ejemplos = len(repository.get_ejemplos_en_diccionario(db))
    
    return {
        "total_tarjetas": total_tarjetas,
        "total_palabras_diccionario": total_palabras,
        "total_ejemplos_diccionario": total_ejemplos,
        "tarjetas_por_palabra": 6 if total_palabras > 0 else 0
    }

# ============================================================================
# FUNCIONES SM2
# ============================================================================

def calcular_sm2_simplificado(quality: int, easiness: float, repetitions: int, interval: int):
    """
    Algoritmo SM2 modificado para escala 0-2
    
    Args:
        quality: 0=Again, 1=Hard, 2=Easy
        easiness: Factor de facilidad actual
        repetitions: Repeticiones consecutivas correctas
        interval: Intervalo actual en días
    
    Returns:
        tuple: (new_easiness, new_repetitions, new_interval, new_estado)
    """
    # Mapeo de quality 0-2 a escala original 0-5 para el cálculo
    quality_map = {
        0: 0,  # Again -> 0 (olvidé completamente)
        1: 3,  # Hard -> 3 (recordé con dificultad)
        2: 5   # Easy -> 5 (perfecto)
    }
    
    q_original = quality_map[quality]
    
    # Calcular nuevo factor de facilidad
    new_easiness = easiness + (0.1 - (5 - q_original) * (0.08 + (5 - q_original) * 0.02))
    
    # Límite mínimo de facilidad
    if new_easiness < 1.3:
        new_easiness = 1.3
    
    # Calcular estado y siguiente intervalo
    if quality >= 1:  # Hard o Easy (recordó)
        if repetitions == 0:
            new_interval = 1
            new_estado = "aprendiendo"
        elif repetitions == 1:
            new_interval = 6
            new_estado = "aprendiendo"
        elif repetitions == 2:
            new_interval = int(6 * new_easiness)
            new_estado = "aprendiendo"
        else:
            new_interval = int(interval * new_easiness)
            # Determinar estado según intervalo
            if new_interval >= 60:
                new_estado = "madura"
            elif new_interval >= 21:
                new_estado = "dominada"
            else:
                new_estado = "aprendiendo"
        
        new_repetitions = repetitions + 1
        
        # Ajuste por dificultad
        if quality == 1:  # Hard
            new_interval = max(1, int(new_interval * 0.7))  # Reducir 30%
    else:  # Again (olvidó)
        new_repetitions = 0
        new_interval = 1
        new_estado = "aprendiendo"
    
    return new_easiness, new_repetitions, new_interval, new_estado

def iniciar_sesion_estudio(db: Session):
    """Inicia una nueva sesión de estudio"""
    session = repository.create_sm2_session(db)
    return {
        "session_id": session.id,
        "fecha_inicio": session.fecha_inicio.isoformat()
    }

def obtener_tarjetas_para_estudiar(db: Session, limite: int = 20):
    """Obtiene tarjetas ACTIVAS que necesitan revisión"""
    tarjetas_data = repository.get_cards_due_for_review(db, limite)
    
    resultado = []
    for tarjeta, hsk, progress, ejemplo in tarjetas_data:
        # Determinar si es palabra o ejemplo
        if tarjeta.hsk_id:
            # Es una palabra
            resultado.append({
                "tarjeta_id": tarjeta.id,
                "tipo": "palabra",
                "hsk_id": hsk.id,
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
                "estado": progress.estado if progress else "nuevo",
                "proxima_revision": progress.next_review.isoformat() if progress else None
            })
        elif tarjeta.ejemplo_id:
            # Es un ejemplo
            # Obtener hanzi componentes
            hanzi_relaciones = repository.get_hanzi_de_ejemplo(db, ejemplo.id)
            hanzi_componentes = [hsk_rel.hanzi for rel, hsk_rel in hanzi_relaciones]
            
            resultado.append({
                "tarjeta_id": tarjeta.id,
                "tipo": "ejemplo",
                "ejemplo_id": ejemplo.id,
                "hanzi": ejemplo.hanzi,
                "pinyin": ejemplo.pinyin,
                "espanol": ejemplo.espanol,
                "hanzi_componentes": hanzi_componentes,
                "mostrado1": tarjeta.mostrado1,
                "mostrado2": tarjeta.mostrado2,
                "audio": tarjeta.audio,
                "requerido": tarjeta.requerido,
                "es_nueva": progress is None or progress.total_reviews == 0,
                "repeticiones": progress.repetitions if progress else 0,
                "facilidad": progress.easiness_factor if progress else 2.5,
                "estado": progress.estado if progress else "nuevo",
                "proxima_revision": progress.next_review.isoformat() if progress else None
            })
    
    return resultado

def procesar_respuesta(db: Session, tarjeta_id: int, session_id: int, quality: int,
                      hanzi_fallados: list = None, frase_fallada: bool = False,
                      respuesta_usuario: str = None):
    """
    Procesa la respuesta del usuario (escala 0-2)
    
    Args:
        quality: 0=Again, 1=Hard, 2=Easy
        hanzi_fallados: Lista de hanzi que fallaron (solo para ejemplos)
        frase_fallada: Si falló la estructura de la frase (solo para ejemplos)
    """
    if quality < 0 or quality > 2:
        return {"error": "Quality debe estar entre 0 y 2"}
    
    # Obtener tarjeta y progreso
    tarjeta = db.query(models.Tarjeta).filter(
        models.Tarjeta.id == tarjeta_id
    ).first()
    
    if not tarjeta:
        return {"error": "Tarjeta no encontrada"}
    
    progress = repository.get_or_create_progress(db, tarjeta_id)
    
    # Guardar valores anteriores
    prev_easiness = progress.easiness_factor
    prev_interval = progress.interval
    prev_repetitions = progress.repetitions
    prev_estado = progress.estado
    
    # Calcular nuevos valores con SM2
    new_easiness, new_repetitions, new_interval, new_estado = calcular_sm2_simplificado(
        quality, prev_easiness, prev_repetitions, prev_interval
    )
    
    # Calcular fecha de próxima revisión
    next_review = datetime.utcnow() + timedelta(days=new_interval)
    
    # Actualizar progreso
    repository.update_progress(db, tarjeta_id, new_easiness, new_repetitions, 
                              new_interval, next_review, new_estado)
    
    # Actualizar estadísticas
    is_correct = quality >= 1
    repository.increment_progress_stats(db, tarjeta_id, is_correct)
    
    # Registrar revisión
    repository.create_review(
        db, tarjeta_id, session_id, quality,
        prev_easiness, new_easiness,
        prev_interval, new_interval,
        prev_estado, new_estado,
        hanzi_fallados, frase_fallada,
        respuesta_usuario
    )
    
    # Si es un ejemplo y fallaron hanzi específicos, reactivarlos
    if tarjeta.ejemplo_id and hanzi_fallados and len(hanzi_fallados) > 0:
        reactivar_hanzi_desde_ejemplo(db, tarjeta.ejemplo_id, hanzi_fallados)
    
    # Si es un ejemplo y ahora está dominado, gestionar desactivaciones
    if tarjeta.ejemplo_id and new_estado in ['dominada', 'madura']:
        gestionar_desactivacion_por_ejemplo(db, tarjeta.ejemplo_id)
    
    # Si es un hanzi y ahora está dominado, verificar ejemplos
    if tarjeta.hsk_id and new_estado in ['dominada', 'madura']:
        verificar_y_activar_ejemplos(db)
    
    return {
        "success": True,
        "nueva_facilidad": round(new_easiness, 2),
        "nuevo_intervalo": new_interval,
        "nuevo_estado": new_estado,
        "proxima_revision": next_review.isoformat(),
        "es_correcta": is_correct
    }

def finalizar_sesion_estudio(db: Session, session_id: int):
    """Finaliza una sesión de estudio y calcula estadísticas"""
    reviews = repository.get_reviews_by_session(db, session_id)
    
    estudiadas = len(reviews)
    correctas = sum(1 for r in reviews if r.quality >= 1)
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
            "tipo": "palabra" if tarjeta.hsk_id else "ejemplo",
            "hanzi": hsk.hanzi if hsk else None,
            "pinyin": hsk.pinyin if hsk else None,
            "espanol": hsk.espanol if hsk else None,
            "facilidad": round(progress.easiness_factor, 2),
            "repeticiones": progress.repetitions,
            "intervalo_dias": progress.interval,
            "estado": progress.estado,
            "proxima_revision": progress.next_review.isoformat(),
            "total_revisiones": progress.total_reviews,
            "revisiones_correctas": progress.correct_reviews,
            "tasa_acierto": round((progress.correct_reviews / progress.total_reviews * 100) 
                                  if progress.total_reviews > 0 else 0, 1),
            "ultima_revision": progress.last_review.isoformat() if progress.last_review else None,
            "activa": tarjeta.activa
        })
    
    return resultado