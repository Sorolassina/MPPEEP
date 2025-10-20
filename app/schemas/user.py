import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Schéma pour la création d'un utilisateur"""

    email: EmailStr = Field(..., description="Adresse email valide")
    full_name: str | None = Field(None, min_length=2, max_length=100, description="Nom complet")
    password: str = Field(..., min_length=6, description="Mot de passe (min 6 caractères)")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """
        Validateur personnalisé pour l'email
        - Vérifie le format
        - Convertit en minuscules
        - Rejette certains domaines (optionnel)
        """
        # Convertir en minuscules
        email = v.lower().strip()

        # Vérification supplémentaire du format
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, email):
            raise ValueError("Format d'email invalide")

        # Rejeter les domaines temporaires (optionnel)
        blocked_domains = ["tempmail.com", "throwaway.email", "10minutemail.com"]
        domain = email.split("@")[1]
        if domain in blocked_domains:
            raise ValueError(f"Le domaine {domain} n'est pas autorisé")

        return email

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None) -> str | None:
        """
        Validateur pour le nom complet
        - Nettoie les espaces multiples
        - Capitalise chaque mot
        """
        if v is None:
            return v

        # Nettoyer les espaces
        name = " ".join(v.split())

        # Vérifier qu'il n'y a pas que des chiffres
        if name.replace(" ", "").isdigit():
            raise ValueError("Le nom ne peut pas contenir que des chiffres")

        return name.title()  # Capitaliser chaque mot

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validateur pour le mot de passe
        - Minimum 6 caractères
        - Au moins une lettre
        - Au moins un chiffre (optionnel)
        """
        if len(v) < 6:
            raise ValueError("Le mot de passe doit contenir au moins 6 caractères")

        if not any(c.isalpha() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une lettre")

        # Règle optionnelle : au moins un chiffre
        # if not any(c.isdigit() for c in v):
        #     raise ValueError("Le mot de passe doit contenir au moins un chiffre")

        return v


class UserRead(BaseModel):
    """Schéma pour la lecture d'un utilisateur"""

    id: int
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    type_user: str

    class Config:
        from_attributes = True  # Permet la conversion depuis ORM


class UserUpdate(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur"""

    full_name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Validateur email pour mise à jour"""
        if v is None:
            return v
        return v.lower().strip()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None) -> str | None:
        """Validateur nom pour mise à jour"""
        if v is None:
            return v
        return " ".join(v.split()).title()
