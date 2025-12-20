from sqlalchemy.orm import Session
import models

def get_hsk_all(db: Session):
    return db.query(models.HSK).all()

def get_hsk_by_id(db: Session, hsk_id: int):
    return db.query(models.HSK).filter(models.HSK.id == hsk_id).first()

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

def create_tarjeta(db: Session, datos_tarjeta: dict):
    nueva_tarjeta = models.Tarjeta(**datos_tarjeta)
    db.add(nueva_tarjeta)
    # No hacemos commit aquí para poder hacer varios seguidos en el servicio

def get_diccionario_entry_by_hsk_id(db: Session, hsk_id: int):
    """Obtiene la entrada del diccionario por hsk_id"""
    return db.query(models.Diccionario).filter(models.Diccionario.hsk_id == hsk_id).first()

def delete_diccionario_entry(db: Session, diccionario_id: int):
    """Elimina una entrada del diccionario"""
    db.query(models.Diccionario).filter(models.Diccionario.id == diccionario_id).delete()

def delete_tarjetas_by_diccionario_id(db: Session, diccionario_id: int):
    """Elimina todas las tarjetas asociadas a una entrada del diccionario"""
    db.query(models.Tarjeta).filter(models.Tarjeta.diccionario_id == diccionario_id).delete()

def get_all_diccionario_with_hsk(db: Session):
    """Obtiene todas las entradas del diccionario con información de HSK"""
    return db.query(models.Diccionario, models.HSK).join(
        models.HSK, models.Diccionario.hsk_id == models.HSK.id
    ).all()

def get_all_tarjetas_with_info(db: Session):
    """Obtiene todas las tarjetas con información completa"""
    return db.query(models.Tarjeta, models.HSK).join(
        models.HSK, models.Tarjeta.hsk_id == models.HSK.id
    ).all()

def get_tarjetas_count(db: Session):
    """Cuenta el total de tarjetas"""
    return db.query(models.Tarjeta).count()