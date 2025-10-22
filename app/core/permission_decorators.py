"""
Décorateurs de permission pour les endpoints
"""

from functools import wraps
from fastapi import HTTPException, Depends
from app.models.user import User
from app.core.permissions import PermissionManager


def require_permission(permission: str):
    """
    Décorateur pour vérifier qu'un utilisateur a une permission spécifique
    
    Args:
        permission: Permission requise (budget, rh, stocks, etc.)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Récupérer l'utilisateur courant
            current_user = None
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break
            
            # Chercher dans les kwargs
            if not current_user:
                current_user = kwargs.get('current_user')
            
            if not current_user:
                raise HTTPException(status_code=401, detail="Utilisateur non authentifié")
            
            # Vérifier la permission
            if not PermissionManager.has_permission(current_user.type_user, permission):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Permission '{permission}' requise. Type d'utilisateur: {current_user.type_user}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_module_access(module: str):
    """
    Décorateur pour vérifier qu'un utilisateur peut accéder à un module
    
    Args:
        module: Module requis (budget, rh, stocks, etc.)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Récupérer l'utilisateur courant
            current_user = None
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break
            
            # Chercher dans les kwargs
            if not current_user:
                current_user = kwargs.get('current_user')
            
            if not current_user:
                raise HTTPException(status_code=401, detail="Utilisateur non authentifié")
            
            # Vérifier l'accès au module
            if not PermissionManager.can_access_module(current_user.type_user, module):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Accès au module '{module}' refusé. Type d'utilisateur: {current_user.type_user}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_guest_mode():
    """
    Décorateur pour vérifier qu'un utilisateur est en mode invité
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Récupérer l'utilisateur courant
            current_user = None
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break
            
            # Chercher dans les kwargs
            if not current_user:
                current_user = kwargs.get('current_user')
            
            if not current_user:
                raise HTTPException(status_code=401, detail="Utilisateur non authentifié")
            
            # Vérifier que c'est un invité
            if not PermissionManager.is_guest(current_user.type_user):
                raise HTTPException(
                    status_code=403, 
                    detail="Accès réservé au mode démonstration"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_data_access():
    """
    Décorateur pour vérifier qu'un utilisateur peut voir les données réelles
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Récupérer l'utilisateur courant
            current_user = None
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break
            
            # Chercher dans les kwargs
            if not current_user:
                current_user = kwargs.get('current_user')
            
            if not current_user:
                raise HTTPException(status_code=401, detail="Utilisateur non authentifié")
            
            # Vérifier l'accès aux données
            if not PermissionManager.can_view_data(current_user.type_user):
                raise HTTPException(
                    status_code=403, 
                    detail="Accès aux données réelles refusé - Mode démonstration uniquement"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Fonctions utilitaires pour les dépendances FastAPI
def require_permission_dep(permission: str):
    """
    Dépendance FastAPI pour vérifier une permission
    
    Args:
        permission: Permission requise
        
    Returns:
        Fonction de dépendance FastAPI
    """
    def _dep(current_user: User) -> User:
        if not PermissionManager.has_permission(current_user.type_user, permission):
            raise HTTPException(
                status_code=403, 
                detail=f"Permission '{permission}' requise"
            )
        return current_user
    return _dep


def require_module_dep(module: str):
    """
    Dépendance FastAPI pour vérifier l'accès à un module
    
    Args:
        module: Module requis
        
    Returns:
        Fonction de dépendance FastAPI
    """
    def _dep(current_user: User) -> User:
        if not PermissionManager.can_access_module(current_user.type_user, module):
            raise HTTPException(
                status_code=403, 
                detail=f"Accès au module '{module}' refusé"
            )
        return current_user
    return _dep


def require_direction_dep():
    """
    Dépendance FastAPI pour vérifier qu'un utilisateur est d'une direction
    
    Returns:
        Fonction de dépendance FastAPI
    """
    def _dep(current_user: User) -> User:
        if not PermissionManager.is_direction(current_user.type_user):
            raise HTTPException(
                status_code=403, 
                detail="Accès réservé aux directions"
            )
        return current_user
    return _dep


def require_data_access_dep():
    """
    Dépendance FastAPI pour vérifier l'accès aux données réelles
    
    Returns:
        Fonction de dépendance FastAPI
    """
    def _dep(current_user: User) -> User:
        if not PermissionManager.can_view_data(current_user.type_user):
            raise HTTPException(
                status_code=403, 
                detail="Accès aux données réelles refusé - Mode démonstration uniquement"
            )
        return current_user
    return _dep
