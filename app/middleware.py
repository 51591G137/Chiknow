"""
Middleware para rate limiting y seguridad
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import logging
import time
import uuid

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting por IP
    
    Limita el número de requests por minuto por IP
    """
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
        logger.info(f"Rate limiting configurado: {requests_per_minute} req/min")
    
    async def dispatch(self, request: Request, call_next):
        # Obtener IP del cliente
        client_ip = request.client.host if request.client else "unknown"
        
        # Paths excluidos del rate limiting
        excluded_paths = ["/health", "/docs", "/openapi.json"]
        if request.url.path in excluded_paths:
            return await call_next(request)
        
        # Limpiar requests antiguos (> 1 minuto)
        now = datetime.now()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < timedelta(minutes=1)
        ]
        
        # Verificar límite
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            logger.warning(
                f"Rate limit excedido para IP {client_ip}",
                extra={
                    "client_ip": client_ip,
                    "requests_count": len(self.requests[client_ip]),
                    "limit": self.requests_per_minute
                }
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "TooManyRequests",
                    "detail": f"Límite de {self.requests_per_minute} requests por minuto excedido",
                    "retry_after": 60
                }
            )
        
        # Registrar request
        self.requests[client_ip].append(now)
        
        # Agregar header con info de rate limit
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.requests[client_ip])
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Agrega headers de seguridad a todas las respuestas
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Headers de seguridad estándar
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS (solo en HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # CSP básico
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logging detallado de todas las requests
    """
    async def dispatch(self, request: Request, call_next):
        # Generar request ID único
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Inicio de request
        start_time = time.time()
        
        logger.info(
            f"Request iniciada: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        
        # Procesar request
        try:
            response = await call_next(request)
            
            # Calcular tiempo de procesamiento
            process_time = time.time() - start_time
            
            # Agregar headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            # Log de respuesta
            logger.info(
                f"Request completada: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "process_time_ms": process_time * 1000
                }
            )
            
            return response
            
        except Exception as e:
            # Log de error
            process_time = time.time() - start_time
            logger.error(
                f"Request fallida: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "process_time": process_time
                },
                exc_info=True
            )
            raise


class CORSCustomMiddleware(BaseHTTPMiddleware):
    """
    CORS personalizado con logging
    (Alternativa a CORSMiddleware de FastAPI)
    """
    def __init__(self, app, allowed_origins: list = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
        logger.info(f"CORS configurado para: {self.allowed_origins}")
    
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        
        # Preflight request
        if request.method == "OPTIONS":
            response = JSONResponse(content={}, status_code=200)
        else:
            response = await call_next(request)
        
        # Agregar headers CORS
        if origin:
            if "*" in self.allowed_origins or origin in self.allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "*"
            else:
                logger.warning(f"Origin no permitido: {origin}")
        
        return response


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Compresión de respuestas grandes
    (Requiere: pip install python-multipart)
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Solo comprimir respuestas grandes
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > 1024:  # > 1KB
            # Verificar si el cliente acepta gzip
            accept_encoding = request.headers.get("accept-encoding", "")
            if "gzip" in accept_encoding:
                response.headers["Content-Encoding"] = "gzip"
                logger.debug(f"Respuesta comprimida: {content_length} bytes")
        
        return response


# Helper para agregar todos los middleware
def setup_middleware(app, config):
    """
    Configura todos los middleware en el orden correcto
    
    Args:
        app: FastAPI app
        config: Config object
    """
    # Orden importante: más específico primero
    
    # 1. Request logging (primero para capturar todo)
    app.add_middleware(RequestLoggingMiddleware)
    
    # 2. Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 3. Rate limiting
    rate_limit = getattr(config, 'RATE_LIMIT_PER_MINUTE', 100)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit)
    
    # 4. CORS (si se usa personalizado)
    # allowed_origins = getattr(config, 'ALLOWED_ORIGINS', ["*"])
    # app.add_middleware(CORSCustomMiddleware, allowed_origins=allowed_origins)
    
    # 5. Compression (último para comprimir todo)
    # app.add_middleware(CompressionMiddleware)
    
    logger.info("✅ Middleware configurado correctamente")
