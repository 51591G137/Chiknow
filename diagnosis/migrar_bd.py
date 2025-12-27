"""
Script de Migración de Base de Datos

Este script actualiza la base de datos existente para añadir:
1. Nuevas columnas a la tabla HSK (categoría, ejemplo, significado_ejemplo)
2. Nueva tabla Notas
3. Actualiza las columnas notas del Diccionario (deprecada) -> usar tabla Notas

IMPORTANTE: Este script es seguro y no elimina datos existentes.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import SessionLocal, engine
import models

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def verificar_columna_existe(table_name, column_name):
    """Verifica si una columna existe en una tabla"""
    db = SessionLocal()
    try:
        query = text(f"PRAGMA table_info({table_name})")
        result = db.execute(query)
        columnas = [row[1] for row in result]
        return column_name in columnas
    finally:
        db.close()

def agregar_columnas_hsk():
    """Añade las nuevas columnas a la tabla HSK si no existen"""
    print_section("1. ACTUALIZANDO TABLA HSK")
    
    db = SessionLocal()
    
    try:
        columnas_nuevas = {
            'categoria': 'TEXT',
            'ejemplo': 'TEXT',
            'significado_ejemplo': 'TEXT'
        }
        
        for columna, tipo in columnas_nuevas.items():
            if verificar_columna_existe('hsk', columna):
                print(f"   ✅ Columna '{columna}' ya existe")
            else:
                print(f"   ➕ Añadiendo columna '{columna}'...")
                query = text(f"ALTER TABLE hsk ADD COLUMN {columna} {tipo}")
                db.execute(query)
                db.commit()
                print(f"   ✅ Columna '{columna}' añadida")
        
        print("\n✅ Tabla HSK actualizada correctamente")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error al actualizar tabla HSK: {e}")
        raise
    finally:
        db.close()

def crear_tabla_notas():
    """Crea la tabla Notas si no existe"""
    print_section("2. CREANDO TABLA NOTAS")
    
    try:
        # Usar SQLAlchemy para crear la tabla
        models.Base.metadata.create_all(bind=engine, tables=[models.Notas.__table__])
        print("   ✅ Tabla 'notas' creada (o ya existía)")
        
    except Exception as e:
        print(f"   ❌ Error al crear tabla notas: {e}")
        raise

def migrar_notas_diccionario():
    """
    Si la tabla diccionario tiene columna 'notas', migrar a la nueva tabla Notas
    """
    print_section("3. MIGRANDO NOTAS DEL DICCIONARIO")
    
    if not verificar_columna_existe('diccionario', 'notas'):
        print("   ℹ️  La tabla diccionario no tiene columna 'notas', nada que migrar")
        return
    
    db = SessionLocal()
    
    try:
        # Obtener todas las entradas del diccionario con notas
        query = text("SELECT id, hsk_id, notas FROM diccionario WHERE notas IS NOT NULL AND notas != ''")
        result = db.execute(query)
        
        count = 0
        for row in result:
            dict_id, hsk_id, notas = row
            
            # Verificar si ya existe una nota para este hsk_id
            nota_existente = db.query(models.Notas).filter(
                models.Notas.hsk_id == hsk_id
            ).first()
            
            if not nota_existente:
                # Crear nueva nota
                nueva_nota = models.Notas(
                    hsk_id=hsk_id,
                    nota=notas
                )
                db.add(nueva_nota)
                count += 1
        
        db.commit()
        
        if count > 0:
            print(f"   ✅ Migradas {count} notas del diccionario a la tabla Notas")
        else:
            print("   ℹ️  No había notas para migrar")
        
    except Exception as e:
        db.rollback()
        print(f"   ❌ Error al migrar notas: {e}")
        raise
    finally:
        db.close()

def verificar_migracion():
    """Verifica que la migración se haya completado correctamente"""
    print_section("4. VERIFICANDO MIGRACIÓN")
    
    db = SessionLocal()
    
    try:
        # Verificar columnas HSK
        for col in ['categoria', 'ejemplo', 'significado_ejemplo']:
            if verificar_columna_existe('hsk', col):
                print(f"   ✅ HSK.{col}")
            else:
                print(f"   ❌ HSK.{col} - FALTA")
        
        # Verificar tabla Notas
        total_notas = db.query(models.Notas).count()
        print(f"\n   📝 Total notas en nueva tabla: {total_notas}")
        
        print("\n✅ Verificación completada")
        
    except Exception as e:
        print(f"\n❌ Error en verificación: {e}")
    finally:
        db.close()

def main():
    """Función principal"""
    print("\n" + "="*60)
    print("  🔄 MIGRACIÓN DE BASE DE DATOS - CHIKNOW")
    print("="*60)
    
    print("\n⚠️  IMPORTANTE:")
    print("   - Esta migración es segura y no elimina datos")
    print("   - Se recomienda hacer backup de test.db antes de continuar")
    print("   - La migración puede tardar unos segundos")
    
    respuesta = input("\n¿Deseas continuar? (s/n): ")
    
    if respuesta.lower() != 's':
        print("\n❌ Migración cancelada")
        return
    
    try:
        agregar_columnas_hsk()
        crear_tabla_notas()
        migrar_notas_diccionario()
        verificar_migracion()
        
        print("\n" + "="*60)
        print("  ✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        print("\n📋 Próximos pasos:")
        print("   1. Ejecutar: python datos/cargar_hsk.py")
        print("   2. Ejecutar: python diagnosis/diagnostico_consolidado.py")
        print("\n")
        
    except Exception as e:
        print("\n" + "="*60)
        print("  ❌ ERROR EN LA MIGRACIÓN")
        print("="*60)
        print(f"\n{e}")
        print("\n⚠️  Si tienes backup, puedes restaurarlo")

if __name__ == "__main__":
    main()
