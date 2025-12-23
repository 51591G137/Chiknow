#!/usr/bin/env python3
"""
Script de migración para añadir campo 'notas' a la tabla diccionario
Uso: python3 migrar_notas_diccionario.py
"""

import sqlite3

def migrar_notas_diccionario():
    """Añade columna notas a la tabla diccionario"""
    
    print("="*60)
    print("MIGRACIÓN: Añadir campo notas a diccionario")
    print("="*60)
    
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(diccionario)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        print(f"\nColumnas actuales en tabla diccionario:")
        for col in columnas:
            print(f"  - {col}")
        
        if 'notas' in columnas:
            print("\n✅ La columna 'notas' ya existe")
            return
        
        print("\n🔄 Añadiendo columna 'notas'...")
        cursor.execute("ALTER TABLE diccionario ADD COLUMN notas TEXT")
        
        conn.commit()
        print("✅ Columna añadida exitosamente")
        
        # Verificar
        cursor.execute("PRAGMA table_info(diccionario)")
        columnas_nuevas = [col[1] for col in cursor.fetchall()]
        
        print(f"\nColumnas actualizadas:")
        for col in columnas_nuevas:
            print(f"  - {col}")
        
        print("\n💡 Ahora los usuarios pueden añadir notas personales a cada palabra")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()


def mostrar_cambios_models():
    """Muestra el código actualizado para models.py"""
    print("\n" + "="*60)
    print("ACTUALIZACIÓN DE models.py")
    print("="*60)
    print("\nAñade esta línea a la clase Diccionario en models.py:")
    print("""
class Diccionario(Base):
    __tablename__ = "diccionario"
    id = Column(Integer, primary_key=True, index=True)
    hsk_id = Column(Integer, ForeignKey("hsk.id"))
    activo = Column(Boolean, default=True)
    notas = Column(Text, nullable=True)  # NUEVA COLUMNA
""")


if __name__ == "__main__":
    migrar_notas_diccionario()
    mostrar_cambios_models()