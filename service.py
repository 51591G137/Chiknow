from sqlalchemy.orm import Session
import repository

def agregar_palabra_y_generar_tarjetas(db: Session, hsk_id: int):
    palabra = repository.get_hsk_by_id(db, hsk_id)
    if not palabra:
        return None
    
    # 1. Crear entrada en diccionario
    entrada_dict = repository.create_diccionario_entry(db, hsk_id)
    
    # 2. Definir las 6 reglas según tu especificación
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
    
    # 3. Aplicar reglas usando el repositorio
    for m1, m2, aud, req in reglas:
        repository.create_tarjeta(db, {
            "hsk_id": palabra.id,
            "diccionario_id": entrada_dict.id,
            "mostrado1": m1 if m1 else None,
            "mostrado2": m2 if m2 else None,
            "audio": aud,
            "requerido": req
        })
    
    db.commit()  # Guardamos todo el lote de tarjetas
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