"""
Middlewares de sécurité et de performance pour l'application

Un middleware est comme un filtre qui traite toutes les requêtes entrantes et sortantes.
"""

import logging
import time
import uuid

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import settings

logger = logging.getLogger(__name__)

# IPs bloquées (liste noire)
BLOCKED_IPS = []  # Ajoutez ici les IPs à bloquer

# User agents bloqués (bots malveillants)
BLOCKED_USER_AGENTS = ["bot", "crawler", "scraper", "spider", "crawling", "scraping"]

# Taille maximale des requêtes (10MB)
MAX_REQUEST_SIZE = 10 * 1024 * 1024


def build_allowed_origins(allowed_hosts: list[str], cors_allow_all: bool = False) -> list[str]:
    """
    Construit la liste des origines autorisées pour CORS

    Args:
        allowed_hosts: Liste des hôtes autorisés
        cors_allow_all: Si True, autorise toutes les origines

    Returns:
        Liste des origines (avec http:// et https://)
    """
    if cors_allow_all:
        return ["*"]

    origins = []
    for host in allowed_hosts:
        if host.startswith("http://") or host.startswith("https://"):
            origins.append(host)
        else:
            origins.append(f"http://{host}")
            origins.append(f"https://{host}")

    return origins


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Ajoute des en-têtes de sécurité à toutes les réponses

    Protection contre :
    - Clickjacking (X-Frame-Options)
    - MIME sniffing (X-Content-Type-Options)
    - Fuite d'informations (Referrer-Policy)
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # En-têtes de sécurité de base
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS en production (force HTTPS)
        if hasattr(request.app.state, "settings") and not request.app.state.settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response


