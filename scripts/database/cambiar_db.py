#!/usr/bin/env python3
"""
Cambia entre base de datos local y producción
Uso: 
  python scripts/cambiar_bd.py local
  python scripts/cambiar_bd.py produccion
"""
import sys
import os

def cambiar_entorno(nuevo_entorno):
    """Cambia el entorno en el archivo .env"""
    if nuevo_entorno not in ['local', 'produccion']:
        print("❌ Entorno debe ser 'local' o 'produccion'")
        return False
    
    # Leer .env
    env_file = '.env'
    if not os.path.exists(env_file):
        print("❌ No existe archivo .env")
        print("   Crea uno copiando .env.example:")
        print("   cp .env.example .env")
        return False
    
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Actualizar línea DB_ENVIRONMENT
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('DB_ENVIRONMENT='):
            lines[i] = f'DB_ENVIRONMENT={nuevo_entorno}\n'
            updated = True
            break
    
    if not updated:
        lines.append(f'\nDB_ENVIRONMENT={nuevo_entorno}\n')
    
    # Escribir .env
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"✅ Entorno cambiado a: {nuevo_entorno.upper()}")
    
    if nuevo_entorno == 'produccion':
        print("\n⚠️  ADVERTENCIA:")
        print("   Ahora estás conectado a PRODUCCIÓN")
        print("   Los cambios afectarán a usuarios reales")
        print("\n💡 Tip: Verifica con 'python scripts/info_bd.py'")
    else:
        print("\n✅ Ahora estás en modo LOCAL")
        print("   Puedes experimentar sin preocupaciones")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n📖 Uso:")
        print("  python scripts/cambiar_bd.py local")
        print("  python scripts/cambiar_bd.py produccion")
        print("\n💡 Ver estado actual: python scripts/info_bd.py")
        sys.exit(1)
    
    entorno = sys.argv[1].lower()
    cambiar_entorno(entorno)