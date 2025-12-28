"""
Script de Diagnóstico Consolidado - Chiknow

Este script unifica y actualiza todos los diagnósticos previos:
- Verifica la estructura de la base de datos
- Muestra estadísticas de todas las tablas
- Identifica problemas y advertencias
- Proporciona recomendaciones
"""

import sys
import os

# Añadir directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect
from database import SessionLocal, engine
import models

def print_section(title):
    """Imprime un título de sección"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def verificar_estructura_bd():
    """Verifica que todas las tablas existan"""
    print_section("1. VERIFICACIÓN DE ESTRUCTURA DE BASE DE DATOS")
    
    inspector = inspect(engine)
    tablas_esperadas = [
        'hsk', 'notas', 'diccionario', 'tarjetas', 'ejemplos', 
        'hsk_ejemplo', 'ejemplo_jerarquia', 'sm2_sessions', 
        'sm2_progress', 'sm2_reviews', 'ejemplo_activacion'
    ]
    
    tablas_existentes = inspector.get_table_names()
    
    print("\n✅ Tablas existentes:")
    for tabla in tablas_existentes:
        print(f"   - {tabla}")
    
    print("\n🔍 Verificación:")
    todas_ok = True
    for tabla in tablas_esperadas:
        if tabla in tablas_existentes:
            print(f"   ✅ {tabla}")
        else:
            print(f"   ❌ {tabla} - FALTA")
            todas_ok = False
    
    if todas_ok:
        print("\n✅ Todas las tablas están presentes")
    else:
        print("\n⚠️  Algunas tablas faltan. Ejecuta las migraciones.")
    
    return todas_ok

def verificar_columnas_hsk():
    """Verifica las columnas de la tabla HSK"""
    print_section("2. VERIFICACIÓN DE COLUMNAS HSK")
    
    inspector = inspect(engine)
    columnas = [col['name'] for col in inspector.get_columns('hsk')]
    
    columnas_esperadas = [
        'id', 'numero', 'nivel', 'hanzi', 'pinyin', 'espanol',
        'hanzi_alt', 'pinyin_alt', 'categoria', 'ejemplo', 'significado_ejemplo'
    ]
    
    print("\n✅ Columnas existentes:")
    for col in columnas:
        print(f"   - {col}")
    
    print("\n🔍 Verificación:")
    todas_ok = True
    for col in columnas_esperadas:
        if col in columnas:
            print(f"   ✅ {col}")
        else:
            print(f"   ❌ {col} - FALTA")
            todas_ok = False
    
    if todas_ok:
        print("\n✅ Todas las columnas están presentes")
    else:
        print("\n⚠️  Algunas columnas faltan. Ejecuta: alembic upgrade head")
    
    return todas_ok

def estadisticas_hsk(db):
    """Muestra estadísticas de la tabla HSK"""
    print_section("3. ESTADÍSTICAS HSK")
    
    total = db.query(models.HSK).count()
    
    print(f"\n📊 Total palabras HSK: {total}")
    
    if total > 0:
        # Por nivel
        print("\n📈 Distribución por nivel:")
        for nivel in range(1, 7):
            count = db.query(models.HSK).filter(models.HSK.nivel == nivel).count()
            print(f"   HSK {nivel}: {count} palabras")
        
        # Con alternativas
        con_hanzi_alt = db.query(models.HSK).filter(models.HSK.hanzi_alt != None).count()
        con_categoria = db.query(models.HSK).filter(models.HSK.categoria != None).count()
        con_ejemplo = db.query(models.HSK).filter(models.HSK.ejemplo != None).count()
        
        print(f"\n📝 Datos adicionales:")
        print(f"   Con hanzi alternativo: {con_hanzi_alt}")
        print(f"   Con categoría: {con_categoria}")
        print(f"   Con ejemplo: {con_ejemplo}")
    else:
        print("\n⚠️  No hay datos HSK. Ejecuta: python datos/cargar_hsk.py")

def estadisticas_notas(db):
    """Muestra estadísticas de la tabla Notas"""
    print_section("4. ESTADÍSTICAS NOTAS")
    
    total = db.query(models.Notas).count()
    print(f"\n📝 Total notas: {total}")
    
    if total > 0:
        print("\n🔍 Muestra de notas:")
        notas = db.query(models.Notas, models.HSK).join(
            models.HSK, models.Notas.hsk_id == models.HSK.id
        ).limit(5).all()
        
        for nota, hsk in notas:
            texto_corto = nota.nota[:50] + "..." if len(nota.nota) > 50 else nota.nota
            print(f"   {hsk.hanzi} ({hsk.pinyin}): {texto_corto}")

def estadisticas_diccionario(db):
    """Muestra estadísticas del diccionario"""
    print_section("5. ESTADÍSTICAS DICCIONARIO")
    
    total = db.query(models.Diccionario).count()
    activos = db.query(models.Diccionario).filter(models.Diccionario.activo == True).count()
    
    print(f"\n📚 Total palabras en diccionario: {total}")
    print(f"   Activas: {activos}")
    print(f"   Inactivas: {total - activos}")
    
    if total > 0:
        # Distribución por nivel
        print("\n📈 Distribución por nivel HSK:")
        for nivel in range(1, 7):
            count = db.query(models.Diccionario).join(
                models.HSK, models.Diccionario.hsk_id == models.HSK.id
            ).filter(models.HSK.nivel == nivel).count()
            print(f"   HSK {nivel}: {count} palabras")

def estadisticas_tarjetas(db):
    """Muestra estadísticas de tarjetas"""
    print_section("6. ESTADÍSTICAS TARJETAS")
    
    total = db.query(models.Tarjeta).count()
    activas = db.query(models.Tarjeta).filter(models.Tarjeta.activa == True).count()
    de_palabras = db.query(models.Tarjeta).filter(models.Tarjeta.hsk_id != None).count()
    de_ejemplos = db.query(models.Tarjeta).filter(models.Tarjeta.ejemplo_id != None).count()
    
    print(f"\n🗂️  Total tarjetas: {total}")
    print(f"   Activas: {activas}")
    print(f"   Inactivas: {total - activas}")
    print(f"\n📊 Por tipo:")
    print(f"   De palabras: {de_palabras}")
    print(f"   De ejemplos: {de_ejemplos}")

def estadisticas_ejemplos(db):
    """Muestra estadísticas de ejemplos"""
    print_section("7. ESTADÍSTICAS EJEMPLOS")
    
    total = db.query(models.Ejemplo).count()
    activados = db.query(models.Ejemplo).filter(models.Ejemplo.activado == True).count()
    en_diccionario = db.query(models.Ejemplo).filter(models.Ejemplo.en_diccionario == True).count()
    
    print(f"\n💬 Total ejemplos: {total}")
    print(f"   Activados: {activados}")
    print(f"   En diccionario del usuario: {en_diccionario}")
    
    if total > 0:
        print("\n📈 Por complejidad:")
        for comp in [1, 2, 3]:
            count = db.query(models.Ejemplo).filter(models.Ejemplo.complejidad == comp).count()
            nombre = "Simple" if comp == 1 else "Medio" if comp == 2 else "Complejo"
            print(f"   {nombre}: {count}")
        
        # Relaciones
        total_relaciones = db.query(models.HSKEjemplo).count()
        print(f"\n🔗 Relaciones HSK-Ejemplo: {total_relaciones}")

def estadisticas_sm2(db):
    """Muestra estadísticas del sistema SM2"""
    print_section("8. ESTADÍSTICAS SISTEMA SM2")
    
    # Sesiones
    total_sesiones = db.query(models.SM2Session).count()
    print(f"\n📅 Total sesiones: {total_sesiones}")
    
    if total_sesiones > 0:
        ultima_sesion = db.query(models.SM2Session).order_by(
            models.SM2Session.fecha_inicio.desc()
        ).first()
        print(f"   Última sesión: {ultima_sesion.fecha_inicio}")
    
    # Progreso
    total_progress = db.query(models.SM2Progress).count()
    print(f"\n📊 Tarjetas con progreso: {total_progress}")
    
    if total_progress > 0:
        print("\n📈 Por estado:")
        for estado in ['nuevo', 'aprendiendo', 'dominada', 'madura']:
            count = db.query(models.SM2Progress).filter(
                models.SM2Progress.estado == estado
            ).count()
            print(f"   {estado.capitalize()}: {count}")
        
        # Estadísticas de revisiones
        total_reviews = db.query(models.SM2Review).count()
        print(f"\n🔄 Total revisiones: {total_reviews}")

def verificar_integridad(db):
    """Verifica la integridad referencial"""
    print_section("9. VERIFICACIÓN DE INTEGRIDAD")
    
    problemas = []
    
    # Diccionario sin HSK
    dict_sin_hsk = db.query(models.Diccionario).outerjoin(
        models.HSK, models.Diccionario.hsk_id == models.HSK.id
    ).filter(models.HSK.id == None).count()
    
    if dict_sin_hsk > 0:
        problemas.append(f"⚠️  {dict_sin_hsk} entradas de diccionario sin HSK asociado")
    
    # Tarjetas sin referencia
    tarjetas_huerfanas = db.query(models.Tarjeta).filter(
        models.Tarjeta.hsk_id == None,
        models.Tarjeta.ejemplo_id == None
    ).count()
    
    if tarjetas_huerfanas > 0:
        problemas.append(f"⚠️  {tarjetas_huerfanas} tarjetas sin referencia a HSK o Ejemplo")
    
    # Progress sin tarjeta
    progress_sin_tarjeta = db.query(models.SM2Progress).outerjoin(
        models.Tarjeta, models.SM2Progress.tarjeta_id == models.Tarjeta.id
    ).filter(models.Tarjeta.id == None).count()
    
    if progress_sin_tarjeta > 0:
        problemas.append(f"⚠️  {progress_sin_tarjeta} registros de progreso sin tarjeta")
    
    if problemas:
        print("\n⚠️  Problemas encontrados:")
        for problema in problemas:
            print(f"   {problema}")
    else:
        print("\n✅ No se encontraron problemas de integridad")

def recomendaciones(db):
    """Proporciona recomendaciones"""
    print_section("10. RECOMENDACIONES")
    
    recs = []
    
    # Verificar datos HSK
    total_hsk = db.query(models.HSK).count()
    if total_hsk == 0:
        recs.append("📥 Cargar datos HSK: python datos/cargar_hsk.py")
    
    # Verificar diccionario
    total_dict = db.query(models.Diccionario).count()
    if total_dict == 0:
        recs.append("📚 Añadir palabras al diccionario desde la interfaz web")
    
    # Verificar ejemplos
    total_ejemplos = db.query(models.Ejemplo).count()
    if total_ejemplos == 0:
        recs.append("💬 Cargar ejemplos: python datos/cargar_ejemplos.py")
    
    # Verificar sesiones
    total_sesiones = db.query(models.SM2Session).count()
    if total_sesiones == 0:
        recs.append("🧠 Iniciar primera sesión de estudio desde /sm2")
    
    if recs:
        print("\n📋 Acciones recomendadas:")
        for i, rec in enumerate(recs, 1):
            print(f"   {i}. {rec}")
    else:
        print("\n✅ El sistema está funcionando correctamente")

def main():
    """Función principal"""
    print("\n" + "="*70)
    print("  🔍 DIAGNÓSTICO CONSOLIDADO - CHIKNOW")
    print("="*70)
    
    db = SessionLocal()
    
    try:
        # Ejecutar todas las verificaciones
        verificar_estructura_bd()
        verificar_columnas_hsk()
        
        estadisticas_hsk(db)
        estadisticas_notas(db)
        estadisticas_diccionario(db)
        estadisticas_tarjetas(db)
        estadisticas_ejemplos(db)
        estadisticas_sm2(db)
        
        verificar_integridad(db)
        recomendaciones(db)
        
        print("\n" + "="*70)
        print("  ✅ DIAGNÓSTICO COMPLETADO")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error durante el diagnóstico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()