class CSPMiddleware(BaseHTTPMiddleware):
    """
    Ajoute une politique de sécurité du contenu (CSP)

    Protection contre :
    - Injection de scripts (XSS)
    - Chargement de ressources non autorisées
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Politique de sécurité du contenu
        csp_policy = (
            "default-src 'self'; "
            # iframes (Power BI)
            "frame-src 'self' https://app.powerbi.com https://*.powerbi.com; "
            "child-src 'self' https://app.powerbi.com https://*.powerbi.com; "
            # qui peut vous embarquer (ok pour votre site)
            "frame-ancestors 'self'; "
            # JS / CSS (tu as du inline → on garde provisoirement 'unsafe-inline')
            "script-src 'self' 'unsafe-inline' cdn.tailwindcss.com cdnjs.cloudflare.com cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' fonts.googleapis.com cdnjs.cloudflare.com; "
            # Fonts / images
            "font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com; "
            "img-src 'self' data: blob: https:; "
            # Réseaux (ajoute *.powerbi.com si tu passes au SDK powerbi-client)
            "connect-src 'self' cdn.jsdelivr.net; "
            # Divers durcissements
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        response.headers["Content-Security-Policy"] = csp_policy
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Enregistre toutes les requêtes HTTP dans les logs

    Logs vers :
    - Console (stdout/stderr selon niveau)
    - logs/app.log (tous les logs)
    - logs/access.log (requêtes HTTP)
    - logs/error.log (erreurs seulement)
    """

    async def dispatch(self, request: Request, call_next):
        from app.core.logging_config import access_logger, get_logger

        logger = get_logger("mppeep.middleware")
        start_time = time.time()

        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        url = str(request.url.path)
        user_agent = request.headers.get("user-agent", "unknown")
        request_id = request.headers.get("X-Request-ID", "no-id")

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            status_code = response.status_code

            # Log dans app.log
            log_message = (
                f"{client_ip} | {method} {url} | "
                f"Status: {status_code} | Duration: {duration:.3f}s | "
                f"Request-ID: {request_id}"
            )

            if status_code >= 500:
                logger.error(f"❌ {log_message}")
            elif status_code >= 400:
                logger.warning(f"⚠️  {log_message}")
            else:
                logger.info(f"✅ {log_message}")

            # Log dans access.log (format Apache-like)
            access_logger.info(f'{client_ip} - "{method} {url}" {status_code} {duration:.3f}s "{user_agent}"')

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_message = (
                f"{client_ip} | {method} {url} | "
                f"ERROR | Duration: {duration:.3f}s | "
                f"Request-ID: {request_id} | Error: {str(e)[:200]}"
            )

            logger.error(f"❌ {error_message}", exc_info=True)

            # Log aussi dans access.log
            access_logger.error(f'{client_ip} - "{method} {url}" 500 {duration:.3f}s "ERROR: {str(e)[:100]}"')

            raise


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Ajoute un identifiant unique à chaque requête

    Utile pour tracer une requête dans les logs
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """
    Gère le cache des fichiers statiques et des réponses API

    - Fichiers statiques : Cache long (1 an)
    - API : Pas de cache
    - Pages HTML : Cache modéré (1 heure)
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Cache pour les fichiers statiques (1 an)
        root_path = settings.get_root_path
        static_prefix = f"{root_path}/static" if root_path else "/static"
        uploads_prefix = f"{root_path}/uploads" if root_path else "/uploads"
        api_prefix = f"{root_path}/api" if root_path else "/api"
        
        if request.url.path.startswith(static_prefix) or request.url.path.startswith(uploads_prefix):
            response.headers["Cache-Control"] = "public, max-age=31536000"
        # Pas de cache pour les API
        elif request.url.path.startswith(api_prefix):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        # Cache modéré pour les pages HTML (1 heure)
        else:
            response.headers["Cache-Control"] = "public, max-age=3600"

        return response


class IPFilterMiddleware(BaseHTTPMiddleware):
    """
    Bloque les adresses IP malveillantes

    Protection contre :
    - Attaques répétées
    - IPs connues comme malveillantes
    """

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        if client_ip in BLOCKED_IPS:
            logger.warning(f"🚫 IP bloquée : {client_ip}")
            return JSONResponse(status_code=403, content={"detail": "Accès refusé - IP bloquée"})

        return await call_next(request)


class UserAgentFilterMiddleware(BaseHTTPMiddleware):
    """
    Bloque les robots malveillants et les scrapers

    Protection contre :
    - Scraping de données
    - Bots automatiques
    """

    async def dispatch(self, request: Request, call_next):
        user_agent = request.headers.get("user-agent", "").lower()

        if any(blocked in user_agent for blocked in BLOCKED_USER_AGENTS):
            logger.warning(f"🤖 User agent bloqué : {user_agent[:100]}")
            return JSONResponse(status_code=403, content={"detail": "Accès refusé - Robot détecté"})

        return await call_next(request)


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Limite la taille des requêtes

    Protection contre :
    - Attaques par déni de service (DoS)
    - Upload de fichiers trop gros
    """

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")

            if content_length:
                try:
                    size = int(content_length)
                    if size > MAX_REQUEST_SIZE:
                        logger.warning(f"📏 Requête trop volumineuse : {size} bytes")
                        return JSONResponse(
                            status_code=413,
                            content={
                                "detail": f"Requête trop volumineuse - Maximum {MAX_REQUEST_SIZE // (1024 * 1024)}MB"
                            },
                        )
                except ValueError:
                    pass

        return await call_next(request)


class ForwardProtoMiddleware(BaseHTTPMiddleware):
    """
    Forwards the protocol to the request
    """

    async def dispatch(self, request: Request, call_next):
        proto = request.headers.get("X-Forwarded-Proto", "https")
        if proto:
            request.scope["scheme"] = proto
        return await call_next(request)


class CloudflareMiddleware(BaseHTTPMiddleware):
    """
    Capture et enrichit les requêtes avec les informations Cloudflare

    Headers Cloudflare capturés :
    - CF-Connecting-IP : IP réelle du client
    - CF-Ray : ID unique de la requête Cloudflare
    - CF-IPCountry : Code pays du client (ISO 3166-1 alpha-2)
    - CF-Visitor : Protocole utilisé (http/https)

    Les informations sont stockées dans request.state pour y accéder partout :
    - request.state.cf_ray
    - request.state.cf_country
    - request.state.client_ip
    """

    async def dispatch(self, request: Request, call_next):
        # Capturer les headers Cloudflare
        cf_ray = request.headers.get("CF-Ray", "")
        cf_country = request.headers.get("CF-IPCountry", "")
        cf_connecting_ip = request.headers.get("CF-Connecting-IP", "")
        cf_visitor = request.headers.get("CF-Visitor", "")

        # Stocker dans request.state pour y accéder dans les endpoints
        request.state.cf_ray = cf_ray
        request.state.cf_country = cf_country
        request.state.cf_connecting_ip = cf_connecting_ip
        request.state.cf_visitor = cf_visitor

        # Log pour le monitoring (optionnel, peut être désactivé en prod)
        if cf_ray:
            logger.debug(f"☁️  Cloudflare Ray: {cf_ray} | Country: {cf_country} | IP: {cf_connecting_ip}")

        return await call_next(request)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Gère les erreurs non gérées de manière élégante

    Avantages :
    - Messages d'erreur clairs pour l'utilisateur
    - Logs détaillés pour les développeurs
    - Pas d'exposition de détails techniques
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)

        except Exception as e:
            logger.error(f"💥 Erreur non gérée : {e!s}", exc_info=True)

            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Erreur interne du serveur",
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
            )


