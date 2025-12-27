#!/usr/bin/env python3
"""
Script de verificación completa del flujo de Chiknow
"""

from database import SessionLocal
import models
import repository
import service

db = SessionLocal()

print("="*60)
print("VERIFICACIÓN COMPLETA DEL FLUJO")
print("="*60)

# 1. Verificar HSK
print("\n1. PALABRAS HSK")
print("-"*40)
hsk_count = db.query(models.HSK).count()
print(f"✅ Total palabras HSK: {hsk_count}")

if hsk_count == 0:
    print("❌ ERROR: No hay palabras HSK")
    print("   Ejecuta: python3 cargar_hsk_sin_cabecera.py")
    db.close()
    exit(1)

# Mostrar algunas palabras
ejemplos = db.query(models.HSK).limit(5).all()
print("\nPrimeras 5 palabras:")
for p in ejemplos:
    print(f"  ID:{p.id} - {p.hanzi} ({p.pinyin}) - {p.espanol}")

# 2. Verificar Diccionario
print("\n2. DICCIONARIO")
print("-"*40)
dic_count = db.query(models.Diccionario).count()
print(f"Total entradas en diccionario: {dic_count}")

if dic_count == 0:
    print("⚠️  El diccionario está vacío")
    print("   Esto es NORMAL si acabas de resetear la BD")
    print("\n📝 ACCIÓN REQUERIDA:")
    print("   1. Ve a http://localhost:8000")
    print("   2. En la página principal, haz clic en el botón '+' de alguna palabra")
    print("   3. Eso añadirá la palabra al diccionario")
    print("\n¿Quieres que añada la primera palabra automáticamente? (s/n): ", end="")
    
    respuesta = input()
    if respuesta.lower() == 's':
        print("\n🔄 Añadiendo palabra ID=1 al diccionario...")
        try:
            resultado = service.agregar_palabra_y_generar_tarjetas(db, 1)
            if resultado:
                print("✅ Palabra añadida correctamente")
            else:
                print("❌ Error al añadir palabra")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
else:
    print("✅ Hay palabras en el diccionario")
    # Mostrar palabras en diccionario
    entradas = db.query(models.Diccionario, models.HSK).join(
        models.HSK, models.Diccionario.hsk_id == models.HSK.id
    ).all()
    print("\nPalabras en diccionario:")
    for dic, hsk in entradas[:5]:
        print(f"  {hsk.hanzi} ({hsk.pinyin}) - {hsk.espanol}")

# 3. Verificar Tarjetas
print("\n3. TARJETAS")
print("-"*40)
tarjetas_count = db.query(models.Tarjeta).count()
print(f"Total tarjetas: {tarjetas_count}")

if tarjetas_count == 0:
    print("⚠️  No hay tarjetas")
    print("   Las tarjetas se crean automáticamente al añadir palabras al diccionario")
else:
    print(f"✅ Hay {tarjetas_count} tarjetas")
    
    # Mostrar algunas tarjetas
    tarjetas = db.query(models.Tarjeta, models.HSK).outerjoin(
        models.HSK, models.Tarjeta.hsk_id == models.HSK.id
    ).limit(6).all()
    
    print("\nPrimeras 6 tarjetas:")
    for tarjeta, hsk in tarjetas:
        if hsk:
            activa = "✓" if tarjeta.activa else "✗"
            m1 = tarjeta.mostrado1 or "(audio)"
            print(f"  [{activa}] {hsk.hanzi} | {m1} → {tarjeta.requerido}")

# 4. Verificar SM2 Progress
print("\n4. PROGRESO SM2")
print("-"*40)
progress_count = db.query(models.SM2Progress).count()
print(f"Total registros de progreso: {progress_count}")

if progress_count == 0:
    print("⚠️  No hay progreso registrado")
    print("   Esto es normal si no has estudiado ninguna tarjeta todavía")
else:
    print(f"✅ Hay {progress_count} registros de progreso")

# 5. Verificar Estadísticas
print("\n5. ESTADÍSTICAS SM2")
print("-"*40)
try:
    stats = service.obtener_estadisticas_sm2(db)
    print("Estadísticas:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")
    
    if stats['total_tarjetas'] == 0:
        print("\n⚠️  Total de tarjetas es 0")
        print("   CAUSA: No has añadido palabras al diccionario")
        print("   SOLUCIÓN: Añade palabras desde la página principal")
    
    if stats['tarjetas_pendientes_hoy'] == 0 and stats['total_tarjetas'] > 0:
        print("\n⚠️  No hay tarjetas pendientes")
        print("   CAUSA: Las tarjetas nuevas están esperando")
        print("   SOLUCIÓN: Haz clic en 'Iniciar sesión de estudio'")
        
except Exception as e:
    print(f"❌ ERROR al obtener estadísticas: {e}")
    import traceback
    traceback.print_exc()

# 6. Probar obtener tarjetas para estudiar
print("\n6. TARJETAS PARA ESTUDIAR")
print("-"*40)
try:
    tarjetas_estudio = service.obtener_tarjetas_para_estudiar(db, limite=10)
    print(f"Tarjetas disponibles para estudiar: {len(tarjetas_estudio)}")
    
    if len(tarjetas_estudio) == 0:
        print("⚠️  No hay tarjetas para estudiar")
        print("   Posibles causas:")
        print("   1. No has añadido palabras al diccionario")
        print("   2. Las tarjetas están pausadas (activa=False)")
        print("   3. Ya estudiaste todas las tarjetas de hoy")
    else:
        print("\nPrimeras tarjetas para estudiar:")
        for t in tarjetas_estudio[:3]:
            print(f"  {t['hanzi']} | {t['mostrado1'] or '(audio)'} → {t['requerido']}")
            
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("RESUMEN")
print("="*60)

if hsk_count > 0 and dic_count > 0 and tarjetas_count > 0:
    print("✅ Todo está configurado correctamente")
    print("\n📚 SIGUIENTE PASO:")
    print("   1. Ve a http://localhost:8000/sm2")
    print("   2. Haz clic en 'Iniciar sesión de estudio'")
    print("   3. Usa los botones 0 (Again), 1 (Hard), 2 (Easy)")
elif hsk_count > 0 and dic_count == 0:
    print("⚠️  Necesitas añadir palabras al diccionario")
    print("\n📚 ACCIÓN REQUERIDA:")
    print("   1. Ve a http://localhost:8000")
    print("   2. Haz clic en '+' junto a alguna palabra")
    print("   3. Luego ve a /sm2 para estudiar")
else:
    print("❌ Faltan datos por cargar")
    print("\n📚 ACCIÓN REQUERIDA:")
    print("   1. Ejecuta: python3 cargar_hsk_sin_cabecera.py")
    print("   2. Añade palabras al diccionario")
    print("   3. Ve a /sm2 para estudiar")

db.close()