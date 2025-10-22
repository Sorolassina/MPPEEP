"""
Système de gestion des autorisations utilisateur
Gère les permissions selon le type d'utilisateur et l'héritage hiérarchique
"""

from typing import List, Set
from app.core.enums import UserType


class PermissionManager:
    """Gestionnaire des permissions utilisateur"""
    
    # Définition des permissions par type d'utilisateur
    PERMISSIONS_BY_TYPE = {
        UserType.ADMIN: {
            "budget", "performance", "rh", "stocks", "personnel", 
            "admin", "referentiels", "workflows", "system_settings"
        },
        UserType.DAF: {
            "budget", "performance", "rh", "stocks", "personnel", 
            "referentiels", "workflows"
        },
        UserType.SDB: {
            "budget", "performance"
        },
        UserType.SDRH: {
            "rh", "personnel"
        },
        UserType.SDCMG: {
            "stocks"
        },
        UserType.CS: {
            "rh", "personnel"  # Chef de service - permissions RH
        },
        UserType.AGENT: {
            "rh"  # Peut faire des demandes RH
        },
        UserType.INVITE: {
            "view_structure", "view_interface", "demo_mode"  # Peut voir la structure mais pas les données
        }
    }
    
    # Hiérarchie des responsables (qui hérite de qui)
    HIERARCHY = {
        UserType.CS: UserType.SDRH,  # Chef de service hérite des permissions SDRH
        UserType.AGENT: UserType.CS,  # Agent hérite des permissions CS
    }
    
    @classmethod
    def get_user_permissions(cls, user_type: str) -> Set[str]:
        """
        Récupère les permissions d'un utilisateur selon son type
        
        Args:
            user_type: Type d'utilisateur (string)
            
        Returns:
            Set des permissions accordées
        """
        try:
            user_enum = UserType(user_type)
        except ValueError:
            # Type inconnu, retourner permissions minimales
            return {"rh"}
        
        # Permissions directes du type
        direct_permissions = cls.PERMISSIONS_BY_TYPE.get(user_enum, set())
        
        # Vérifier s'il y a un héritage hiérarchique
        inherited_permissions = set()
        if user_enum in cls.HIERARCHY:
            parent_type = cls.HIERARCHY[user_enum]
            inherited_permissions = cls.PERMISSIONS_BY_TYPE.get(parent_type, set())
        
        # Combiner les permissions directes et héritées
        all_permissions = direct_permissions | inherited_permissions
        
        return all_permissions
    
    @classmethod
    def has_permission(cls, user_type: str, permission: str) -> bool:
        """
        Vérifie si un utilisateur a une permission spécifique
        
        Args:
            user_type: Type d'utilisateur
            permission: Permission à vérifier
            
        Returns:
            True si l'utilisateur a la permission
        """
        user_permissions = cls.get_user_permissions(user_type)
        return permission in user_permissions
    
    @classmethod
    def can_access_module(cls, user_type: str, module: str) -> bool:
        """
        Vérifie si un utilisateur peut accéder à un module
        
        Args:
            user_type: Type d'utilisateur
            module: Module à vérifier (budget, rh, stocks, etc.)
            
        Returns:
            True si l'utilisateur peut accéder au module
        """
        return cls.has_permission(user_type, module)
    
    @classmethod
    def get_accessible_modules(cls, user_type: str) -> List[str]:
        """
        Récupère la liste des modules accessibles pour un utilisateur
        
        Args:
            user_type: Type d'utilisateur
            
        Returns:
            Liste des modules accessibles
        """
        permissions = cls.get_user_permissions(user_type)
        return sorted(list(permissions))
    
    @classmethod
    def is_admin(cls, user_type: str) -> bool:
        """Vérifie si l'utilisateur est admin"""
        return user_type == UserType.ADMIN.value
    
    @classmethod
    def is_direction(cls, user_type: str) -> bool:
        """Vérifie si l'utilisateur est d'une direction"""
        direction_types = {UserType.DAF, UserType.SDB, UserType.SDRH, UserType.SDCMG}
        try:
            user_enum = UserType(user_type)
            return user_enum in direction_types
        except ValueError:
            return False
    
    @classmethod
    def is_guest(cls, user_type: str) -> bool:
        """Vérifie si l'utilisateur est un invité (mode MVP)"""
        return user_type == UserType.INVITE.value
    
    @classmethod
    def can_view_data(cls, user_type: str) -> bool:
        """Vérifie si l'utilisateur peut voir les données réelles"""
        return not cls.is_guest(user_type)
    
    @classmethod
    def can_perform_crud(cls, user_type: str) -> bool:
        """Vérifie si l'utilisateur peut effectuer des opérations CRUD"""
        return not cls.is_guest(user_type)
    
    @classmethod
    def get_user_type_display_name(cls, user_type: str) -> str:
        """
        Récupère le nom d'affichage d'un type d'utilisateur
        
        Args:
            user_type: Type d'utilisateur
            
        Returns:
            Nom d'affichage
        """
        display_names = {
            UserType.ADMIN.value: "Administrateur",
            UserType.DAF.value: "Direction Administrative et Financière",
            UserType.SDB.value: "Sous-Direction Budget",
            UserType.SDRH.value: "Sous-Direction des Ressources Humaines",
            UserType.SDCMG.value: "Sous-Direction Commerciale et Marketing",
            UserType.CS.value: "Chef de Service",
            UserType.AGENT.value: "Agent",
            UserType.INVITE.value: "Invité",
        }
        
        return display_names.get(user_type, "Type inconnu")


# Fonctions utilitaires pour les templates
def user_can_access(user_type: str, module: str) -> bool:
    """Fonction utilitaire pour les templates"""
    return PermissionManager.can_access_module(user_type, module)


def user_is_admin(user_type: str) -> bool:
    """Fonction utilitaire pour les templates"""
    return PermissionManager.is_admin(user_type)


def user_is_direction(user_type: str) -> bool:
    """Fonction utilitaire pour les templates"""
    return PermissionManager.is_direction(user_type)
