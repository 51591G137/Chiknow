#!/usr/bin/env python3
"""
Diagnóstico Completo de Bytes en HSK
=====================================
Detecta bytes en CUALQUIER campo de la tabla.

Uso:
    python diagnostico_completo_bytes.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app import models
from sqlalchemy import inspect

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def obtener_todos_campos():
    """Obtiene todos los campos de la tabla HSK dinámicamente"""
    inspector = inspect(models.HSK)
    return [col.key for col in inspector.mapper.column_attrs]

def diagnosticar_bytes_completo():
    """Diagnostica bytes en TODOS los campos"""
    print_section("🔍 DIAGNÓSTICO COMPLETO DE BYTES")
    
    db = SessionLocal()
    
    try:
        # Obtener todos los campos
        todos_campos = obtener_todos_campos()
        print(f"📋 Campos a verificar: {', '.join(todos_campos)}")
        
        total_registros = db.query(models.HSK).count()
        print(f"📊 Analizando {total_registros} registros...\n")
        
        # Diccionario para contar problemas por campo
        problemas_por_campo = {campo: [] for campo in todos_campos}
        
        for idx, registro in enumerate(db.query(models.HSK).all()):
            for campo in todos_campos:
                valor = getattr(registro, campo, None)
                
                # Verificar si es bytes
                if isinstance(valor, bytes):
                    problemas_por_campo[campo].append({
                        'id': registro.id,
                        'valor_bytes': valor,
                        'longitud': len(valor)
                    })
            
            if (idx + 1) % 100 == 0:
                print(f"   Procesados: {idx + 1}/{total_registros}")
        
        # REPORTE
        print("\n" + "="*70)
        print("📊 RESULTADOS")
        print("="*70)
        
        campos_con_problemas = {k: v for k, v in problemas_por_campo.items() if v}
        
        if not campos_con_problemas:
            print("\n✅ No se encontraron campos con bytes")
        else:
            print(f"\n⚠️  Encontrados bytes en {len(campos_con_problemas)} campo(s):")
            
            for campo, problemas in campos_con_problemas.items():
                print(f"\n📌 Campo: {campo}")
                print(f"   Registros afectados: {len(problemas)}")
                
                # Mostrar primeros 5 ejemplos
                for i, prob in enumerate(problemas[:5]):
                    print(f"\n   Ejemplo {i+1} - ID {prob['id']}:")
                    print(f"      Longitud: {prob['longitud']} bytes")
                    print(f"      Raw bytes: {prob['valor_bytes'][:50]}")
                    print(f"      Hex: {prob['valor_bytes'][:20].hex()}")
                    
                    # Intentar decodificar
                    print(f"      Intentos de decodificación:")
                    for encoding in ['utf-8', 'latin-1', 'cp1252', 'ascii']:
                        try:
                            decodificado = prob['valor_bytes'].decode(encoding)
                            print(f"         ✅ {encoding}: '{decodificado}'")
                        except Exception as e:
                            print(f"         ❌ {encoding}: {str(e)[:30]}")
                
                if len(problemas) > 5:
                    print(f"\n   ... y {len(problemas) - 5} registros más")
        
        # MOSTRAR REGISTRO COMPLETO PROBLEMÁTICO
        if campos_con_problemas:
            print("\n" + "="*70)
            print("🔬 REGISTRO COMPLETO CON PROBLEMA")
            print("="*70)
            
            # Obtener el primer ID problemático
            primer_campo = list(campos_con_problemas.keys())[0]
            primer_id = campos_con_problemas[primer_campo][0]['id']
            
            registro = db.query(models.HSK).filter(models.HSK.id == primer_id).first()
            
            print(f"\nID: {primer_id}")
            for campo in todos_campos:
                valor = getattr(registro, campo, None)
                tipo = type(valor).__name__
                
                if isinstance(valor, bytes):
                    print(f"   {campo} ({tipo}): ⚠️  {valor[:30]}... (bytes)")
                else:
                    print(f"   {campo} ({tipo}): {valor}")
        
        return campos_con_problemas
        
    finally:
        db.close()

def proponer_solucion(campos_con_problemas):
    """Propone soluciones según los campos afectados"""
    print("\n" + "="*70)
    print("💡 SOLUCIÓN PROPUESTA")
    print("="*70)
    
    if not campos_con_problemas:
        print("\n✅ No hay problemas que resolver")
        return
    
    # Analizar qué tipo de campos tienen problemas
    campos_texto = ['hanzi', 'pinyin', 'espanol', 'hanzi_alt', 'pinyin_alt', 
                    'categoria', 'ejemplo', 'significado_ejemplo']
    campos_numericos = ['id', 'numero', 'nivel']
    
    campos_texto_afectados = [c for c in campos_con_problemas if c in campos_texto]
    campos_numericos_afectados = [c for c in campos_con_problemas if c in campos_numericos]
    campos_otros = [c for c in campos_con_problemas if c not in campos_texto + campos_numericos]
    
    print("\n📋 Análisis:")
    if campos_texto_afectados:
        print(f"   📝 Campos de texto afectados: {', '.join(campos_texto_afectados)}")
        print(f"      → Se pueden decodificar de bytes a string")
    
    if campos_numericos_afectados:
        print(f"   🔢 Campos numéricos afectados: {', '.join(campos_numericos_afectados)}")
        print(f"      → Se pueden convertir de bytes a int")
    
    if campos_otros:
        print(f"   ❓ Otros campos afectados: {', '.join(campos_otros)}")
    
    print("\n🛠️  Script de limpieza automática:")
    print("   Este script puede convertir automáticamente:")
    print("   - Bytes → String (para campos de texto)")
    print("   - Bytes → Integer (para campos numéricos)")

def generar_script_limpieza(campos_con_problemas):
    """Genera un script personalizado de limpieza"""
    print("\n" + "="*70)
    print("🔧 GENERANDO SCRIPT DE LIMPIEZA")
    print("="*70)
    
    script_content = f'''#!/usr/bin/env python3
"""
Script de limpieza generado automáticamente
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app import models

