#!/usr/bin/env python3
"""
Script de Reemplazo Completo de Datos HSK
==========================================
CONSERVA solo los IDs de las primeras 500 filas.
REEMPLAZA COMPLETAMENTE todos los datos con el nuevo CSV.

Uso:
    python reemplazar_datos_hsk_completo.py

IMPORTANTE: 
- Ejecutar desde el directorio raíz del proyecto (Chiknow-main/)
- El nuevo CSV debe estar en data/hsk.csv
"""

import sys
import os
import pandas as pd
from datetime import datetime
import shutil
import unicodedata
import re
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app import models
from sqlalchemy import text

def print_section(title, char="="):
    """Imprime un título de sección"""
    print(f"\n{char*70}")
    print(f"  {title}")
    print(f"{char*70}\n")

def normalizar_columnas_csv(df):
    """Normaliza nombres de columnas del CSV"""
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
        nombre_nfd = unicodedata.normalize('NFD', str(nombre))
        nombre_sin_acentos = ''.join(c for c in nombre_nfd if unicodedata.category(c) != 'Mn')
        nombre_limpio = nombre_sin_acentos.lower().strip().replace(' ', '_')
        return nombre_limpio
    
    # Crear diccionario de renombrado
    renombrar = {}
    for col in df.columns:
        col_normalizada = normalizar_nombre(col)
        if col_normalizada in mapeo_columnas:
            renombrar[col] = mapeo_columnas[col_normalizada]
        else:
            renombrar[col] = col_normalizada
    
    # Renombrar columnas
    df = df.rename(columns=renombrar)
    
    return df

def hacer_backup():
    """Crea backup de la base de datos"""
    print_section("1. CREANDO BACKUP DE SEGURIDAD")
    
    db_path = "data/test.db"
    
    if not os.path.exists(db_path):
        print("ℹ️  No existe base de datos local")
        return True, None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backups/reemplazo_completo_backup_{timestamp}.db"
    
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

