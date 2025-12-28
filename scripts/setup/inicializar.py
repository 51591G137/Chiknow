"""
Script de Inicialización Completa - Chiknow

Este script ejecuta todos los pasos necesarios para configurar o actualizar el proyecto:
1. Migración de base de datos
2. Carga de datos HSK
3. Carga de ejemplos
4. Diagnóstico final

Uso:
    python inicializar.py --completo     # Ejecuta todo
    python inicializar.py --solo-datos   # Solo actualiza datos
    python inicializar.py --diagnostico  # Solo diagnóstico
"""

import sys
import os
import argparse
import subprocess

def print_header(title):
    """Imprime un encabezado bonito"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def ejecutar_script(script_path, descripcion):
    """Ejecuta un script Python y muestra su salida"""
    print(f"▶️  Ejecutando: {descripcion}")
    print(f"   Archivo: {script_path}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=False,
            text=True,
            check=True
        )
        print(f"\n✅ {descripcion} - COMPLETADO\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {descripcion} - ERROR\n")
        print(f"Código de salida: {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n❌ No se encontró el archivo: {script_path}\n")
        return False

def verificar_archivos():
    """Verifica que existan los archivos necesarios"""
    print_header("VERIFICACIÓN DE ARCHIVOS")
    
    archivos_criticos = [
        "diagnosis/migrar_bd.py",
        "datos/cargar_hsk.py",
        "datos/cargar_ejemplos.py",
        "diagnosis/diagnostico_consolidado.py",
        "database.py",
        "models.py",
        "repository.py",
        "service.py"
    ]
    
    archivos_datos = [
        "datos/hsk.csv",
        "datos/ejemplos.csv"
    ]
    
    print("📁 Archivos críticos del sistema:")
    todos_ok = True
    for archivo in archivos_criticos:
        existe = os.path.exists(archivo)
        simbolo = "✅" if existe else "❌"
        print(f"   {simbolo} {archivo}")
        if not existe:
            todos_ok = False
    
    print("\n📄 Archivos de datos:")
    datos_ok = True
    for archivo in archivos_datos:
        existe = os.path.exists(archivo)
        simbolo = "✅" if existe else "⚠️ "
        print(f"   {simbolo} {archivo}")
        if not existe:
            datos_ok = False
    
    if not todos_ok:
        print("\n❌ Faltan archivos críticos del sistema")
        return False
    
    if not datos_ok:
        print("\n⚠️  Advertencia: Faltan archivos de datos CSV")
        print("   Los scripts de carga fallarán sin estos archivos")
        respuesta = input("\n¿Deseas continuar de todos modos? (s/n): ")
        return respuesta.lower() == 's'
    
    print("\n✅ Todos los archivos necesarios están presentes")
    return True

def hacer_backup():
    """Crea un backup de la base de datos si existe"""
    print_header("BACKUP DE BASE DE DATOS")
    
    if not os.path.exists("test.db"):
        print("ℹ️  No existe base de datos previa (test.db)")
        print("   Se creará una nueva base de datos")
        return True
    
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"test.db.backup_{timestamp}"
    
    try:
        shutil.copy2("test.db", backup_name)
        print(f"✅ Backup creado: {backup_name}")
        print(f"   Tamaño: {os.path.getsize('test.db') / 1024:.2f} KB")
        return True
    except Exception as e:
        print(f"❌ Error al crear backup: {e}")
        respuesta = input("\n¿Deseas continuar sin backup? (s/n): ")
        return respuesta.lower() == 's'

def migrar_bd():
    """Ejecuta la migración de base de datos"""
    print_header("PASO 1: MIGRACIÓN DE BASE DE DATOS")
    
    print("⚠️  IMPORTANTE:")
    print("   - Esta migración actualiza la estructura de la BD")
    print("   - Añade nuevas columnas y tablas")
    print("   - Es seguro y no elimina datos")
    
    respuesta = input("\n¿Deseas ejecutar la migración? (s/n): ")
    if respuesta.lower() != 's':
        print("⏭️  Migración omitida")
        return False
    
    return ejecutar_script(
        "diagnosis/migrar_bd.py",
        "Migración de Base de Datos"
    )

def cargar_hsk():
    """Carga datos de HSK"""
    print_header("PASO 2: CARGA DE DATOS HSK")
    
    if not os.path.exists("datos/hsk.csv"):
        print("❌ No se encontró datos/hsk.csv")
        print("   Omitiendo carga de HSK")
        return False
    
    return ejecutar_script(
        "datos/cargar_hsk.py",
        "Carga de Datos HSK"
    )

def cargar_ejemplos():
    """Carga ejemplos"""
    print_header("PASO 3: CARGA DE EJEMPLOS")
    
    if not os.path.exists("datos/ejemplos.csv"):
        print("❌ No se encontró datos/ejemplos.csv")
        print("   Omitiendo carga de ejemplos")
        return False
    
    return ejecutar_script(
        "datos/cargar_ejemplos.py",
        "Carga de Ejemplos"
    )

def diagnostico():
    """Ejecuta el diagnóstico"""
    print_header("PASO 4: DIAGNÓSTICO FINAL")
    
    return ejecutar_script(
        "diagnosis/diagnostico_consolidado.py",
        "Diagnóstico del Sistema"
    )

def inicializacion_completa():
    """Ejecuta el proceso completo de inicialización"""
    print_header("🚀 INICIALIZACIÓN COMPLETA - CHIKNOW")
    
    print("Este proceso ejecutará:")
    print("   1. ✅ Verificación de archivos")
    print("   2. 💾 Backup de base de datos")
    print("   3. 🔄 Migración de estructura")
    print("   4. 📥 Carga de datos HSK")
    print("   5. 💬 Carga de ejemplos")
    print("   6. 🔍 Diagnóstico final")
    
    respuesta = input("\n¿Deseas continuar? (s/n): ")
    if respuesta.lower() != 's':
        print("\n❌ Proceso cancelado")
        return
    
    # Paso 0: Verificar archivos
    if not verificar_archivos():
        print("\n❌ Inicialización abortada por archivos faltantes")
        return
    
    # Paso 0.5: Backup
    if not hacer_backup():
        print("\n❌ Inicialización abortada")
        return
    
    # Paso 1: Migración
    if not migrar_bd():
        print("\n⚠️  Migración falló o fue omitida")
    
    # Paso 2: Cargar HSK
    if not cargar_hsk():
        print("\n⚠️  Carga de HSK falló o fue omitida")
    
    # Paso 3: Cargar ejemplos
    if not cargar_ejemplos():
        print("\n⚠️  Carga de ejemplos falló o fue omitida")
    
    # Paso 4: Diagnóstico
    diagnostico()
    
    print_header("✅ INICIALIZACIÓN COMPLETADA")
    print("Próximos pasos:")
    print("   1. Revisar el diagnóstico anterior")
    print("   2. Iniciar el servidor: uvicorn main:app --reload")
    print("   3. Abrir navegador: http://localhost:8000")
    print()

def solo_datos():
    """Solo actualiza datos (HSK y ejemplos)"""
    print_header("📥 ACTUALIZACIÓN DE DATOS")
    
    if not verificar_archivos():
        return
    
    hacer_backup()
    cargar_hsk()
    cargar_ejemplos()
    diagnostico()

def solo_diagnostico():
    """Solo ejecuta el diagnóstico"""
    print_header("🔍 DIAGNÓSTICO")
    diagnostico()

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Script de inicialización de Chiknow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python inicializar.py --completo      # Proceso completo
  python inicializar.py --solo-datos    # Solo actualizar datos
  python inicializar.py --diagnostico   # Solo diagnóstico
  python inicializar.py                 # Modo interactivo
        """
    )
    
    parser.add_argument(
        '--completo',
        action='store_true',
        help='Ejecuta el proceso completo de inicialización'
    )
    
    parser.add_argument(
        '--solo-datos',
        action='store_true',
        help='Solo actualiza los datos (HSK y ejemplos)'
    )
    
    parser.add_argument(
        '--diagnostico',
        action='store_true',
        help='Solo ejecuta el diagnóstico'
    )
    
    args = parser.parse_args()
    
    if args.completo:
        inicializacion_completa()
    elif args.solo_datos:
        solo_datos()
    elif args.diagnostico:
        solo_diagnostico()
    else:
        # Modo interactivo
        print("\n" + "="*70)
        print("  🚀 CHIKNOW - SCRIPT DE INICIALIZACIÓN")
        print("="*70)
        print("\nSelecciona una opción:")
        print("  1. Inicialización completa (recomendado para primera vez)")
        print("  2. Solo actualizar datos (HSK y ejemplos)")
        print("  3. Solo ejecutar diagnóstico")
        print("  4. Salir")
        
        opcion = input("\nOpción (1-4): ").strip()
        
        if opcion == '1':
            inicializacion_completa()
        elif opcion == '2':
            solo_datos()
        elif opcion == '3':
            solo_diagnostico()
        elif opcion == '4':
            print("\n👋 ¡Hasta luego!")
        else:
            print("\n❌ Opción no válida")

if __name__ == "__main__":
    main()