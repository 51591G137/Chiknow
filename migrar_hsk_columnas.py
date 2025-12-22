#!/usr/bin/env python3
"""
Script de migración para añadir columnas alternativas a la tabla HSK
Uso: python3 migrar_hsk_columnas.py
"""

import sqlite3
from database import SessionLocal
import models

def migrar_base_datos():
    """Añade columnas hanzi_alt, pinyin_alt, espanol_alt a la tabla HSK"""
    
    print("="*60)
    print("MIGRACIÓN: Añadir columnas alternativas a HSK")
    print("="*60)
    
    # Conectar directamente con SQLite
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    try:
        # Verificar si las columnas ya existen
        cursor.execute("PRAGMA table_info(hsk)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        print(f"\nColumnas actuales en tabla HSK:")
        for col in columnas:
            print(f"  - {col}")
        
        columnas_a_añadir = []
        
        if 'hanzi_alt' not in columnas:
            columnas_a_añadir.append(('hanzi_alt', 'TEXT'))
        
        if 'pinyin_alt' not in columnas:
            columnas_a_añadir.append(('pinyin_alt', 'TEXT'))
        
        if 'espanol_alt' not in columnas:
            columnas_a_añadir.append(('espanol_alt', 'TEXT'))
        
        if not columnas_a_añadir:
            print("\n✅ Las columnas ya existen, no es necesario migrar")
            return
        
        print(f"\n🔄 Añadiendo {len(columnas_a_añadir)} columnas nuevas...")
        
        for columna, tipo in columnas_a_añadir:
            print(f"  Añadiendo columna: {columna} ({tipo})")
            cursor.execute(f"ALTER TABLE hsk ADD COLUMN {columna} {tipo}")
        
        conn.commit()
        
        print("\n✅ Migración completada exitosamente")
        
        # Verificar que se añadieron
        cursor.execute("PRAGMA table_info(hsk)")
        columnas_nuevas = [col[1] for col in cursor.fetchall()]
        
        print(f"\nColumnas actualizadas en tabla HSK:")
        for col in columnas_nuevas:
            print(f"  - {col}")
        
        print("\n💡 Las nuevas columnas están vacías (NULL)")
        print("   Puedes actualizarlas posteriormente si necesitas")
        
    except Exception as e:
        print(f"\n❌ ERROR durante la migración: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

def actualizar_modelo():
    """Muestra el código actualizado para models.py"""
    print("\n" + "="*60)
    print("ACTUALIZACIÓN DE models.py")
    print("="*60)
    print("\nAñade estas líneas a la clase HSK en models.py:")
    print("""
class HSK(Base):
    __tablename__ = "hsk"
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer)
    nivel = Column(Integer)
    hanzi = Column(String)
    pinyin = Column(String)
    espanol = Column(String)
    # NUEVAS COLUMNAS (añadidas en migración)
    hanzi_alt = Column(String, nullable=True)
    pinyin_alt = Column(String, nullable=True)
    espanol_alt = Column(String, nullable=True)
""")

if __name__ == "__main__":
    migrar_base_datos()
    actualizar_modelo()