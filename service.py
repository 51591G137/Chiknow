from sqlalchemy.orm import Session
import repository

def agregar_palabra_y_generar_tarjetas(db: Session, hsk_id: int):
    palabra = repository.get_hsk_by_id(db, hsk_id)
    if not palabra:
        return None
    
    # 1. Crear entrada en diccionario
    entrada_dict = repository.create_diccionario_entry(db, hsk_id)
    
    # 2. Definir las 8 reglas
    reglas = [
        (palabra.hanzi, palabra.pinyin, True, "Español"),
        (palabra.hanzi, palabra.pinyin, False, "Español"),
        (palabra.hanzi, "", False, "Español"),
        ("", "", True, "Español"),
        (palabra.espanol, palabra.pinyin, True, "Hanzi"),
        (palabra.espanol, palabra.pinyin, False, "Hanzi"),
        (palabra.espanol, "", False, "Hanzi"),
        ("", palabra.pinyin, True, "Hanzi"),
    ]
    
    # 3. Aplicar reglas usando el repositorio
    for m1, m2, aud, req in reglas:
        repository.create_tarjeta(db, {
            "hsk_id": palabra.id,
            "diccionario_id": entrada_dict.id,
            "mostrado1": m1,
            "mostrado2": m2,
            "audio": aud,
            "requerido": req
        })
    
    db.commit() # Guardamos todo el lote de tarjetas
    return True