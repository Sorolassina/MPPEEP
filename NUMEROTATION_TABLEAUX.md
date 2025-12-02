# Système de Numérotation des Tableaux

## Vue d'ensemble

Le système de numérotation des tableaux dans le Rapport Annuel de Performance utilise un **compteur global continu** qui s'incrémente automatiquement pour chaque tableau créé dans le document.

## Architecture du Système

### 1. Compteur Global de Classe

```python
# Variable de classe stockée dans RapportAnnuelPerformanceGeneratorSimpleDoc
_tableau_counter: int = 1
```

- **Portée** : Variable de classe partagée entre toutes les instances
- **Type** : Entier (`int`)
- **Valeur initiale** : `1`

### 2. Méthodes de Gestion du Compteur

#### `_get_next_tableau_numero()`
```python
@classmethod
def _get_next_tableau_numero(cls) -> int:
    numero = cls._tableau_counter
    cls._tableau_counter += 1
    return numero
```

**Fonction** : 
- Retourne le numéro actuel du compteur
- Incrémente automatiquement le compteur pour le prochain tableau
- Utilisée à chaque création d'un nouveau tableau

#### `_reset_tableau_counter(start_value=1)`
```python
@classmethod
def _reset_tableau_counter(cls, start_value: int = 1):
    cls._tableau_counter = start_value
```

**Fonction** :
- Réinitialise le compteur à une valeur spécifique
- Utilisée au début de la génération du PDF

## Processus de Numérotation

### Étape 1 : Initialisation

Au début de la génération du PDF (`generate_pdf`), le compteur est initialisé :

```python
cls._reset_tableau_counter(2)  # Le premier tableau commence à 2
```

**Note** : Le compteur commence à 2 car le "Tableau 1" est réservé pour un tableau spécifique (probablement le tableau récapitulatif).

### Étape 2 : Tableaux du Ministère (Partie I)

Les tableaux de la Partie I utilisent directement `_get_next_tableau_numero()` :

1. **Tableau 2** : "Composantes des cadres de performance du ministère"
   ```python
   tableau_numero = cls._get_next_tableau_numero()  # Retourne 2
   ```

2. **Tableau 3** : "Réalisations du cadre de performance du ministère"
   ```python
   tableau_numero = cls._get_next_tableau_numero()  # Retourne 3
   ```

3. **Tableau 4** : "Tableau présentant l'exécution du budget du ministère"
   ```python
   tableau_numero = cls._get_next_tableau_numero()  # Retourne 4
   ```

### Étape 3 : Tableaux des Programmes

Pour chaque programme, 4 tableaux sont créés de manière séquentielle :

**Programme 1** :
- **Tableau 5** : "Exécution financière par action du programme 1"
- **Tableau 6** : "Suivi des investissements du Programme 1"
- **Tableau 7** : "Exécution des prévisions d'effectifs du programme 1"
- **Tableau 8** : "Évolution des indicateurs du programme 1"

**Programme 2** :
- **Tableau 9** : "Exécution financière par action du programme 2"
- **Tableau 10** : "Suivi des investissements du Programme 2"
- **Tableau 11** : "Exécution des prévisions d'effectifs du programme 2"
- **Tableau 12** : "Évolution des indicateurs du programme 2"

Et ainsi de suite pour chaque programme supplémentaire.

### Exemple d'Utilisation dans le Code

```python
# Dans _draw_partie_i_ministere
tableau_numero = cls._get_next_tableau_numero()  # Ex: 2
story.append(Paragraph(f"Tableau {tableau_numero}: Composantes des cadres...", style))

# Plus loin...
tableau_numero = cls._get_next_tableau_numero()  # Ex: 3
story.append(Paragraph(f"Tableau {tableau_numero}: Réalisations du cadre...", style))

# Dans _draw_partie_programme_simpledoc
tableau_numero = cls._get_next_tableau_numero()  # Ex: 5
tableau_titre = f"Tableau {tableau_numero}: Exécution financière par action..."
story.append(Paragraph(f"<b>{tableau_titre}</b>", style))
```

## Caractéristiques Importantes

### ✅ Numérotation Continue
- Le compteur s'incrémente de manière continue dans tout le document
- Aucun redémarrage du compteur entre les sections
- Garantit une numérotation séquentielle (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, ...)

### ✅ Automatique
- Pas besoin de spécifier manuellement le numéro
- Chaque appel à `_get_next_tableau_numero()` retourne automatiquement le bon numéro
- Réduction des erreurs de numérotation

### ✅ Thread-Safe (Variable de Classe)
- La variable de classe est partagée entre toutes les méthodes
- Assure la cohérence de la numérotation dans tout le document

## Ordre des Tableaux dans le Document

1. **Tableau 1** : (Récapitulatif - si présent)
2. **Tableau 2** : Composantes des cadres de performance du ministère
3. **Tableau 3** : Réalisations du cadre de performance du ministère
4. **Tableau 4** : Tableau présentant l'exécution du budget du ministère
5. **Tableau 5-N** : Tableaux des programmes (4 par programme)
   - Exécution financière par action
   - Suivi des investissements
   - Exécution des prévisions d'effectifs
   - Évolution des indicateurs

## Avantages de cette Approche

1. **Simplicité** : Un seul compteur gère toute la numérotation
2. **Maintenabilité** : Facile d'ajouter ou retirer des tableaux
3. **Fiabilité** : Impossible d'avoir des numéros dupliqués ou manquants
4. **Flexibilité** : Fonctionne avec un nombre variable de programmes

## Points d'Attention

⚠️ **Important** : 
- Le compteur est initialisé à 2 au début de chaque génération
- Assurez-vous de ne pas réinitialiser le compteur en cours de génération
- Si vous ajoutez un nouveau tableau, il prendra automatiquement le prochain numéro disponible

