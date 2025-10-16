#!/usr/bin/env python3
"""
Script pour initialiser les catégories d'articles de stock
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import engine, get_session
from sqlmodel import SQLModel, select
from app.models.stock import CategorieArticle, Fournisseur

def init_categories():
    """Créer les catégories par défaut"""
    
    # Créer les tables si nécessaire
    SQLModel.metadata.create_all(engine)
    
    session = next(get_session())
    
    # Catégories par défaut
    categories_default = [
        {"code": "FOUR", "libelle": "Fournitures de Bureau", "description": "Papier, stylos, classeurs, etc."},
        {"code": "INFO", "libelle": "Matériel Informatique", "description": "Ordinateurs, imprimantes, accessoires IT"},
        {"code": "MOBI", "libelle": "Mobilier", "description": "Bureaux, chaises, armoires, etc."},
        {"code": "CONS", "libelle": "Consommables", "description": "Cartouches, toners, produits d'entretien"},
        {"code": "ELEC", "libelle": "Électronique", "description": "Téléphones, tablettes, équipements électroniques"},
        {"code": "ENTRE", "libelle": "Entretien", "description": "Produits de nettoyage et maintenance"},
        {"code": "AUTRE", "libelle": "Autres", "description": "Articles divers"}
    ]
    
    for cat_data in categories_default:
        # Vérifier si existe déjà
        existing = session.exec(
            select(CategorieArticle).where(CategorieArticle.code == cat_data["code"])
        ).first()
        if not existing:
            cat = CategorieArticle(**cat_data)
            session.add(cat)
            print(f"✅ Catégorie créée : {cat_data['libelle']}")
        else:
            print(f"ℹ️  Catégorie existe déjà : {cat_data['libelle']}")
    
    session.commit()
    print("\n✅ Initialisation des catégories terminée !")
    
    # Afficher le résultat
    total = session.exec(select(CategorieArticle)).all()
    print(f"📊 Total catégories : {len(total)}")


def init_fournisseurs_exemple():
    """Créer des fournisseurs d'exemple (optionnel)"""
    
    session = next(get_session())
    
    fournisseurs_exemple = [
        {
            "code": "F001",
            "nom": "Papeterie Centrale",
            "telephone": "+221 33 123 45 67",
            "email": "contact@papeterie-centrale.sn",
            "adresse": "Dakar, Sénégal"
        },
        {
            "code": "F002",
            "nom": "Informatique Pro",
            "telephone": "+221 33 987 65 43",
            "email": "info@informatique-pro.sn",
            "adresse": "Dakar, Sénégal"
        }
    ]
    
    for f_data in fournisseurs_exemple:
        existing = session.exec(
            select(Fournisseur).where(Fournisseur.code == f_data["code"])
        ).first()
        if not existing:
            f = Fournisseur(**f_data)
            session.add(f)
            print(f"✅ Fournisseur créé : {f_data['nom']}")
        else:
            print(f"ℹ️  Fournisseur existe déjà : {f_data['nom']}")
    
    session.commit()
    print("\n✅ Initialisation des fournisseurs terminée !")


if __name__ == "__main__":
    print("🚀 Initialisation du système de gestion des stocks\n")
    print("=" * 60)
    
    init_categories()
    print("\n" + "=" * 60)
    
    # Décommenter si vous voulez aussi créer des fournisseurs d'exemple
    # init_fournisseurs_exemple()
    
    print("\n✅ Initialisation terminée avec succès !")

