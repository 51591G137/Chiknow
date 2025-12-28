# Chiknow - Sistema de Aprendizaje de Chino HSK

Sistema de repaso espaciado (SM2) para aprendizaje de vocabulario chino.

## 🚀 Quick Start

\`\`\`bash
# Instalar
pip install -r requirements.txt

# Configurar
cp .env.example .env
# Editar .env con tus credenciales

# Inicializar
python scripts/setup/inicializar.py --completo

# Ejecutar
uvicorn app.main:app --reload
\`\`\`

## 📚 Documentación

- [Instalación](docs/SETUP.md)
- [Base de Datos](docs/DATABASE.md)
- [API](docs/API.md)
- [Deploy](docs/DEPLOY.md)

## 📂 Estructura del Proyecto

\`\`\`
app/          - Aplicación principal
data/         - Datos y BD local
scripts/      - Scripts de gestión
templates/    - Templates HTML
static/       - Archivos estáticos
docs/         - Documentación
\`\`\`

[... resto ...]