from sqlalchemy.orm import Session
import models

def get_hsk_all(db: Session):
    return db.query(models.HSK).all()

def get_hsk_by_id(db: Session, hsk_id: int):
    return db.query(models.HSK).filter(models.HSK.id == hsk_id).first()

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