#!/usr/bin/env python3
"""
Punto de entrada para ejecutar localmente
"""
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    print(f"🚀 Iniciando Chiknow en puerto {port}...")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )