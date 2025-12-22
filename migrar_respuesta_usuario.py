#!/usr/bin/env python3
"""
Migración: Añadir campo respuesta_usuario a SM2Review
y modificar repository.py para orden aleatorio
"""

import sqlite3

def migrar_sm2_review():
    """Añade columna respuesta_usuario a SM2Review"""
    
    print("="*60)
    print("MIGRACIÓN: Añadir respuesta_usuario a SM2Review")
    print("="*60)
    
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(sm2_reviews)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        print(f"\nColumnas actuales en sm2_reviews:")
        for col in columnas:
            print(f"  - {col}")
        
        if 'respuesta_usuario' in columnas:
            print("\n✅ La columna 'respuesta_usuario' ya existe")
            return
        
        print("\n🔄 Añadiendo columna respuesta_usuario...")
        cursor.execute("ALTER TABLE sm2_reviews ADD COLUMN respuesta_usuario TEXT")
        
        conn.commit()
        print("✅ Columna añadida exitosamente")
        
        # Verificar
        cursor.execute("PRAGMA table_info(sm2_reviews)")
        columnas_nuevas = [col[1] for col in cursor.fetchall()]
        
        print(f"\nColumnas actualizadas:")
        for col in columnas_nuevas:
            print(f"  - {col}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

def mostrar_cambios_codigo():
    """Muestra los cambios necesarios en el código"""
    
    print("\n" + "="*60)
    print("CAMBIOS NECESARIOS EN EL CÓDIGO")
    print("="*60)
    
    print("\n1. MODELS.PY - Añadir campo a SM2Review:")
    print("""
class SM2Review(Base):
    __tablename__ = "sm2_reviews"
    id = Column(Integer, primary_key=True, index=True)
    tarjeta_id = Column(Integer, ForeignKey("tarjetas.id"))
    session_id = Column(Integer, ForeignKey("sm2_sessions.id"))
    
    # Datos de la revisión
    quality = Column(Integer)  # 0-2: 0=Again, 1=Hard, 2=Easy
    
    # NUEVO: Lo que el usuario escribió/pensó
    respuesta_usuario = Column(Text, nullable=True)
    
    previous_easiness = Column(Float)
    new_easiness = Column(Float)
    previous_interval = Column(Integer)
    new_interval = Column(Integer)
    previous_estado = Column(String)
    new_estado = Column(String)
    
    # Para tarjetas de ejemplo: hanzi que fallaron
    hanzi_fallados = Column(Text, nullable=True)
    frase_fallada = Column(Boolean, default=False)
    
    fecha = Column(DateTime, default=datetime.utcnow)
""")
    
    print("\n2. REPOSITORY.PY - Añadir parámetro a create_review:")
    print("""
def create_review(db: Session, tarjeta_id: int, session_id: int, quality: int, 
                  prev_easiness: float, new_easiness: float, 
                  prev_interval: int, new_interval: int,
                  prev_estado: str, new_estado: str,
                  hanzi_fallados: list = None, frase_fallada: bool = False,
                  respuesta_usuario: str = None):  # NUEVO PARÁMETRO
    review = models.SM2Review(
        tarjeta_id=tarjeta_id,
        session_id=session_id,
        quality=quality,
        respuesta_usuario=respuesta_usuario,  # NUEVO
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
""")
    
    print("\n3. REPOSITORY.PY - Modificar get_cards_due_for_review para orden ALEATORIO:")
    print("""
import random  # Añadir al inicio del archivo

def get_cards_due_for_review(db: Session, limite: int = None):
    \"\"\"Obtiene tarjetas ACTIVAS que necesitan revisión (ORDEN ALEATORIO)\"\"\"
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
            models.SM2Progress.next_review <= datetime.utcnow(),
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
""")
    
    print("\n4. SERVICE.PY - Añadir parámetro respuesta_usuario:")
    print("""
def procesar_respuesta(db: Session, tarjeta_id: int, session_id: int, quality: int,
                      hanzi_fallados: list = None, frase_fallada: bool = False,
                      respuesta_usuario: str = None):  # NUEVO PARÁMETRO
    # ... código existente ...
    
    # Registrar revisión
    repository.create_review(
        db, tarjeta_id, session_id, quality,
        prev_easiness, new_easiness,
        prev_interval, new_interval,
        prev_estado, new_estado,
        hanzi_fallados, frase_fallada,
        respuesta_usuario  # NUEVO
    )
    
    # ... resto del código ...
""")
    
    print("\n5. MAIN.PY - Actualizar ReviewRequest:")
    print("""
class ReviewRequest(BaseModel):
    tarjeta_id: int
    session_id: int
    quality: int
    hanzi_fallados: Optional[List[str]] = None
    frase_fallada: bool = False
    respuesta_usuario: Optional[str] = None  # NUEVO
    
@app.post("/api/sm2/review")
def api_procesar_respuesta(
    review: ReviewRequest,
    db: Session = Depends(database.get_db)
):
    return service.procesar_respuesta(
        db, 
        review.tarjeta_id, 
        review.session_id, 
        review.quality, 
        review.hanzi_fallados, 
        review.frase_fallada,
        review.respuesta_usuario  # NUEVO
    )
""")
    
    print("\n6. SM2.HTML - Añadir input para respuesta del usuario:")
    print("""
<!-- En la parte de flashcard-back, antes de los botones SM2 -->
<div class="flashcard-back" id="card-back" style="display: none;">
    <div class="card-content" id="card-requerido"></div>
    
    <!-- NUEVO: Input para respuesta del usuario -->
    <div style="margin: 1rem 0;">
        <label for="respuesta-usuario" style="display: block; margin-bottom: 0.5rem;">
            ¿Qué respondiste? (opcional)
        </label>
        <input 
            type="text" 
            id="respuesta-usuario" 
            placeholder="Tu respuesta..."
            style="width: 100%; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px;"
        />
    </div>
    
    <!-- Botones SM2 -->
    <div class="sm2-buttons">
        ...
    </div>
</div>

<!-- En la función responder() -->
async function responder(calidad) {
    const respuestaUsuario = document.getElementById('respuesta-usuario').value.trim();
    
    const response = await fetch('/api/sm2/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            tarjeta_id: tarjetaActual.tarjeta_id,
            session_id: sessionId,
            quality: calidad,
            respuesta_usuario: respuestaUsuario || null  // NUEVO
        })
    });
    
    // Limpiar input para siguiente tarjeta
    document.getElementById('respuesta-usuario').value = '';
    
    // ... resto del código ...
}
""")

if __name__ == "__main__":
    migrar_sm2_review()
    mostrar_cambios_codigo()