def cargar_csv():
    """Carga y normaliza el CSV"""
    print_section("2. CARGANDO NUEVO CSV")
    
    csv_path = "data/hsk.csv"
    if not os.path.exists(csv_path):
        print(f"❌ No se encontró {csv_path}")
        return None
    
    print(f"📖 Leyendo {csv_path}...")
    try:
        # Intentar múltiples codificaciones
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(csv_path, encoding=encoding)
                print(f"✅ CSV leído con codificación: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            print("❌ No se pudo leer el CSV con ninguna codificación conocida")
            return None
        
        print(f"   {len(df)} filas")
        print(f"   Columnas originales: {', '.join(df.columns.tolist())}")
        
        # Normalizar columnas
        df = normalizar_columnas_csv(df)
        print(f"   Columnas normalizadas: {', '.join(df.columns.tolist())}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error al leer CSV: {e}")
        import traceback
        traceback.print_exc()
        return None

def limpiar_valor(valor):
    """Limpia un valor para asegurarse de que es del tipo correcto"""
    if pd.isna(valor):
        return None
    
    if isinstance(valor, bytes):
        # Si es bytes, intentar decodificar
        try:
            return valor.decode('utf-8')
        except:
            try:
                return valor.decode('latin-1')
            except:
                return valor.decode('utf-8', errors='ignore')
    
    if isinstance(valor, str):
        return valor.strip()
    
    return valor

def reemplazar_datos_completo(df):
    """
    Reemplaza COMPLETAMENTE todos los datos:
    - Primeras 500 filas: ACTUALIZA conservando ID
    - Filas 501+: ELIMINA y REEMPLAZA con datos del CSV
    """
    print_section("3. REEMPLAZANDO DATOS COMPLETOS")
    
    db = SessionLocal()
    
    try:
        # Estado actual
        total_actual = db.query(models.HSK).count()
        print(f"📊 Registros actuales en BD: {total_actual}")
        print(f"📊 Filas en nuevo CSV: {len(df)}")
        
        # CONFIRMACIÓN
        print("\n" + "⚠️ "*35)
        print("⚠️  ESTA OPERACIÓN VA A:")
        print("   1. ACTUALIZAR completamente las primeras 500 filas (conservando IDs)")
        print(f"   2. ELIMINAR las filas {min(500, total_actual) + 1} a {total_actual}")
        print(f"   3. AÑADIR las filas del CSV desde la 501 hasta la {len(df)}")
        print("⚠️ "*35)
        
        respuesta = input("\n¿Estás SEGURO de continuar? (escribe 'SI' para confirmar): ")
        if respuesta != "SI":
            print("\n❌ Operación cancelada")
            return False
        
        # PASO 1: Actualizar primeras 500 filas
        print("\n🔄 PASO 1: Actualizando primeras 500 filas...")
        
        limite_actualizacion = min(500, len(df))
        actualizados = 0
        
        for idx in range(limite_actualizacion):
            hsk_id = idx + 1
            row = df.iloc[idx]
            
            # Buscar registro
            registro = db.query(models.HSK).filter(models.HSK.id == hsk_id).first()
            
            if registro:
                # ACTUALIZAR TODOS LOS CAMPOS (excepto id)
                registro.numero = hsk_id
                registro.nivel = int(row['nivel']) if pd.notna(row['nivel']) else 1
                registro.hanzi = limpiar_valor(row['hanzi']) if 'hanzi' in row else None
                registro.pinyin = limpiar_valor(row['pinyin']) if 'pinyin' in row else None
                registro.espanol = limpiar_valor(row['espanol']) if 'espanol' in row else None
                
                # Campos opcionales
                if 'hanzi_alt' in row:
                    registro.hanzi_alt = limpiar_valor(row['hanzi_alt'])
                if 'pinyin_alt' in row:
                    registro.pinyin_alt = limpiar_valor(row['pinyin_alt'])
                if 'categoria' in row:
                    registro.categoria = limpiar_valor(row['categoria'])
                if 'ejemplo' in row:
                    registro.ejemplo = limpiar_valor(row['ejemplo'])
                if 'significado_ejemplo' in row:
                    registro.significado_ejemplo = limpiar_valor(row['significado_ejemplo'])
                
                actualizados += 1
                
                if actualizados % 50 == 0:
                    db.commit()
                    print(f"   Actualizados: {actualizados}/{limite_actualizacion}")
        
        db.commit()
        print(f"\n✅ Actualizadas {actualizados} filas (IDs conservados)")
        
        # PASO 2: Eliminar filas 501+
        if total_actual > 500:
            print(f"\n🗑️  PASO 2: Eliminando filas {501} a {total_actual}...")
            
            eliminados = db.query(models.HSK).filter(models.HSK.id > 500).delete()
            db.commit()
            print(f"✅ Eliminadas {eliminados} filas")
        else:
            print(f"\n✅ No hay filas que eliminar (BD tiene {total_actual} registros)")
        
        # PASO 3: Añadir nuevas filas desde CSV (fila 501 en adelante)
        if len(df) > 500:
            print(f"\n➕ PASO 3: Añadiendo filas {501} a {len(df)} desde CSV...")
            
            nuevos = 0
            
            for idx in range(500, len(df)):
                row = df.iloc[idx]
                
                # Crear nuevo registro con ID = número de fila + 1
                nuevo_id = idx + 1
                
                datos = {
                    'id': nuevo_id,
                    'numero': nuevo_id,
                    'nivel': int(row['nivel']) if pd.notna(row['nivel']) else 1,
                    'hanzi': limpiar_valor(row['hanzi']) if 'hanzi' in row else None,
                    'pinyin': limpiar_valor(row['pinyin']) if 'pinyin' in row else None,
                    'espanol': limpiar_valor(row['espanol']) if 'espanol' in row else None,
                }
                
                # Campos opcionales
                if 'hanzi_alt' in row:
                    datos['hanzi_alt'] = limpiar_valor(row['hanzi_alt'])
                if 'pinyin_alt' in row:
                    datos['pinyin_alt'] = limpiar_valor(row['pinyin_alt'])
                if 'categoria' in row:
                    datos['categoria'] = limpiar_valor(row['categoria'])
                if 'ejemplo' in row:
                    datos['ejemplo'] = limpiar_valor(row['ejemplo'])
                if 'significado_ejemplo' in row:
                    datos['significado_ejemplo'] = limpiar_valor(row['significado_ejemplo'])
                
                nuevo_registro = models.HSK(**datos)
                db.add(nuevo_registro)
                
                nuevos += 1
                
                if nuevos % 50 == 0:
                    db.commit()
                    print(f"   Añadidos: {nuevos}/{len(df) - 500}")
            
            db.commit()
            print(f"\n✅ Añadidos {nuevos} registros nuevos")
        else:
            print(f"\n✅ No hay registros nuevos que añadir")
        
        # RESUMEN FINAL
        total_final = db.query(models.HSK).count()
        
        print("\n" + "="*70)
        print("📊 RESUMEN DE CAMBIOS")
        print("="*70)
        print(f"  Registros iniciales: {total_actual}")
        print(f"  Registros actualizados (1-500): {actualizados}")
        print(f"  Registros eliminados (501+): {total_actual - 500 if total_actual > 500 else 0}")
        print(f"  Registros añadidos: {len(df) - 500 if len(df) > 500 else 0}")
        print(f"  ➡️  TOTAL FINAL: {total_final}")
        print("="*70)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error durante el reemplazo: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def verificar_resultado():
    """Verifica que el resultado sea correcto"""
    print_section("4. VERIFICANDO RESULTADO")
    
    db = SessionLocal()
    
    try:
        total = db.query(models.HSK).count()
        print(f"✅ Total registros en BD: {total}")
        
        # Verificar que no hay bytes
        print("\n🔍 Verificando que no hay campos tipo bytes...")
        campos_con_bytes = 0
        
        for registro in db.query(models.HSK).all():
            if isinstance(registro.nivel, bytes):
                campos_con_bytes += 1
        
        if campos_con_bytes > 0:
            print(f"⚠️  {campos_con_bytes} registros aún tienen bytes en 'nivel'")
            print("   Ejecuta: python limpiar_nivel_correcto.py")
        else:
            print("✅ No hay campos con bytes")
        
        # Mostrar primeros y últimos registros
        print("\n📝 Primeros 3 registros:")
        for r in db.query(models.HSK).limit(3).all():
            print(f"   ID {r.id}: {r.hanzi} ({r.pinyin}) - nivel {r.nivel} - {r.espanol}")
        
        print("\n📝 Últimos 3 registros:")
        for r in db.query(models.HSK).order_by(models.HSK.id.desc()).limit(3).all():
            print(f"   ID {r.id}: {r.hanzi} ({r.pinyin}) - nivel {r.nivel} - {r.espanol}")
        
        return True
        
    finally:
        db.close()

def main():
    """Función principal"""
    print("\n" + "="*70)
    print("  🔄 REEMPLAZO COMPLETO DE DATOS HSK")
    print("="*70)
    
    print("\n⚠️  IMPORTANTE:")
    print("   - Se CONSERVARÁN los IDs de las primeras 500 filas")
    print("   - Se REEMPLAZARÁN COMPLETAMENTE todos los datos")
    print("   - Se ELIMINARÁN las filas 501+ incorrectas")
    print("   - Se AÑADIRÁN las filas correctas del CSV")
    print("   - El progreso del usuario en las primeras 500 se mantendrá")
    
    respuesta = input("\n¿Deseas continuar? (s/n): ")
    if respuesta.lower() != 's':
        print("\n❌ Operación cancelada")
        return
    
    # Paso 1: Backup
    ok, backup_path = hacer_backup()
    if not ok:
        print("\n❌ No se pudo crear backup. Operación abortada.")
        return
    
    # Paso 2: Cargar CSV
    df = cargar_csv()
    if df is None:
        print("\n❌ No se pudo cargar el CSV. Operación abortada.")
        return
    
    # Paso 3: Reemplazar datos
    ok = reemplazar_datos_completo(df)
    
    if ok:
        # Paso 4: Verificar
        verificar_resultado()
        
        print("\n" + "="*70)
        print("  ✅ REEMPLAZO COMPLETADO EXITOSAMENTE")
        print("="*70)
        
        if backup_path:
            print(f"\n💾 Backup guardado en: {backup_path}")
        
        print("\n🎯 Próximos pasos:")
        print("   1. Verificar que no hay bytes: python limpiar_nivel_correcto.py")
        print("   2. Iniciar servidor: uvicorn app.main:app --reload")
        print("   3. Probar la aplicación en: http://localhost:8000/")
        print()
    else:
        print("\n❌ El reemplazo falló")
        if backup_path:
            print(f"\n💾 Puedes restaurar el backup desde: {backup_path}")

if __name__ == "__main__":
    main()