# Gestion des Objectifs Globaux et Spécifiques

## Architecture de la Hiérarchie de Performance

La hiérarchie complète de performance est la suivante :

```
Orientation Stratégique
  └── Résultat Stratégique
      └── Objectif Global (type=STRATEGIQUE)
          └── Objectif Spécifique (type=OPERATIONNEL)
              └── Indicateur de Performance
```

## Gestion dans une Seule Table : `ObjectifPerformance`

**Important :** Il n'y a qu'**une seule table** `ObjectifPerformance` qui gère les deux types d'objectifs via le champ `type_objectif` :

### Objectifs Globaux (STRATEGIQUE)
- **Type** : `type_objectif = TypeObjectif.STRATEGIQUE`
- **Relation** : Lié à un `ResultatStrategique` via `resultat_strategique_id`
- **Caractéristiques** :
  - Représente les objectifs stratégiques de haut niveau
  - Déclinent les résultats stratégiques en objectifs concrets
  - Utilisés dans le tableau de politique ministérielle

### Objectifs Spécifiques (OPERATIONNEL)
- **Type** : `type_objectif = TypeObjectif.OPERATIONNEL`
- **Relation** : Lié à un `ObjectifPerformance` de type STRATEGIQUE via `objectif_global_id`
- **Caractéristiques** :
  - Représente les objectifs opérationnels de terrain
  - Déclinent les objectifs globaux en actions concrètes
  - Utilisés dans les sections programmes du rapport

## Structure de la Table

```python
class ObjectifPerformance(SQLModel, table=True):
    # Classification
    type_objectif: TypeObjectif = Field(default=TypeObjectif.OPERATIONNEL)
    
    # Relations hiérarchiques
    # Pour les objectifs globaux (STRATEGIQUE) :
    resultat_strategique_id: int | None = Field(
        default=None, 
        foreign_key="resultat_strategique.id"
    )
    
    # Pour les objectifs spécifiques (OPERATIONNEL) :
    objectif_global_id: int | None = Field(
        default=None, 
        foreign_key="objectif_performance.id"  # Auto-référence !
    )
```

## Chargement dans le Rapport Annuel

### Dans `_load_performance_hierarchy_from_db` :

1. **Charge les objectifs globaux** (STRATEGIQUE) liés aux résultats stratégiques :
   ```python
   objectifs_globaux = session.exec(
       select(ObjectifPerformance).where(
           and_(
               ObjectifPerformance.resultat_strategique_id == resultat.id,
               ObjectifPerformance.type_objectif == TypeObjectif.STRATEGIQUE
           )
       )
   ).all()
   ```

2. **Charge optionnellement les objectifs spécifiques** (OPERATIONNEL) liés aux objectifs globaux :
   ```python
   objectifs_specifiques = session.exec(
       select(ObjectifPerformance).where(
           and_(
               ObjectifPerformance.objectif_global_id == obj_global.id,
               ObjectifPerformance.type_objectif == TypeObjectif.OPERATIONNEL
           )
       )
   ).all()
   ```

### Dans `load_budget_data` :

1. **Compte les objectifs globaux** :
   ```python
   objectifs_globaux = session.exec(
       select(ObjectifPerformance).where(
           and_(
               ObjectifPerformance.type_objectif == TypeObjectif.STRATEGIQUE,
               ObjectifPerformance.resultat_strategique_id.isnot(None)
           )
       )
   ).all()
   ```

2. **Compte les objectifs spécifiques** :
   ```python
   objectifs_specifiques = session.exec(
       select(ObjectifPerformance).where(
           and_(
               ObjectifPerformance.type_objectif == TypeObjectif.OPERATIONNEL,
               ObjectifPerformance.objectif_global_id.isnot(None)
           )
       )
   ).all()
   ```

## Avantages de cette Approche

1. **Unification** : Une seule table pour gérer tous les objectifs
2. **Flexibilité** : La distinction se fait via un champ simple
3. **Hiérarchie** : L'auto-référence (`objectif_global_id`) permet de lier les objectifs spécifiques aux objectifs globaux
4. **Cohérence** : Tous les objectifs partagent les mêmes champs (titre, description, valeurs, dates, etc.)

## Exemple de Données

### Objectif Global (STRATEGIQUE)
```python
{
    "id": 1,
    "titre": "Améliorer la gouvernance du secteur",
    "type_objectif": "STRATEGIQUE",
    "resultat_strategique_id": 1,  # Lié au résultat stratégique
    "objectif_global_id": None,     # Pas de parent
    ...
}
```

### Objectif Spécifique (OPERATIONNEL)
```python
{
    "id": 5,
    "titre": "Mettre en place un système de suivi des décisions",
    "type_objectif": "OPERATIONNEL",
    "resultat_strategique_id": None,  # Pas directement lié
    "objectif_global_id": 1,          # Lié à l'objectif global #1
    ...
}
```

## Utilisation dans le Rapport

- **Section "I.2. Politique ministérielle"** : Affiche la hiérarchie Orientation → Résultat → Objectif Global
- **Sections programmes** : Utilise les objectifs spécifiques (OPERATIONNEL) pour détailler les actions
- **Tableaux d'indicateurs** : Les indicateurs sont liés aux objectifs spécifiques (OPERATIONNEL) via `objectif_id`



