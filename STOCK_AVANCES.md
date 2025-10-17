# 📦 Fonctionnalités Avancées du Module Stock

## 🎯 Vue d'ensemble

Le module de gestion des stocks a été enrichi avec **deux nouvelles fonctionnalités majeures** :

1. **📅 Gestion des articles périssables** - Suivi des lots, dates de péremption, alertes
2. **💰 Amortissement du matériel** - Calcul comptable de la dépréciation

---

## 📅 1. GESTION DES ARTICLES PÉRISSABLES

### Concept

Permet de gérer les articles avec une **date de péremption** (denrées alimentaires, médicaments, produits chimiques, etc.) en assurant :
- ✅ Suivi des lots avec dates de péremption
- ✅ Alertes avant péremption
- ✅ Gestion FIFO (First In, First Out)
- ✅ Détection automatique des produits périmés

### Configuration d'un article périssable

```python
article = Article(
    code="ALI-001",
    designation="Riz long grain",
    est_perissable=True,  # ⬅️ Activer la gestion périssable
    duree_conservation_jours=365,  # Durée de conservation standard
    seuil_alerte_peremption_jours=30,  # Alerte 30 jours avant péremption
    # ... autres champs
)
```

### Création d'un lot périssable

À chaque réception d'un article périssable, créer un lot :

```python
from app.services.stock_service import StockService

lot = StockService.creer_lot_perissable(
    session=db_session,
    article_id=1,
    numero_lot="LOT-2025-001",  # N° de lot fournisseur
    date_peremption=date(2025, 12, 31),
    quantite=Decimal("100"),
    fournisseur_id=2,
    date_fabrication=date(2025, 1, 15),
    observations="Lot reçu en bon état"
)
```

### Consommation avec gestion FIFO

Lors d'une sortie, les lots qui périment en premier sont utilisés automatiquement :

```python
# Sortie de 150 unités - consomme automatiquement les lots par ordre de péremption
lots_consommes = StockService.consommer_lot_fifo(
    session=db_session,
    article_id=1,
    quantite=Decimal("150")
)

# Résultat: 
# [
#   {"lot_id": 1, "numero_lot": "LOT-2025-001", "quantite_consommee": 100, "date_peremption": "2025-06-30"},
#   {"lot_id": 2, "numero_lot": "LOT-2025-002", "quantite_consommee": 50, "date_peremption": "2025-12-31"}
# ]
```

### Alertes et rapports

#### Lots à périmer prochainement

```python
# Lots qui périment dans les 30 prochains jours
lots_alerte = StockService.get_lots_a_perimer(session=db_session, jours=30)

# Résultat:
# [
#   {
#     "lot": <LotPerissable>,
#     "article": <Article>,
#     "jours_restants": 15,
#     "urgence": "ELEVEE"  # CRITIQUE (<7j), ELEVEE (<15j), MOYENNE
#   }
# ]
```

#### Lots périmés

```python
# Lots déjà périmés avec stock restant
lots_perimes = StockService.get_lots_perimes(session=db_session)
```

#### Mise à jour quotidienne des statuts

```python
# À exécuter quotidiennement (tâche planifiée)
stats = StockService.mettre_a_jour_statuts_lots(session=db_session)
# Retourne: {"actifs": 150, "alertes": 25, "perimes": 3, "epuises": 42}
```

### Statuts des lots

| Statut | Description |
|--------|-------------|
| `ACTIF` | Lot disponible, pas d'alerte |
| `ALERTE` | Lot approchant de la date de péremption (selon seuil) |
| `PERIME` | Lot périmé |
| `EPUISE` | Lot entièrement consommé |

---

## 💰 2. AMORTISSEMENT DU MATÉRIEL

### Concept

Permet de **calculer la dépréciation comptable** des immobilisations (équipements, véhicules, mobilier, informatique) selon les normes comptables :
- ✅ Méthode linéaire
- ✅ Méthode dégressive
- ✅ Calcul de la Valeur Nette Comptable (VNC)
- ✅ Plan d'amortissement automatique
- ✅ Suivi annuel

### Configuration d'un matériel amortissable

