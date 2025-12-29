#!/usr/bin/env python3
"""
Script de Actualización de Tabla HSK
=====================================
MANTIENE IDs de las primeras 500 filas para conservar progreso del usuario.
Añade nuevas columnas y nuevos registros automáticamente.

Uso:
    python actualizar_hsk_conservando_ids.py

IMPORTANTE: Ejecutar desde el directorio raíz del proyecto (Chiknow-main/)
"""

import sys
import os
import pandas as pd
from datetime import datetime
import shutil
import unicodedata
import re

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app import models
from sqlalchemy import text, inspect

def print_section(title, char="="):
    """Imprime un título de sección"""
    print(f"\n{char*70}")
    print(f"  {title}")
    print(f"{char*70}\n")

def normalizar_columnas_csv(df):
    """Normaliza nombres de columnas del CSV para que coincidan con el modelo"""
    # Primero, eliminar columnas unnamed (vacías del CSV)
    columnas_validas = [col for col in df.columns if not str(col).lower().startswith('unnamed')]
    df = df[columnas_validas]
    
    # Mapeo de nombres del CSV a nombres del modelo
    mapeo_columnas = {
        'nivel': 'nivel',
        'hànzì': 'hanzi',
        'hanzi': 'hanzi',
        'pīnyīn': 'pinyin',
        'pinyin': 'pinyin',
        'español': 'espanol',
        'espanol': 'espanol',
        'hànzì_alt': 'hanzi_alt',
        'hanzi_alt': 'hanzi_alt',
        'pīnyīn_alt': 'pinyin_alt',
        'pinyin_alt': 'pinyin_alt',
        'categoría': 'categoria',
        'categoria': 'categoria',
        'ejemplo': 'ejemplo',
        'significado ejemplo': 'significado_ejemplo',
        'significado_ejemplo': 'significado_ejemplo',
    }
    
    # Función para normalizar un nombre de columna
    def normalizar_nombre(nombre):
        # Eliminar acentos
        nombre_nfd = unicodedata.normalize('NFD', str(nombre))
        nombre_sin_acentos = ''.join(c for c in nombre_nfd if unicodedata.category(c) != 'Mn')
        # Convertir a minúsculas y reemplazar espacios por _
        nombre_limpio = nombre_sin_acentos.lower().strip().replace(' ', '_')
        return nombre_limpio
    
    # Crear diccionario de renombrado
    renombrar = {}
    for col in df.columns:
        col_normalizada = normalizar_nombre(col)
        if col_normalizada in mapeo_columnas:
            renombrar[col] = mapeo_columnas[col_normalizada]
        else:
            # Mantener el nombre normalizado
            renombrar[col] = col_normalizada
    
    # Renombrar columnas
    df = df.rename(columns=renombrar)
    
    return df

def verificar_prerequisitos():
    """Verifica que todo esté listo"""
    print_section("1. VERIFICACIÓN DE PREREQUISITOS")
    
    # Verificar que existe hsk.csv
    csv_path = "data/hsk.csv"
    if not os.path.exists(csv_path):
        print(f"❌ No se encontró {csv_path}")
        print("\n💡 Asegúrate de que:")
        print("   1. El archivo hsk.csv esté en la carpeta data/")
        print("   2. Estás ejecutando el script desde el directorio raíz (Chiknow-main/)")
        return False, None
    
    # Leer CSV
    print(f"📖 Leyendo {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ CSV leído correctamente: {len(df)} filas")
        print(f"   Columnas originales: {', '.join(df.columns.tolist())}")
        
        # Normalizar nombres de columnas (eliminar acentos, espacios, etc.)
        df = normalizar_columnas_csv(df)
        print(f"   Columnas normalizadas: {', '.join(df.columns.tolist())}")
        
        return True, df
    except Exception as e:
        print(f"❌ Error al leer CSV: {e}")
        return False, None

def hacer_backup():
    """Crea backup de la base de datos"""
    print_section("2. CREANDO BACKUP DE SEGURIDAD")
    
    db_path = "data/test.db"
    
    if not os.path.exists(db_path):
        print("ℹ️  No existe base de datos local (se creará una nueva)")
        return True, None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backups/hsk_update_backup_{timestamp}.db"
    
    try:
        os.makedirs("backups", exist_ok=True)
        shutil.copy2(db_path, backup_path)
        size_mb = os.path.getsize(backup_path) / 1024 / 1024
        print(f"✅ Backup creado: {backup_path}")
        print(f"   Tamaño: {size_mb:.2f} MB")
        return True, backup_path
    except Exception as e:
        print(f"❌ Error al crear backup: {e}")
        return False, None

