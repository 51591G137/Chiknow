#!/usr/bin/env python3
"""
Script de migración: Mueve test.db del directorio raíz a data/
Y actualiza todas las referencias

Uso: python migrar_test_db.py
"""
import os
import shutil
from datetime import datetime

def migrar_test_db():
    """Migra test.db del directorio raíz a data/"""
    
    print("\n" + "="*70)
    print("🔄 MIGRACIÓN: test.db → data/test.db")
    print("="*70)
    
    # Rutas
    test_db_raiz = "test.db"
    test_db_data = "data/test.db"
    
    # Verificar si existe test.db en raíz
    if not os.path.exists(test_db_raiz):
        print("\n❌ No existe test.db en el directorio raíz")
        print("   Nada que migrar")
        return
    
    # Crear directorio data/ si no existe
    os.makedirs("data", exist_ok=True)
    
    # Verificar si ya existe test.db en data/
    if os.path.exists(test_db_data):
        print("\n⚠️  Ya existe data/test.db")
        
        # Comparar tamaños
        size_raiz = os.path.getsize(test_db_raiz)
        size_data = os.path.getsize(test_db_data)
        
        print(f"\n📊 Comparación:")
        print(f"   test.db (raíz):  {size_raiz / 1024:.2f} KB")
        print(f"   data/test.db:    {size_data / 1024:.2f} KB")
        
        # Determinar cuál es más reciente
        mtime_raiz = os.path.getmtime(test_db_raiz)
        mtime_data = os.path.getmtime(test_db_data)
        
        print(f"\n📅 Fechas de modificación:")
        print(f"   test.db (raíz):  {datetime.fromtimestamp(mtime_raiz)}")
        print(f"   data/test.db:    {datetime.fromtimestamp(mtime_data)}")
        
        # Preguntar qué hacer
        print("\n❓ ¿Qué deseas hacer?")
        print("   1. Reemplazar data/test.db con test.db (raíz)")
        print("   2. Hacer backup de ambos y usar test.db (raíz)")
        print("   3. Mantener data/test.db y eliminar test.db (raíz)")
        print("   4. Cancelar")
        
        opcion = input("\nOpción (1-4): ").strip()
        
        if opcion == "1":
            # Backup de data/test.db
            backup_data = f"backups/data_test_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            os.makedirs("backups", exist_ok=True)
            shutil.copy2(test_db_data, backup_data)
            print(f"\n💾 Backup de data/test.db: {backup_data}")
            
            # Reemplazar
            shutil.copy2(test_db_raiz, test_db_data)
            print(f"✅ data/test.db reemplazado con test.db (raíz)")
            
            # Eliminar test.db de raíz
            os.remove(test_db_raiz)
            print(f"✅ test.db (raíz) eliminado")
            
        elif opcion == "2":
            # Backup de ambos
            os.makedirs("backups", exist_ok=True)
            backup_raiz = f"backups/raiz_test_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_data = f"backups/data_test_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            shutil.copy2(test_db_raiz, backup_raiz)
            shutil.copy2(test_db_data, backup_data)
            
            print(f"\n💾 Backups creados:")
            print(f"   Raíz: {backup_raiz}")
            print(f"   Data: {backup_data}")
            
            # Usar el de raíz
            shutil.copy2(test_db_raiz, test_db_data)
            print(f"\n✅ data/test.db actualizado con test.db (raíz)")
            
            os.remove(test_db_raiz)
            print(f"✅ test.db (raíz) eliminado")
            
        elif opcion == "3":
            # Backup de raíz y eliminar
            os.makedirs("backups", exist_ok=True)
            backup_raiz = f"backups/raiz_test_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(test_db_raiz, backup_raiz)
            
            print(f"\n💾 Backup de test.db (raíz): {backup_raiz}")
            
            os.remove(test_db_raiz)
            print(f"✅ test.db (raíz) eliminado")
            print(f"✅ Manteniendo data/test.db sin cambios")
            
        else:
            print("\n❌ Operación cancelada")
            return
    else:
        # No existe data/test.db, simplemente mover
        print(f"\n📦 Moviendo test.db → data/test.db")
        
        # Hacer backup por seguridad
        os.makedirs("backups", exist_ok=True)
        backup_raiz = f"backups/raiz_test_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(test_db_raiz, backup_raiz)
        print(f"💾 Backup creado: {backup_raiz}")
        
        # Copiar a data/
        shutil.copy2(test_db_raiz, test_db_data)
        print(f"✅ Copiado a data/test.db")
        
        # Eliminar de raíz
        os.remove(test_db_raiz)
        print(f"✅ test.db (raíz) eliminado")
    
    # Verificar resultado
    print("\n" + "="*70)
    print("✅ MIGRACIÓN COMPLETADA")
    print("="*70)
    
    if os.path.exists(test_db_data):
        size = os.path.getsize(test_db_data) / 1024
        print(f"\n✅ data/test.db existe ({size:.2f} KB)")
    
    if not os.path.exists(test_db_raiz):
        print("✅ test.db (raíz) eliminado correctamente")
    
    print("\n📋 Próximos pasos:")
    print("   1. Verificar que la app funciona correctamente")
    print("   2. Si todo está bien, eliminar los backups antiguos")
    print("   3. Asegurarse de que .gitignore incluye data/*.db")
    print("\n💡 Ahora tu base de datos está en data/test.db (buenas prácticas)")

if __name__ == "__main__":
    migrar_test_db()