```python
article = Article(
    code="MAT-001",
    designation="Ordinateur portable Dell",
    est_amortissable=True,  # ⬅️ Activer l'amortissement
    date_acquisition=date(2023, 1, 15),
    valeur_acquisition=Decimal("1500000"),  # Prix d'achat en FCFA
    duree_amortissement_annees=3,  # 3 ans
    taux_amortissement=Decimal("33.33"),  # Pour méthode linéaire
    valeur_residuelle=Decimal("150000"),  # Valeur finale après amortissement
    methode_amortissement="LINEAIRE",  # ou "DEGRESSIF"
    # ... autres champs
)
```

### Méthodes d'amortissement

#### 1️⃣ Méthode Linéaire

**Formule** : `Amortissement annuel = (Valeur acquisition - Valeur résiduelle) / Durée`

**Exemple** :
- Valeur acquisition : 1 500 000 FCFA
- Durée : 3 ans
- Valeur résiduelle : 150 000 FCFA
- **Amortissement annuel** : (1 500 000 - 150 000) / 3 = **450 000 FCFA/an**

```python
article.methode_amortissement = "LINEAIRE"
article.duree_amortissement_annees = 3
```

#### 2️⃣ Méthode Dégressive

**Formule** : `Amortissement annuel = VNC début période × Taux dégressif`

**Taux dégressif** = Taux linéaire × Coefficient
- Durée 3-4 ans : coefficient 1.25
- Durée 5-6 ans : coefficient 1.75
- Durée > 6 ans : coefficient 2.25

**Exemple** :
- Valeur acquisition : 2 000 000 FCFA
- Durée : 5 ans
- Taux linéaire : 100/5 = 20%
- **Taux dégressif** : 20% × 1.75 = **35%**

```python
article.methode_amortissement = "DEGRESSIF"
article.taux_amortissement = Decimal("35")  # 35%
```

### Calcul annuel de l'amortissement

```python
from app.services.stock_service import StockService

# Calculer l'amortissement pour l'année 2025
amortissement = StockService.calculer_amortissement_annee(
    session=db_session,
    article_id=1,
    annee=2025,
    user_id=current_user.id
)

# Résultat stocké en base de données :
# - Valeur brute
# - Amortissement cumulé début
# - Amortissement de la période
# - Amortissement cumulé fin
# - Valeur Nette Comptable (VNC)
```

### Plan d'amortissement complet

```python
# Génère le plan complet sur toute la durée
plan = StockService.get_plan_amortissement(session=db_session, article_id=1)

# Résultat:
# [
#   {
#     "annee": 2023,
#     "valeur_brute": 1500000,
#     "amortissement_periode": 450000,
#     "amortissement_cumule": 450000,
#     "valeur_nette_comptable": 1050000,
#     "statut": "CALCULE",
#     "calcule": True
#   },
#   {
#     "annee": 2024,
#     "valeur_brute": 1500000,
#     "amortissement_periode": 450000,
#     "amortissement_cumule": 900000,
#     "valeur_nette_comptable": 600000,
#     "statut": "PROJETE",  # ⬅️ Pas encore calculé
#     "calcule": False
#   },
#   # ... années suivantes
# ]
```

### Matériels à amortir

```python
# Liste des matériels nécessitant un calcul d'amortissement pour 2025
materiels = StockService.get_materiels_a_amortir(session=db_session, annee=2025)

# Résultat:
# [
#   {
#     "article": <Article>,
#     "annee": 2025,
#     "annees_depuis_acquisition": 2
#   }
# ]
```

### Exemple complet : Tableau d'amortissement

**Matériel** : Véhicule de service  
**Valeur acquisition** : 10 000 000 FCFA  
**Durée** : 5 ans  
**Méthode** : Linéaire  
**Valeur résiduelle** : 1 000 000 FCFA

| Année | Valeur brute | Amort. annuel | Amort. cumulé | VNC |
|-------|--------------|---------------|---------------|-----|
| 2023 | 10 000 000 | 1 800 000 | 1 800 000 | 8 200 000 |
| 2024 | 10 000 000 | 1 800 000 | 3 600 000 | 6 400 000 |
| 2025 | 10 000 000 | 1 800 000 | 5 400 000 | 4 600 000 |
| 2026 | 10 000 000 | 1 800 000 | 7 200 000 | 2 800 000 |
| 2027 | 10 000 000 | 1 800 000 | 9 000 000 | 1 000 000 ✅ |

---

## 🔄 Intégration avec les mouvements de stock

### Articles périssables

