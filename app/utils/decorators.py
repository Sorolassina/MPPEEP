"""
Décorateurs personnalisés pour l'application
"""
import functools
import logging
from time import time
from typing import Callable
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def log_execution_time(func: Callable) -> Callable:
    """
    Décorateur pour logger le temps d'exécution d'une fonction
    
    Example:
        @log_execution_time
        async def ma_fonction():
            # Code
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time()
        result = await func(*args, **kwargs)
        duration = time() - start
        logger.info(f"⏱️  {func.__name__} exécuté en {duration:.3f}s")
        return result
    return wrapper


def require_role(required_role: str):
    """
    Décorateur pour vérifier le rôle d'un utilisateur
    
    Args:
        required_role: Rôle requis (user, admin, superadmin)
    
    Example:
        @require_role("admin")
        async def admin_only_endpoint():
            # Accessible seulement aux admins
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # TODO: Récupérer l'utilisateur depuis la session
            # current_user = get_current_user()
            # if current_user.role != required_role:
            #     raise HTTPException(status_code=403, detail="Accès refusé")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def cache_result(expiry_seconds: int = 300):
    """
    Décorateur pour mettre en cache le résultat d'une fonction
    
    Args:
        expiry_seconds: Durée de validité du cache (secondes)
    
    Example:
        @cache_result(expiry_seconds=600)
        async def get_expensive_data():
            # Calcul coûteux
    """
    cache = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Créer une clé de cache
            cache_key = f"{func.__name__}_{args}_{kwargs}"
            
            # Vérifier si en cache et pas expiré
            if cache_key in cache:
                cached_time, cached_value = cache[cache_key]
                if time() - cached_time < expiry_seconds:
                    logger.debug(f"💾 Cache hit: {func.__name__}")
                    return cached_value
            
            # Exécuter et mettre en cache
            result = await func(*args, **kwargs)
            cache[cache_key] = (time(), result)
            
            return result
        return wrapper
    return decorator


def rate_limit(max_calls: int = 10, window_seconds: int = 60):
    """
    Décorateur pour limiter le taux d'appels (rate limiting)
    
    Args:
        max_calls: Nombre maximum d'appels
        window_seconds: Fenêtre de temps (secondes)
    
    Example:
        @rate_limit(max_calls=5, window_seconds=60)
        async def sensitive_endpoint():
            # Max 5 appels par minute
    """
    calls = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Identifier le client (IP)
            from app.utils.helpers import get_client_ip
            client_id = get_client_ip(request)
            
            # Nettoyer les anciennes entrées
            current_time = time()
            if client_id in calls:
                calls[client_id] = [
                    call_time for call_time in calls[client_id]
                    if current_time - call_time < window_seconds
                ]
            else:
                calls[client_id] = []
            
            # Vérifier la limite
            if len(calls[client_id]) >= max_calls:
                raise HTTPException(
                    status_code=429,
                    detail=f"Trop de requêtes. Réessayez dans {window_seconds} secondes."
                )
            
            # Enregistrer l'appel
            calls[client_id].append(current_time)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def retry(max_attempts: int = 3, delay_seconds: int = 1):
    """
    Décorateur pour réessayer une fonction en cas d'échec
    
    Args:
        max_attempts: Nombre maximum de tentatives
        delay_seconds: Délai entre les tentatives
    
    Example:
        @retry(max_attempts=3, delay_seconds=2)
        async def unstable_api_call():
            # Appel qui peut échouer
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"❌ {func.__name__} échoué après {max_attempts} tentatives")
                        raise
                    
                    logger.warning(f"⚠️  {func.__name__} échec tentative {attempt + 1}/{max_attempts}: {e}")
                    await asyncio.sleep(delay_seconds)
        
        return wrapper
    return decorator

