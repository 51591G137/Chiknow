#!/usr/bin/env python3
"""
Script de diagnóstico completo de Chiknow
Genera un informe con toda la información relevante del proyecto
"""

import os
import json
from datetime import datetime
from pathlib import Path

def header(text):
    """Imprime un encabezado"""
    print("\n" + "="*70)
    print(text.center(70))
    print("="*70)

def subheader(text):
    """Imprime un subencabezado"""
    print("\n" + "-"*70)
    print(text)
    print("-"*70)

def safe_read_file(filepath, lines=None):
    """Lee un archivo de forma segura"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if lines:
                content = []
                for i, line in enumerate(f, 1):
                    if i > lines:
                        content.append(f"... ({sum(1 for _ in open(filepath))} líneas totales)")
                        break
                    content.append(line.rstrip())
                return '\n'.join(content)
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"

def get_file_info(filepath):
    """Obtiene información de un archivo"""
    try:
        stat = os.stat(filepath)
        size = stat.st_size
        if size < 1024:
            size_str = f"{size}B"
        elif size < 1024*1024:
            size_str = f"{size/1024:.1f}KB"
        else:
            size_str = f"{size/(1024*1024):.1f}MB"
        
        lines = sum(1 for _ in open(filepath, 'rb'))
        return f"{size_str} | {lines} líneas"
    except:
        return "?"

# Inicio del diagnóstico
header("DIAGNÓSTICO CHIKNOW")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Directorio: {os.getcwd()}")

# 1. ESTRUCTURA DEL PROYECTO
header("1. ESTRUCTURA DEL PROYECTO")

project_structure = {
    'python': ['*.py'],
    'templates': ['templates/*.html'],
    'static_css': ['static/css/*.css'],
    'static_js': ['static/js/*.js'],
    'data': ['*.csv', '*.db'],
    'config': ['*.txt', '*.yaml', '*.md']
}

for category, patterns in project_structure.items():
    subheader(category.upper())
    found_files = []
    for pattern in patterns:
        for filepath in Path('.').glob(pattern):
            if filepath.is_file():
                found_files.append(filepath)
    
    if found_files:
        for filepath in sorted(found_files):
            info = get_file_info(filepath)
            print(f"  ✓ {filepath} ({info})")
    else:
        print(f"  ⚠️  No se encontraron archivos con patrón: {patterns}")

# 2. BASE DE DATOS
header("2. ESTADO DE LA BASE DE DATOS")

try:
    from database import SessionLocal
    import models
    
    db = SessionLocal()
    
    tables = [
        ('HSK', models.HSK),
        ('Diccionario', models.Diccionario),
        ('Tarjeta', models.Tarjeta),
        ('SM2Progress', models.SM2Progress),
        ('SM2Review', models.SM2Review),
        ('Ejemplo', models.Ejemplo),
        ('HSKEjemplo', models.HSKEjemplo),
        ('EjemploJerarquia', models.EjemploJerarquia),
        ('EjemploActivacion', models.EjemploActivacion),
    ]
    
    for table_name, model in tables:
        try:
            count = db.query(model).count()
            print(f"  ✓ {table_name:20s} : {count:6d} registros")
        except Exception as e:
            print(f"  ✗ {table_name:20s} : ERROR - {str(e)[:50]}")
    
    db.close()
    
except Exception as e:
    print(f"  ✗ ERROR al conectar a la base de datos: {e}")

# 3. RUTAS API DISPONIBLES
header("3. RUTAS API DISPONIBLES")

try:
    import main
    from fastapi.routing import APIRoute
    
    routes = []
    for route in main.app.routes:
        if isinstance(route, APIRoute):
            routes.append({
                'path': route.path,
                'methods': list(route.methods),
                'name': route.name
            })
    
    # Agrupar por prefijo
    route_groups = {}
    for route in sorted(routes, key=lambda x: x['path']):
        prefix = route['path'].split('/')[1] if '/' in route['path'] else 'root'
        if prefix not in route_groups:
            route_groups[prefix] = []
        route_groups[prefix].append(route)
    
    for prefix, group_routes in sorted(route_groups.items()):
        subheader(f"/{prefix}")
        for route in group_routes:
            methods = ', '.join(route['methods'])
            print(f"  {methods:15s} {route['path']}")
    
except Exception as e:
    print(f"  ✗ ERROR al listar rutas: {e}")

# 4. ARCHIVOS HTML - RESUMEN
header("4. ARCHIVOS HTML - RUTAS Y SCRIPTS")

html_files = list(Path('templates').glob('*.html'))
for html_file in sorted(html_files):
    subheader(str(html_file))
    content = safe_read_file(html_file)
    
    # Buscar referencias a CSS
    print("\n  CSS:")
    for line in content.split('\n'):
        if 'href=' in line and ('.css' in line or 'stylesheet' in line):
            print(f"    {line.strip()}")
    
    # Buscar referencias a JS/API
    print("\n  API Calls:")
    for line in content.split('\n'):
        if "fetch('" in line or 'fetch("' in line:
            print(f"    {line.strip()[:80]}")
    
    # Contar líneas de script
    script_lines = content.count('<script>')
    if script_lines > 0:
        print(f"\n  Scripts: {script_lines} bloques <script>")

# 5. ARCHIVOS PYTHON - RESUMEN
header("5. ARCHIVOS PYTHON - FUNCIONES PRINCIPALES")

py_files = ['models.py', 'repository.py', 'service.py', 'main.py']
for py_file in py_files:
    if os.path.exists(py_file):
        subheader(py_file)
        content = safe_read_file(py_file)
        
        # Buscar definiciones de funciones
        functions = []
        for line in content.split('\n'):
            if line.strip().startswith('def ') or line.strip().startswith('async def '):
                func_name = line.strip().split('(')[0].replace('def ', '').replace('async ', '')
                functions.append(func_name)
        
        print(f"  Total funciones: {len(functions)}")
        print(f"  Funciones: {', '.join(functions[:10])}")
        if len(functions) > 10:
            print(f"             ... y {len(functions)-10} más")

# 6. PRUEBAS DE API
header("6. PRUEBAS DE API (llamadas clave)")

try:
    import requests
    
    base_url = "http://localhost:8000"
    tests = [
        ('GET', '/api/hsk', 'Listar palabras HSK'),
        ('GET', '/api/diccionario', 'Listar diccionario'),
        ('GET', '/api/tarjetas', 'Listar tarjetas'),
        ('GET', '/api/sm2/statistics', 'Estadísticas SM2'),
        ('GET', '/api/sm2/cards/due', 'Tarjetas pendientes'),
    ]
    
    print("\n  Probando endpoints...")
    for method, endpoint, description in tests:
        try:
            if method == 'GET':
                response = requests.get(f"{base_url}{endpoint}", timeout=2)
                status = response.status_code
                if status == 200:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"  ✓ {endpoint:30s} → {status} ({len(data)} items)")
                    elif isinstance(data, dict):
                        print(f"  ✓ {endpoint:30s} → {status} ({len(data)} keys)")
                    else:
                        print(f"  ✓ {endpoint:30s} → {status}")
                else:
                    print(f"  ✗ {endpoint:30s} → {status}")
        except Exception as e:
            print(f"  ⚠️  {endpoint:30s} → ERROR: {str(e)[:30]}")
    
except ImportError:
    print("  ⚠️  requests no instalado, saltando pruebas de API")
    print("  💡 Instalar con: pip install requests")

# 7. PROBLEMAS CONOCIDOS
header("7. VERIFICACIÓN DE PROBLEMAS COMUNES")

checks = []

# Check 1: CSS path
css_file = Path('static/css/style.css')
if css_file.exists():
    checks.append(('✓', 'CSS', f'Archivo existe: {css_file}'))
else:
    checks.append(('✗', 'CSS', f'Archivo NO existe: {css_file}'))

# Check 2: HTML CSS references
for html_file in Path('templates').glob('*.html'):
    content = safe_read_file(html_file)
    if '/static/styles.css' in content:
        checks.append(('✗', 'HTML', f'{html_file} usa /static/styles.css (debería ser /static/css/style.css)'))
    elif '/static/css/style.css' in content:
        checks.append(('✓', 'HTML', f'{html_file} usa /static/css/style.css (correcto)'))

# Check 3: API routes in HTML
api_issues = []
for html_file in Path('templates').glob('*.html'):
    content = safe_read_file(html_file)
    if '/api/sm2/start-session' in content:
        api_issues.append(f'{html_file} usa /start-session (debería ser /session/start)')

if api_issues:
    for issue in api_issues:
        checks.append(('✗', 'API', issue))
else:
    checks.append(('✓', 'API', 'Rutas API correctas en HTML'))

# Imprimir checks
for status, category, message in checks:
    print(f"  {status} [{category:8s}] {message}")

# 8. RESUMEN Y RECOMENDACIONES
header("8. RESUMEN EJECUTIVO")

print("""
CÓMO USAR ESTE DIAGNÓSTICO:
  
  1. Ejecuta este script antes de pedir ayuda:
     $ python3 diagnostico_completo.py > diagnostico.txt
  
  2. Revisa el archivo diagnostico.txt
  
  3. Cuando pidas ayuda, proporciona:
     ✓ El output completo de este script
     ✓ Una descripción clara del problema
     ✓ Errores específicos (consola del navegador o servidor)
  
  4. Según el problema, se te pedirá:
     ✓ Contenido específico de archivos HTML
     ✓ Contenido específico de archivos Python
     ✓ Logs del servidor
     ✓ Errores de la consola del navegador

ARCHIVOS CRÍTICOS POR PROBLEMA:
  
  • Problemas de UI/CSS:
    → templates/[página].html
    → static/css/style.css
  
  • Problemas de funcionalidad:
    → main.py (rutas)
    → service.py (lógica de negocio)
    → repository.py (acceso a datos)
  
  • Problemas de base de datos:
    → models.py (esquema)
    → Comando: sqlite3 test.db ".schema"
  
  • Problemas de API:
    → Console del navegador (F12 → Console)
    → main.py (definición de rutas)

PRÓXIMOS PASOS:
  
  1. Revisa la sección "7. VERIFICACIÓN DE PROBLEMAS COMUNES"
  2. Corrige cualquier ✗ que aparezca
  3. Si sigues con problemas, proporciona este diagnóstico completo
""")

header("FIN DEL DIAGNÓSTICO")
print(f"\nGuardado en: diagnostico.txt")
print(f"Para guardar: python3 diagnostico_completo.py > diagnostico.txt\n")