def setup_middlewares(app, settings):
    """
    Configure tous les middlewares pour l'application

    L'ordre est important : le premier ajouté s'exécute en dernier !

    Args:
        app: Instance FastAPI
        settings: Paramètres de configuration
    """

    # Stocker settings dans l'état de l'app
    app.state.settings = settings

    # ==========================================
    # MIDDLEWARES DANS L'ORDRE D'EXÉCUTION
    # ==========================================

    # 1. Redirection HTTPS en production
    if settings.should_enable_https_redirect:
        app.add_middleware(HTTPSRedirectMiddleware)
        logger.info("🔒 HTTPS Redirect activé")

    # 2. Trusted Hosts
    if not settings.DEBUG:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
        logger.info(f"✅ Trusted Hosts : {settings.ALLOWED_HOSTS}")
    else:
        # Dev : accepter tous les hôtes
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

    # 3. CORS - Cross-Origin Resource Sharing
    if settings.ENABLE_CORS:
        origins = build_allowed_origins(settings.ALLOWED_HOSTS, settings.CORS_ALLOW_ALL)

        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(f"🌐 CORS configuré : {origins}")

    # 4. Gestion des erreurs
    if settings.ENABLE_ERROR_HANDLING:
        app.add_middleware(ErrorHandlingMiddleware)
        logger.info("💥 Error Handling activé")

    # 5. Limitation de taille des requêtes
    if settings.ENABLE_REQUEST_SIZE_LIMIT:
        app.add_middleware(RequestSizeMiddleware)
        logger.info(f"📏 Request Size Limit : {MAX_REQUEST_SIZE // (1024 * 1024)}MB")

    # 6. Filtrage des IPs
    if settings.ENABLE_IP_FILTER and BLOCKED_IPS:
        app.add_middleware(IPFilterMiddleware)
        logger.info(f"🚫 IP Filter activé ({len(BLOCKED_IPS)} IPs bloquées)")

    # 7. Filtrage des user agents
    if settings.ENABLE_USER_AGENT_FILTER:
        app.add_middleware(UserAgentFilterMiddleware)
        logger.info("🤖 User Agent Filter activé")

    # 8. Logging des requêtes
    if settings.ENABLE_LOGGING:
        app.add_middleware(LoggingMiddleware)
        logger.info("📝 Request Logging activé")

    # 9. ID de requête
    if settings.ENABLE_REQUEST_ID:
        app.add_middleware(RequestIDMiddleware)
        logger.info("🎫 Request ID activé")

    # 10. Compression GZip
    if settings.should_enable_gzip:
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        logger.info("📦 GZip activé")

    # 11. Contrôle du cache
    if settings.should_enable_cache_control:
        app.add_middleware(CacheControlMiddleware)
        logger.info("💾 Cache Control activé")

    # 12. En-têtes de sécurité
    if settings.should_enable_security_headers:
        app.add_middleware(SecurityHeadersMiddleware)
        logger.info("🔒 Security Headers activés")

    # 13. Politique de sécurité du contenu (CSP)
    if settings.should_enable_csp:
        app.add_middleware(CSPMiddleware)
        logger.info("🛡️ CSP activé")

    # 14. Forward Proto (derrière proxy/Cloudflare)
    if settings.should_enable_forward_proto:
        app.add_middleware(ForwardProtoMiddleware)
        logger.info("🔗 Forward Proto activé")

    # 15. Cloudflare (capture des headers CF-*)
    if settings.should_enable_cloudflare:
        app.add_middleware(CloudflareMiddleware)
        logger.info("☁️  Cloudflare Middleware activé")

    logger.info("✅ Configuration middlewares terminée")
