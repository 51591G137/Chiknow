from sqlalchemy import text
import sys
sys.path.insert(0, ".")
from app.database import SessionLocal

def migrate():
    db = SessionLocal()
    try:
        # Verificar si la columna ya existe
        result = db.execute(text("""
            SELECT COUNT(*) FROM pragma_table_info('sm2_progress') 
            WHERE name='version'
        """))
        column_exists = result.scalar() > 0
        
        if not column_exists:
            # Agregar columna version a sm2_progress
            db.execute(text("""
                ALTER TABLE sm2_progress 
                ADD COLUMN version INTEGER DEFAULT 1 NOT NULL
            """))
            print("✅ Columna 'version' agregada a sm2_progress")
        else:
            print("✅ La columna 'version' ya existe en sm2_progress")
            
        db.commit()
        print("✅ Migración completada")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()