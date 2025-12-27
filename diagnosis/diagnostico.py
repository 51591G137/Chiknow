#!/usr/bin/env python3
"""
Script de diagnóstico para Chiknow
Ejecuta esto desde tu directorio de proyecto: python3 diagnostico.py
"""

import sys
import os

print("="*60)
print("DIAGNÓSTICO CHIKNOW")
print("="*60)

try:
    from database import SessionLocal
    import repository
    import service
    import models
    
    db = SessionLocal()
    
    # Test 1: HSK
    print("\n1. TEST HSK")
    print("-"*40)
    hsk_count = db.query(models.HSK).count()
    print(f"✅ Palabras HSK en BD: {hsk_count}")
    
    # Test 2: Diccionario
    print("\n2. TEST DICCIONARIO")
    print("-"*40)
    try:
        entradas = repository.get_all_diccionario_with_hsk(db)
        print(f"✅ Entradas en diccionario: {len(entradas)}")
        if len(entradas) > 0:
            for i, (dic, hsk) in enumerate(entradas[:5]):
                print(f"  {i+1}. {hsk.hanzi} ({hsk.pinyin}) - Activo: {dic.activo}")
        else:
            print("  ⚠️  Diccionario vacío - añade palabras desde la página HSK")
    except Exception as e:
        print(f"❌ ERROR en diccionario: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Tarjetas (Repository)
    print("\n3. TEST TARJETAS (Repository)")
    print("-"*40)
    try:
        tarjetas = repository.get_all_tarjetas_with_info(db)
        print(f"✅ Tarjetas en BD: {len(tarjetas)}")
        
        # Contar por tipo
        con_hsk = sum(1 for t, h in tarjetas if h is not None)
        sin_hsk = sum(1 for t, h in tarjetas if h is None)
        print(f"  - Con HSK: {con_hsk}")
        print(f"  - Sin HSK (ejemplos): {sin_hsk}")
        
        if len(tarjetas) > 0:
            print("\n  Primeras 5 tarjetas:")
            for i, (tarjeta, hsk) in enumerate(tarjetas[:5]):
                if hsk:
                    m1 = tarjeta.mostrado1 or '(nada)'
                    m2 = tarjeta.mostrado2 or ''
                    audio_icon = '🔊' if tarjeta.audio else ''
                    print(f"  {i+1}. ID:{tarjeta.id} | {hsk.hanzi} | {m1} {m2} {audio_icon} → {tarjeta.requerido}")
                else:
                    print(f"  {i+1}. ID:{tarjeta.id} | (ejemplo sin HSK)")
        else:
            print("  ⚠️  No hay tarjetas - añade palabras al diccionario")
    except Exception as e:
        print(f"❌ ERROR en tarjetas: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Service - obtener_tarjetas_completas
    print("\n4. TEST SERVICE.OBTENER_TARJETAS_COMPLETAS")
    print("-"*40)
    try:
        resultado = service.obtener_tarjetas_completas(db)
        print(f"✅ Tarjetas procesadas por service: {len(resultado)}")
        if len(resultado) > 0:
            print("\n  Primeras 5 tarjetas procesadas:")
            for i, t in enumerate(resultado[:5]):
                m1 = t.get('mostrado1') or '(nada)'
                m2 = t.get('mostrado2') or ''
                audio_icon = '🔊' if t.get('audio') else ''
                print(f"  {i+1}. {t['hanzi']} | {m1} {m2} {audio_icon} → {t['requerido']}")
        else:
            print("  ⚠️  Service devuelve 0 tarjetas")
    except Exception as e:
        print(f"❌ ERROR en service: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: SM2 Statistics
    print("\n5. TEST SM2 STATISTICS")
    print("-"*40)
    try:
        stats = service.obtener_estadisticas_sm2(db)
        print(f"✅ Estadísticas SM2:")
        for key, value in stats.items():
            print(f"  - {key}: {value}")
    except Exception as e:
        print(f"❌ ERROR en stats: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 6: Añadir palabra de prueba
    print("\n6. TEST AÑADIR PALABRA")
    print("-"*40)
    try:
        # Verificar si ya existe la palabra 1 en diccionario
        if not repository.existe_en_diccionario(db, 1):
            print("  Añadiendo palabra ID=1 (爱) al diccionario...")
            resultado = service.agregar_palabra_y_generar_tarjetas(db, 1)
            if resultado:
                print(f"  ✅ Palabra añadida correctamente")
                
                # Verificar que se crearon las tarjetas
                tarjetas_nuevas = repository.get_all_tarjetas_with_info(db)
                print(f"  ✅ Total de tarjetas ahora: {len(tarjetas_nuevas)}")
            else:
                print(f"  ❌ Error al añadir palabra")
        else:
            print(f"  ⚠️  La palabra ID=1 ya está en el diccionario")
    except Exception as e:
        print(f"❌ ERROR al añadir palabra: {e}")
        import traceback
        traceback.print_exc()
    
    db.close()
    
    print("\n" + "="*60)
    print("DIAGNÓSTICO COMPLETADO")
    print("="*60)
    print("\n📋 RESUMEN:")
    print("- Si ves '✅' en todos los tests, la app funciona correctamente")
    print("- Si ves '❌', hay un error que necesita corrección")
    print("- Si ves '⚠️', necesitas añadir datos (palabras al diccionario)")
    
except ImportError as e:
    print(f"\n❌ ERROR DE IMPORTACIÓN: {e}")
    print("\n¿Estás ejecutando desde el directorio correcto?")
    print("Debes ejecutar: python3 diagnostico.py")
    print("Desde el directorio donde está main.py")
    
except Exception as e:
    print(f"\n❌ ERROR GENERAL: {e}")
    import traceback
    traceback.print_exc()