def verificar_columnas_nuevas(df):
    """Identifica columnas nuevas que necesitan añadirse"""
    print_section("3. VERIFICANDO ESTRUCTURA DE TABLA")
    
    inspector = inspect(engine)
    
    # Verificar si la tabla existe
    if not inspector.has_table('hsk'):
        print("⚠️  La tabla 'hsk' no existe")
        print("✨ Creando tabla 'hsk' con estructura completa...")
        
        # Crear todas las tablas (esto creará hsk y las demás)
        models.Base.metadata.create_all(bind=engine)
        
        print("✅ Tabla 'hsk' creada exitosamente")
        
        # Ahora todas las columnas del CSV son "nuevas" (la tabla está vacía)
        # Pero como acabamos de crear la tabla con el modelo, ya tiene la estructura base
        # Solo necesitamos identificar columnas del CSV que NO estén en el modelo
        inspector = inspect(engine)
        columnas_actuales = {col['name'] for col in inspector.get_columns('hsk')}
    else:
        columnas_actuales = {col['name'] for col in inspector.get_columns('hsk')}
    
    columnas_csv = set(df.columns)
    
    # Columnas nuevas (excluyendo 'id' y 'numero' que son especiales)
    columnas_nuevas = columnas_csv - columnas_actuales - {'id', 'numero'}
    
    print(f"📊 Columnas actuales en BD: {len(columnas_actuales)}")
    print(f"📊 Columnas en CSV: {len(columnas_csv)}")
    
    if columnas_nuevas:
        print(f"\n🆕 Columnas nuevas a añadir:")
        for col in columnas_nuevas:
            print(f"   - {col}")
    else:
        print("\n✅ No hay columnas nuevas")
    
    return columnas_nuevas

def añadir_columnas_nuevas(columnas_nuevas):
    """Añade columnas nuevas a la tabla HSK"""
    if not columnas_nuevas:
        return True
    
    print_section("4. AÑADIENDO NUEVAS COLUMNAS")
    
    db = SessionLocal()
    
    try:
        for columna in columnas_nuevas:
            print(f"➕ Añadiendo columna '{columna}'...")
            query = text(f"ALTER TABLE hsk ADD COLUMN {columna} TEXT")
            db.execute(query)
            db.commit()
            print(f"✅ Columna '{columna}' añadida")
        
        print("\n✅ Todas las columnas nuevas añadidas correctamente")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error al añadir columnas: {e}")
        return False
    finally:
        db.close()