def limpiar_bytes():
    db = SessionLocal()
    
    try:
        total = db.query(models.HSK).count()
        print(f"Limpiando {{total}} registros...")
        
        limpiados = 0
        
        for registro in db.query(models.HSK).all():
'''
    
    for campo in campos_con_problemas:
        # Determinar tipo de conversión
        if campo in ['id', 'numero', 'nivel']:
            script_content += f'''
            # Limpiar campo numérico: {campo}
            if isinstance(registro.{campo}, bytes):
                try:
                    registro.{campo} = int(registro.{campo}.decode('utf-8'))
                except:
                    registro.{campo} = int(registro.{campo}.decode('latin-1'))
'''
        else:
            script_content += f'''
            # Limpiar campo de texto: {campo}
            if isinstance(registro.{campo}, bytes):
                try:
                    registro.{campo} = registro.{campo}.decode('utf-8')
                except:
                    try:
                        registro.{campo} = registro.{campo}.decode('latin-1')
                    except:
                        registro.{campo} = registro.{campo}.decode('utf-8', errors='ignore')
'''
    
    script_content += '''
            limpiados += 1
            
            if limpiados % 50 == 0:
                db.commit()
                print(f"   Limpiados: {limpiados}/{total}")
        
        db.commit()
        print(f"\\n✅ Limpiados {limpiados} registros")
        
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Iniciando limpieza...")
    limpiar_bytes()
    print("✅ Limpieza completada")
'''
    
    # Guardar script
    with open('limpiar_bytes_auto.py', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print("✅ Script generado: limpiar_bytes_auto.py")
    print("\n📝 Para ejecutar:")
    print("   python limpiar_bytes_auto.py")

def main():
    """Función principal"""
    print("\n" + "="*70)
    print("  🔬 DIAGNÓSTICO COMPLETO DE BYTES EN HSK")
    print("="*70)
    
    campos_con_problemas = diagnosticar_bytes_completo()
    
    if campos_con_problemas:
        proponer_solucion(campos_con_problemas)
        
        print("\n" + "="*70)
        respuesta = input("¿Generar script de limpieza automática? (s/n): ")
        
        if respuesta.lower() == 's':
            generar_script_limpieza(campos_con_problemas)
    
    print("\n" + "="*70)
    print("  ✅ DIAGNÓSTICO COMPLETADO")
    print("="*70)
    print()

if __name__ == "__main__":
    main()