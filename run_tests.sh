#!/bin/bash
# Script para ejecutar todos los tests de Chiknow

set -e  # Salir si cualquier comando falla

echo "🧪 =========================================="
echo "🧪 CHIKNOW - SUITE DE TESTS"
echo "🧪 =========================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Verificar que estamos en el directorio correcto
if [ ! -f "app/main.py" ]; then
    print_color $RED "❌ Error: Debes ejecutar este script desde el directorio raíz del proyecto"
    exit 1
fi

# Crear directorio de logs si no existe
mkdir -p logs

# ============================================================================
# FASE 1: Tests Unitarios
# ============================================================================
print_color $BLUE "
📋 FASE 1: TESTS UNITARIOS"
print_color $YELLOW "─────────────────────────────────────────"

print_color $GREEN "
✓ Ejecutando tests de utils.py..."
pytest tests/test_utils.py -v --tb=short || {
    print_color $RED "❌ Tests de utils fallaron"
    exit 1
}

print_color $GREEN "
✓ Ejecutando tests de schemas.py..."
pytest tests/test_cache.py -v --tb=short || {
    print_color $RED "❌ Tests de schemas fallaron"
    exit 1
}

print_color $GREEN "
✓ Ejecutando tests de cache.py..."
pytest tests/test_cache_functionality.py -v --tb=short || {
    print_color $RED "❌ Tests de cache fallaron"
    exit 1
}

print_color $GREEN "
✅ Tests unitarios completados exitosamente
"

# ============================================================================
# FASE 2: Tests de Integración
# ============================================================================
print_color $BLUE "
📋 FASE 2: TESTS DE INTEGRACIÓN"
print_color $YELLOW "─────────────────────────────────────────"

print_color $GREEN "
✓ Ejecutando tests de API..."
pytest tests/test_api.py -v --tb=short || {
    print_color $RED "❌ Tests de API fallaron"
    exit 1
}

print_color $GREEN "
✓ Ejecutando tests de SM2..."
pytest tests/test_sm2.py -v --tb=short || {
    print_color $RED "❌ Tests de SM2 fallaron"
    exit 1
}

print_color $GREEN "
✅ Tests de integración completados exitosamente
"

# ============================================================================
# FASE 3: Reporte de Coverage
# ============================================================================
print_color $BLUE "
📋 FASE 3: REPORTE DE COBERTURA"
print_color $YELLOW "─────────────────────────────────────────"

print_color $GREEN "
✓ Generando reporte de cobertura..."
pytest --cov=app --cov-report=term-missing --cov-report=html tests/ || {
    print_color $YELLOW "⚠️  Advertencia: No se pudo generar reporte de coverage"
}

if [ -d "htmlcov" ]; then
    print_color $GREEN "
✅ Reporte HTML generado en: htmlcov/index.html"
fi

# ============================================================================
# FASE 4: Verificación de Imports
# ============================================================================
print_color $BLUE "
📋 FASE 4: VERIFICACIÓN DE IMPORTS"
print_color $YELLOW "─────────────────────────────────────────"

print_color $GREEN "✓ Verificando imports de main.py..."
python -c "from app.main import app; print('  ✅ main.py OK')" || {
    print_color $RED "❌ Error en imports de main.py"
    exit 1
}

print_color $GREEN "✓ Verificando imports de repository.py..."
python -c "from app.repository import *; print('  ✅ repository.py OK')" || {
    print_color $RED "❌ Error en imports de repository.py"
    exit 1
}

print_color $GREEN "✓ Verificando imports de service.py..."
python -c "from app.service import *; print('  ✅ service.py OK')" || {
    print_color $RED "❌ Error en imports de service.py"
    exit 1
}

print_color $GREEN "✓ Verificando imports de utils.py..."
python -c "from app.utils import *; print('  ✅ utils.py OK')" || {
    print_color $RED "❌ Error en imports de utils.py"
    exit 1
}

print_color $GREEN "
✅ Todos los imports verificados
"

# ============================================================================
# FASE 5: Verificación de Base de Datos
# ============================================================================
print_color $BLUE "
📋 FASE 5: VERIFICACIÓN DE BASE DE DATOS"
print_color $YELLOW "─────────────────────────────────────────"

print_color $GREEN "✓ Verificando conexión a BD..."
python -c "from app.database import engine; engine.connect(); print('  ✅ Conexión a BD OK')" || {
    print_color $RED "❌ Error conectando a BD"
    exit 1
}

print_color $GREEN "
✅ Base de datos verificada
"

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print_color $GREEN "
╔════════════════════════════════════════════╗
║                                            ║
║  ✅ TODOS LOS TESTS PASARON EXITOSAMENTE  ║
║                                            ║
╚════════════════════════════════════════════╝
"

print_color $BLUE "
📊 RESUMEN:
   ✓ Tests unitarios: OK
   ✓ Tests de integración: OK
   ✓ Coverage generado: htmlcov/index.html
   ✓ Imports verificados: OK
   ✓ Base de datos: OK
"

print_color $YELLOW "
💡 Próximos pasos:
   1. Revisar reporte de coverage: open htmlcov/index.html
   2. Iniciar servidor: uvicorn app.main:app --reload
   3. Probar manualmente: http://localhost:8000
"

exit 0