def actualizar_datos_hsk(df):
    """
    Actualiza la tabla HSK:
    - Primeras 500 filas: ACTUALIZA sin cambiar ID
    - Filas 501+: INSERTA como nuevos registros
    """
    print_section("5. ACTUALIZANDO DATOS HSK")
    
    db = SessionLocal()
    
    try:
        registros_actualizados = 0
        registros_nuevos = 0
        
        # Obtener el máximo ID actual
        max_id_actual = db.query(models.HSK).count()
        print(f"📊 Registros actuales en BD: {max_id_actual}")
        print(f"📊 Filas en CSV: {len(df)}")
        
        # PARTE 1: Actualizar primeras 500 filas (o las que haya)
        print("\n🔄 Fase 1: Actualizando registros existentes...")
        limite_actualizacion = min(500, max_id_actual)
        
        for idx in range(limite_actualizacion):
            hsk_id = idx + 1
            row = df.iloc[idx]
            
            # Buscar registro existente
            registro = db.query(models.HSK).filter(models.HSK.id == hsk_id).first()
            
            if registro:
                # Actualizar todos los campos (excepto id y numero que se mantienen)
                for col in df.columns:
                    if col not in ['id', 'numero'] and hasattr(registro, col):
                        valor = row[col]
                        if pd.notna(valor):
                            setattr(registro, col, str(valor).strip() if isinstance(valor, str) else valor)
                        else:
                            setattr(registro, col, None)
                
                registros_actualizados += 1
                
                if (registros_actualizados % 50 == 0):
                    db.commit()
                    print(f"   Actualizados: {registros_actualizados}/{limite_actualizacion}")
        
        db.commit()
        print(f"\n✅ Actualizados {registros_actualizados} registros existentes")
        
        # PARTE 2: Añadir nuevos registros (desde fila 501 o donde corresponda)
        if len(df) > limite_actualizacion:
            print(f"\n➕ Fase 2: Añadiendo nuevos registros...")
            
            # Obtener el próximo ID disponible
            proximo_id = max_id_actual + 1
            
            for idx in range(limite_actualizacion, len(df)):
                row = df.iloc[idx]
                
                # Crear nuevo registro
                datos = {
                    'id': proximo_id,
                    'numero': proximo_id
                }
                
                # Añadir todos los campos del CSV
                for col in df.columns:
                    if col not in ['id', 'numero'] and hasattr(models.HSK, col):
                        valor = row[col]
                        if pd.notna(valor):
                            datos[col] = str(valor).strip() if isinstance(valor, str) else valor
                        else:
                            datos[col] = None
                
                nuevo_registro = models.HSK(**datos)
                db.add(nuevo_registro)
                
                registros_nuevos += 1
                proximo_id += 1
                
                if (registros_nuevos % 50 == 0):
                    db.commit()
                    print(f"   Nuevos: {registros_nuevos}/{len(df) - limite_actualizacion}")
            
            db.commit()
            print(f"\n✅ Añadidos {registros_nuevos} registros nuevos")
        
        # Resumen final
        print("\n" + "="*70)
        print("📊 RESUMEN DE ACTUALIZACIÓN:")
        print("="*70)
        print(f"  ✅ Registros actualizados: {registros_actualizados}")
        print(f"  ➕ Registros nuevos: {registros_nuevos}")
        print(f"  📈 Total en BD: {db.query(models.HSK).count()}")
        print("="*70)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error durante la actualización: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def verificar_integridad():
    """Verifica que los datos se hayan actualizado correctamente"""
    print_section("6. VERIFICANDO INTEGRIDAD")
    
    db = SessionLocal()
    
    try:
        # Contar registros
        total = db.query(models.HSK).count()
        print(f"✅ Total registros en BD: {total}")
        
        # Verificar que no hay IDs duplicados
        ids = [r.id for r in db.query(models.HSK.id).all()]
        duplicados = len(ids) - len(set(ids))
        
        if duplicados > 0:
            print(f"⚠️  ADVERTENCIA: {duplicados} IDs duplicados encontrados")
            return False
        else:
            print("✅ No hay IDs duplicados")
        
        # Verificar primeros y últimos registros
        print("\n📝 Primeros 3 registros:")
        for r in db.query(models.HSK).limit(3).all():
            print(f"   ID {r.id}: {r.hanzi} ({r.pinyin}) - {r.espanol}")
        
        print("\n📝 Últimos 3 registros:")
        for r in db.query(models.HSK).order_by(models.HSK.id.desc()).limit(3).all():
            print(f"   ID {r.id}: {r.hanzi} ({r.pinyin}) - {r.espanol}")
        
        # Verificar relaciones importantes (tarjetas, diccionario)
        print("\n🔗 Verificando relaciones:")
        tarjetas = db.query(models.Tarjeta).count()
        diccionario = db.query(models.Diccionario).count()
        progreso = db.query(models.SM2Progress).count()
        
        print(f"   Tarjetas: {tarjetas}")
        print(f"   Diccionario: {diccionario}")
        print(f"   Progreso SM2: {progreso}")
        
        print("\n✅ Verificación completada")
        return True
        
    except Exception as e:
        print(f"\n❌ Error en verificación: {e}")
        return False
    finally:
        db.close()

def main():
    """Función principal"""
    print("\n" + "="*70)
    print("  🚀 ACTUALIZACIÓN DE TABLA HSK - CONSERVANDO PROGRESO")
    print("="*70)
    
    print("\n⚠️  IMPORTANTE:")
    print("   - Se conservarán los IDs de las primeras 500 filas")
    print("   - El progreso del usuario NO se perderá")
    print("   - Se creará un backup automático")
    print("   - Nuevos registros se añadirán después de los existentes")
    
    respuesta = input("\n¿Deseas continuar? (s/n): ")
    if respuesta.lower() != 's':
        print("\n❌ Operación cancelada")
        return
    
    # Paso 1: Verificar prerequisitos
    ok, df = verificar_prerequisitos()
    if not ok:
        return
    
    # Paso 2: Crear backup
    ok, backup_path = hacer_backup()
    if not ok:
        return
    
    # Paso 3: Verificar columnas nuevas
    columnas_nuevas = verificar_columnas_nuevas(df)
    
    # Paso 4: Añadir columnas nuevas
    if columnas_nuevas:
        ok = añadir_columnas_nuevas(columnas_nuevas)
        if not ok:
            print(f"\n⚠️  Error al añadir columnas. Backup disponible en: {backup_path}")
            return
    
    # Paso 5: Actualizar datos
    ok = actualizar_datos_hsk(df)
    if not ok:
        print(f"\n⚠️  Error al actualizar datos. Backup disponible en: {backup_path}")
        return
    
    # Paso 6: Verificar integridad
    ok = verificar_integridad()
    
    # Resumen final
    print_section("✅ ACTUALIZACIÓN COMPLETADA EXITOSAMENTE", "=")
    
    if backup_path:
        print(f"💾 Backup guardado en: {backup_path}")
    
    print("\n🎯 Próximos pasos:")
    print("   1. Revisar los datos en la aplicación")
    print("   2. Verificar que el progreso del usuario se mantiene")
    print("   3. Si todo está bien, ejecutar el servidor:")
    print("      python run.py")
    print()

if __name__ == "__main__":
    main()