Lors d'un mouvement **ENTREE** pour un article périssable :
1. Créer un lot avec la date de péremption
2. Le stock de l'article est augmenté
3. Le lot est automatiquement géré en FIFO lors des sorties

Lors d'un mouvement **SORTIE** :
1. La méthode `consommer_lot_fifo()` est appelée automatiquement
2. Les lots sont consommés par ordre de péremption
3. Les quantités restantes sont mises à jour

### Matériels amortissables

À l'acquisition d'un matériel :
1. Créer l'article avec `est_amortissable=True`
2. Renseigner la date d'acquisition et la valeur
3. Calculer annuellement l'amortissement
4. La VNC reflète la valeur comptable actuelle

---

## 📊 Rapports et statistiques

### Dashboard des périssables

```python
# KPIs périssables
lots_critiques = get_lots_a_perimer(session, jours=7)
lots_alertes = get_lots_a_perimer(session, jours=30)
lots_perimes = get_lots_perimes(session)

stats = {
    "lots_critiques": len(lots_critiques),
    "lots_alertes": len(lots_alertes),
    "lots_perimes": len(lots_perimes),
    "valeur_pertes": sum([l['lot'].quantite_restante * article.prix_unitaire for l in lots_perimes])
}
```

### Dashboard des amortissements

```python
# Valeur totale des immobilisations
materiels = session.exec(select(Article).where(Article.est_amortissable == True)).all()

valeur_brute_totale = sum([m.valeur_acquisition for m in materiels])
valeur_nette_totale = 0

for materiel in materiels:
    plan = StockService.get_plan_amortissement(session, materiel.id)
    if plan:
        # Prendre la VNC de la dernière année calculée
        derniere_vnc = [p for p in plan if p['calcule']][-1]['valeur_nette_comptable']
        valeur_nette_totale += derniere_vnc
    else:
        valeur_nette_totale += materiel.valeur_acquisition

stats = {
    "nb_materiels": len(materiels),
    "valeur_brute": valeur_brute_totale,
    "valeur_nette": valeur_nette_totale,
    "amortissement_cumule": valeur_brute_totale - valeur_nette_totale
}
```

---

## ⚙️ Configuration et bonnes pratiques

### Articles périssables

✅ **À faire** :
- Toujours créer un lot à chaque réception
- Définir un `seuil_alerte_peremption_jours` adapté (30-60 jours)
- Exécuter quotidiennement `mettre_a_jour_statuts_lots()`
- Utiliser `consommer_lot_fifo()` pour garantir la gestion FIFO

❌ **À éviter** :
- Ne pas créer de lot pour les articles périssables
- Ignorer les alertes de péremption
- Faire des sorties manuelles sans FIFO

### Matériels amortissables

✅ **À faire** :
- Calculer l'amortissement chaque fin d'exercice
- Vérifier les durées selon les normes comptables locales
- Documenter les calculs (colonne `observations`)
- Générer le plan complet pour audit

❌ **À éviter** :
- Sauter des années d'amortissement
- Modifier les valeurs après calcul
- Oublier la valeur résiduelle

---

## 🔧 Migration de la base de données

Pour activer ces fonctionnalités, exécuter la migration :

```bash
python scripts/migrate_stock_avances.py
```

Cette migration :
- ✅ Ajoute les colonnes pour articles périssables
- ✅ Ajoute les colonnes pour matériels amortissables
- ✅ Crée la table `lot_perissable`
- ✅ Crée la table `amortissement`

---

## 📚 Références

### Modèles de données

- **Article** : `mppeep/app/models/stock.py` (lignes 44-91)
- **LotPerissable** : `mppeep/app/models/stock.py` (lignes 249-282)
- **Amortissement** : `mppeep/app/models/stock.py` (lignes 288-324)

### Services

- **StockService** : `mppeep/app/services/stock_service.py`
  - Gestion périssables : lignes 523-773
  - Gestion amortissement : lignes 775-1061

---

## 🎯 Prochaines étapes

Pour utiliser ces fonctionnalités :

1. ✅ Migrer la base de données
2. ✅ Configurer les articles (périssables et/ou amortissables)
3. ✅ Créer des lots pour les articles périssables
4. ✅ Calculer les amortissements annuels
5. ✅ Configurer les alertes et rapports

**Bon usage des fonctionnalités avancées ! 🚀**

