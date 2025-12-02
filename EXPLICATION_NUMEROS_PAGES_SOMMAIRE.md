# Explication : Comment les numéros de page dans le sommaire sont déterminés

## Vue d'ensemble

Le système utilise un mécanisme en **deux passes** pour déterminer les numéros de page dans le sommaire :

1. **Première passe** : Génération temporaire du sommaire pour calculer son nombre de pages
2. **Enregistrement** : Chaque section enregistre sa position de page pendant la génération
3. **Ajustement** : Toutes les positions sont ajustées en ajoutant le nombre de pages du sommaire
4. **Deuxième passe** : Génération finale du sommaire avec les pages ajustées

---

## Exemple concret : "LISTE DES TABLEAUX"

### Étape 1 : Génération temporaire du sommaire

```python
# Ligne 11447-11459
sommaire_temp_buffer = BytesIO()
sommaire_temp_pdf = canvas.Canvas(sommaire_temp_buffer, pagesize=landscape(A4))
cls._draw_table_of_contents(sommaire_temp_pdf, width, height)
sommaire_temp_pdf.save()

# Compter le nombre de pages
sommaire_temp_reader = PdfReader(sommaire_temp_buffer)
nb_pages_sommaire = len(sommaire_temp_reader.pages)  # Exemple : 2 pages
```

**Résultat** : `nb_pages_sommaire = 2` (le sommaire occupe 2 pages)

### Étape 2 : Enregistrement de la position de "LISTE DES TABLEAUX"

```python
# Ligne 11482-11491
next_page = 2 + nb_pages_sommaire  # = 2 + 2 = 4
content_pdf.showPage()

# Générer la LISTE DES TABLEAUX
liste_tableaux_start = next_page  # = 4
cls._register_page_position("liste_tableaux", liste_tableaux_start)
# Enregistre : "liste_tableaux" → 4 dans cls._page_positions
```

**Résultat** : `cls._page_positions["liste_tableaux"] = 4`

### Étape 3 : Ajustement des positions estimées (programmes uniquement)

```python
# Ligne 11463-11468
# À ce stade, seules les positions des programmes sont enregistrées (estimations)
# Les positions du contenu ne sont pas encore enregistrées
adjusted_positions = {}
for key, page_num in cls._page_positions.items():
    adjusted_positions[key] = page_num + nb_pages_sommaire
    # "programme_1_start": 13 + 2 = 15
cls._page_positions = adjusted_positions
```

**Résultat** : `cls._page_positions["programme_1_start"] = 15` (ajusté)
**Note** : Les positions du contenu ne sont pas encore enregistrées à ce stade.

### Étape 4 : Récupération dans le sommaire final

```python
# Ligne 932 dans _draw_table_of_contents (génération finale)
toc_items.append({
    "text": "LISTE DES TABLEAUX", 
    "page": cls._get_page_position("liste_tableaux", 3),  # Récupère 4 (valeur enregistrée)
    "level": 0, 
    "bold": False
})
```

**Résultat** : Le sommaire affiche "LISTE DES TABLEAUX" avec le numéro de page **4** (valeur réelle enregistrée)

---

## Ordre des opérations (IMPORTANT)

L'ordre exact des opérations est crucial pour comprendre :

1. **Enregistrement des positions estimées des programmes** (SANS sommaire) - ligne 11437-11446
   - Exemple : `programme_1_start = 13` (estimation sans sommaire)

2. **Génération temporaire du sommaire** - ligne 11448-11460
   - Calcule `nb_pages_sommaire = 2` (exemple)

3. **Ajustement de TOUTES les positions** (programmes uniquement à ce stade) - ligne 11463-11468
   - `programme_1_start = 13 + 2 = 15` (ajusté avec sommaire)

4. **Génération du contenu** qui enregistre les positions **RÉELLES** (déjà avec sommaire) - ligne 11491+
   - `liste_tableaux = 4` (déjà après sommaire, pas besoin d'ajustement)
   - `liste_graphiques = 5`
   - etc.

**Note** : Les positions du contenu sont enregistrées directement avec les bonnes valeurs (après sommaire), donc elles n'ont pas besoin d'ajustement. Seules les positions estimées des programmes sont ajustées.

---

## Flux complet avec exemple numérique

### Scénario : Sommaire = 2 pages, Contenu commence à la page 4

#### Phase 1 : Préparation (avant génération du contenu)

1. **Enregistrement des positions estimées des programmes** (SANS sommaire) :
   - Estimation : contenu = 8 pages
   - `programme_1_start` → 1 + 8 + 1 = **10** (estimation sans sommaire)
   - Enregistré : `"programme_1_start" = 10`

2. **Génération temporaire du sommaire** :
   - `nb_pages_sommaire = 2`

3. **Ajustement des positions estimées** :
   - `programme_1_start` → 10 + 2 = **12** (ajusté avec sommaire)
   - `cls._page_positions["programme_1_start"] = 12`

#### Phase 2 : Génération du contenu (positions réelles)

4. **Génération du contenu** (après sommaire) :
   - `next_page = 2 + 2 = 4` (après couverture + sommaire)
   - `liste_tableaux_start = 4` → Enregistré : `"liste_tableaux" = 4`
   - `liste_graphiques_start = 5` → Enregistré : `"liste_graphiques" = 5`
   - `sigles_start = 6` → Enregistré : `"sigles_abreviations" = 6`
   - `introduction_start = 7` → Enregistré : `"introduction_generale" = 7`
   - `partie_i_start = 8` → Enregistré : `"partie_i" = 8`

#### Phase 3 : Génération finale du sommaire

5. **Récupération des positions dans le sommaire** :
   - `_get_page_position("liste_tableaux", 3)` → Retourne **4** (valeur réelle enregistrée)
   - `_get_page_position("liste_graphiques", 3)` → Retourne **5**
   - `_get_page_position("sigles_abreviations", 5)` → Retourne **6**
   - `_get_page_position("introduction_generale", 7)` → Retourne **7**
   - `_get_page_position("partie_i", 8)` → Retourne **8**
   - `_get_page_position("programme_1_start", 13)` → Retourne **12** (valeur ajustée)

6. **Affichage dans le sommaire** :
   ```
   LISTE DES TABLEAUX ......................... 4
   LISTE DES GRAPHIQUES ....................... 5
   SIGLES ET ABRÉVIATIONS ...................... 6
   INTRODUCTION GÉNÉRALE ....................... 7
   PARTIE I : LE MINISTÈRE .................... 8
   ...
   PARTIE II : LE PROGRAMME 1 ................. 12
   ```

---

## Méthodes utilisées

### `_register_page_position(key, page_number)`
Enregistre la position d'une page pour une section donnée.

**Exemple** :
```python
cls._register_page_position("liste_tableaux", 4)
# Enregistre dans cls._page_positions["liste_tableaux"] = 4
```

### `_get_page_position(key, default)`
Récupère la position d'une page pour une section donnée, ou retourne la valeur par défaut si non trouvée.

**Exemple** :
```python
page = cls._get_page_position("liste_tableaux", 3)
# Retourne 4 si enregistré, sinon 3 (valeur par défaut)
```

---

## Points importants

1. **Les positions sont enregistrées en temps réel** pendant la génération du contenu
2. **Le sommaire est généré en deux passes** : temporaire (pour calculer nb_pages) puis final (avec pages ajustées)
3. **Les valeurs par défaut** dans `_get_page_position` servent de fallback si une position n'a pas été enregistrée
4. **L'ajustement du sommaire** se fait avant la génération du contenu, donc les positions enregistrées sont déjà les positions finales

