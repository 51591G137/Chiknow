#!/bin/bash
# Script de verificación completa de la instalación de Chiknow

set -e

echo "🔍 =========================================="
echo "🔍 CHIKNOW - VERIFICACIÓN DE INSTALACIÓN"
echo "🔍 =========================================="
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

passed=0
failed=0

check_passed() {
    echo -e "${GREEN}✅ $1${NC}"
    ((passed++))
}

check_failed() {
    echo -e "${RED}❌ $1${NC}"
    ((failed++))
}

check_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# ============================================================================
# 1. VERIFICAR ARCHIVOS CRÍTICOS
# ============================================================================
echo -e "${BLUE}📁 Verificando archivos críticos...${NC}"

files=(
    "app/main.py"
    "app/repository.py"
    "app/service.py"
    "app/models.py"
    "app/database.py"
    "app/config.py"
    "app/utils.py"
    "app/schemas.py"
    "app/decorators.py"
    "app/cache.py"
    "app/middleware.py"
    "app/logging_config.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        check_passed "Archivo existe: $file"
    else
        check_failed "Archivo faltante: $file"
    fi
done

echo ""

# ============================================================================
# 2. VERIFICAR IMPORTS
# ============================================================================
echo -e "${BLUE}📦 Verificando imports...${NC}"

# Import crítico: sqlalchemy text
if python -c "from app.main import app" 2>/dev/null; then
    if grep -q "from sqlalchemy import text" app/main.py; then
        check_passed "Import crítico 'text' presente en main.py"
    else
        check_failed "Import crítico 'text' FALTANTE en main.py"
    fi
else
    check_failed "No se puede importar app.main"
fi

# Verificar otros imports
python -c "from app.utils import now_utc" 2>/dev/null && \
    check_passed "Import: app.utils" || \
    check_failed "Import: app.utils"

python -c "from app.schemas import ReviewRequest" 2>/dev/null && \
    check_passed "Import: app.schemas" || \
    check_failed "Import: app.schemas"

python -c "from app.decorators import transactional" 2>/dev/null && \
    check_passed "Import: app.decorators" || \
    check_failed "Import: app.decorators"

python -c "from app.cache import cache" 2>/dev/null && \
    check_passed "Import: app.cache" || \
    check_failed "Import: app.cache"

echo ""

# ============================================================================
# 3. VERIFICAR TIMEZONE CONSISTENCY
# ============================================================================
echo -e "${BLUE}⏰ Verificando consistencia de timezone...${NC}"

# Verificar que now_utc() está en uso
if grep -q "from .utils import now_utc" app/repository.py && \
   grep -q "from .utils import now_utc" app/service.py; then
    check_passed "now_utc() importado en repository.py y service.py"
else
    check_failed "now_utc() no está importado correctamente"
fi

# Verificar que no hay datetime.utcnow() remanente en service.py
if grep -q "datetime.utcnow()" app/service.py; then
    check_failed "datetime.utcnow() AÚN PRESENTE en service.py - debe ser now_utc()"
else
    check_passed "Sin datetime.utcnow() en service.py"
fi

echo ""

# ============================================================================
# 4. VERIFICAR @transactional
# ============================================================================
echo -e "${BLUE}🔄 Verificando decorators @transactional...${NC}"

if grep -q "from .decorators import transactional" app/service.py; then
    check_passed "@transactional importado en service.py"
    
    # Contar usos
    count=$(grep -c "@transactional" app/service.py || echo "0")
    if [ "$count" -gt "0" ]; then
        check_passed "@transactional usado $count veces en service.py"
    else
        check_warning "@transactional importado pero no usado"
    fi
else
    check_failed "@transactional NO importado en service.py"
fi

echo ""

# ============================================================================
# 5. VERIFICAR CACHÉ
# ============================================================================
echo -e "${BLUE}💾 Verificando sistema de caché...${NC}"

if grep -q "from .cache import cache, invalidate_cache" app/repository.py; then
    check_passed "Cache importado en repository.py"
    
    # Verificar que se usa
    if grep -q "@cache(ttl_seconds" app/repository.py; then
        check_passed "Decorator @cache en uso"
    else
        check_warning "Cache importado pero decorator no usado"
    fi
    
    if grep -q "invalidate_cache" app/repository.py; then
        check_passed "invalidate_cache() en uso"
    else
        check_warning "invalidate_cache() no encontrado"
    fi
else
    check_failed "Cache NO importado en repository.py"
fi

echo ""

# ============================================================================
# 6. VERIFICAR VALIDACIÓN PYDANTIC
# ============================================================================
echo -e "${BLUE}✔️  Verificando validación Pydantic...${NC}"

if grep -q "schemas.ReviewRequest" app/main.py; then
    check_passed "schemas.ReviewRequest usado en main.py"
else
    check_failed "schemas.ReviewRequest NO usado en main.py"
fi

if grep -q "schemas.NotaRequest" app/main.py; then
    check_passed "schemas.NotaRequest usado en main.py"
else
    check_failed "schemas.NotaRequest NO usado en main.py"
fi

echo ""

# ============================================================================
# 7. VERIFICAR ERROR HANDLING
# ============================================================================
echo -e "${BLUE}🛡️  Verificando manejo de errores...${NC}"

# Verificar try/except en main.py
try_count=$(grep -c "try:" app/main.py || echo "0")
except_count=$(grep -c "except" app/main.py || echo "0")

if [ "$try_count" -gt "10" ] && [ "$except_count" -gt "10" ]; then
    check_passed "Try/except presente en main.py ($try_count bloques)"
else
    check_failed "Insuficientes try/except en main.py"
fi

# Verificar HTTPException
if grep -q "raise HTTPException" app/main.py; then
    check_passed "HTTPException en uso"
else
    check_failed "HTTPException NO encontrado"
fi

echo ""

# ============================================================================
# 8. VERIFICAR LOGGING
# ============================================================================
echo -e "${BLUE}📝 Verificando logging...${NC}"

if grep -q "import logging" app/repository.py && \
   grep -q "logger = logging.getLogger" app/repository.py; then
    check_passed "Logging configurado en repository.py"
else
    check_failed "Logging NO configurado en repository.py"
fi

if grep -q "import logging" app/service.py && \
   grep -q "logger = logging.getLogger" app/service.py; then
    check_passed "Logging configurado en service.py"
else
    check_failed "Logging NO configurado en service.py"
fi

# Verificar directorio de logs
if [ -d "logs" ]; then
    check_passed "Directorio logs/ existe"
else
    check_warning "Directorio logs/ no existe - se creará al iniciar"
fi

echo ""

# ============================================================================
# 9. VERIFICAR BASE DE DATOS
# ============================================================================
echo -e "${BLUE}🗄️  Verificando base de datos...${NC}"

python -c "from app.database import engine; engine.connect(); print('OK')" 2>/dev/null && \
    check_passed "Conexión a base de datos OK" || \
    check_failed "No se puede conectar a la base de datos"

# Verificar columna version en sm2_progress
python -c "
from app.database import SessionLocal, engine
from sqlalchemy import inspect
db = SessionLocal()
inspector = inspect(engine)
columns = [c['name'] for c in inspector.get_columns('sm2_progress')]
if 'version' in columns:
    print('OK')
    exit(0)
else:
    exit(1)
" 2>/dev/null && \
    check_passed "Columna 'version' existe en sm2_progress" || \
    check_warning "Columna 'version' NO existe - ejecutar migración"

echo ""

# ============================================================================
# 10. VERIFICAR MIDDLEWARE
# ============================================================================
echo -e "${BLUE}🔒 Verificando middleware...${NC}"

if grep -q "from .middleware import setup_middleware" app/main.py; then
    check_passed "Middleware importado en main.py"
    
    if grep -q "setup_middleware(app, config)" app/main.py; then
        check_passed "setup_middleware() llamado"
    else
        check_failed "setup_middleware() NO llamado"
    fi
else
    check_failed "Middleware NO importado"
fi

echo ""

# ============================================================================
# RESUMEN FINAL
# ============================================================================
echo ""
echo "═══════════════════════════════════════════"
echo -e "${BLUE}📊 RESUMEN DE VERIFICACIÓN${NC}"
echo "═══════════════════════════════════════════"
echo ""
echo -e "${GREEN}✅ Checks pasados: $passed${NC}"
echo -e "${RED}❌ Checks fallidos: $failed${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ INSTALACIÓN VERIFICADA CON ÉXITO  ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}🚀 Puedes iniciar el servidor:${NC}"
    echo "   uvicorn app.main:app --reload"
    echo ""
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ⚠️  HAY PROBLEMAS EN LA INSTALACIÓN  ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}📋 Revisa los checks fallidos arriba${NC}"
    echo -e "${YELLOW}📖 Consulta INSTRUCCIONES_IMPLEMENTACION.md${NC}"
    echo ""
    exit 1
fi
