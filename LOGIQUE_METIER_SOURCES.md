# 📊 LOGIQUE MÉTIER : Détermination des Sources de Données (DB, USER, DEFAULT)

## 🎯 Objectif
Déterminer automatiquement la source de chaque donnée dans le rapport pour appliquer le bon styling :
- **USER** (vert) : Données saisies/modifiées par l'utilisateur via le modal
- **DB** (bold+italique) : Données récupérées depuis SystemSettings (base de données)
- **DEFAULT** (rouge) : Données par défaut codées en dur dans le code

---

## 🔑 Variables de Classe (lignes 55-64)

```python
_user_data_keys: set[str] = set()      # Clés des données USER
_db_data_keys: set[str] = set()        # Clés des données DB
_original_default_data: dict           # Copie des données par défaut
_db_session: Session | None            # Session DB pour récupérer SystemSettings
```

---

## 📝 Processus en 3 Étapes

### 1️⃣ INITIALISATION (ligne 680-697 dans `generate_pdf()`)

**Marquage des données USER** :
```python
# Ligne 686-692
for key, value in user_data.items():
    default_value = cls.DEFAULT_DATA.get(key)
    if default_value is None or value != default_value:
        cls._user_data_keys.add(key)  # ← Marquage comme USER
```

**Logique** : Si une valeur dans `data` (du modal) diffère de `DEFAULT_DATA` → **USER**

---

### 2️⃣ RÉCUPÉRATION DB (ligne 2638-2684 dans `_draw_introduction_generale()`)

**Marquage des données DB** :
```python
# Récupération depuis SystemSettings
if settings.minister_role:
    db_data_map["ministere"] = ministere_name
    cls._db_data_keys.add("ministere")  # ← Marquage comme DB

if settings.ministry_mission:
    db_intro_data["mission_ministere"] = settings.ministry_mission
    cls._db_data_keys.add(f"introduction.mission_ministere")  # ← Marquage comme DB
```

**Logique** : Si une valeur est récupérée depuis SystemSettings → **DB**

---

### 3️⃣ DÉCISION FINALE (ligne 71-95 : `_determine_data_source_for_canvas()`)

**Algorithme de priorité** :
```python
# Ligne 87-88 : Priorité 1 - USER
if is_user_explicit or key in cls._user_data_keys:
    return value, "user"  # ← Vert

# Ligne 91-92 : Priorité 2 - DB
if key in cls._db_data_keys or (db_value is not None and value == db_value):
    return value, "db"  # ← Bold+Italique

# Ligne 95 : Priorité 3 - DEFAULT
return value, "default"  # ← Rouge
```

**Priorité** : **USER > DB > DEFAULT**

---

## 🔄 Fonctions Spécialisées

### Pour les valeurs principales (`ministere`, `annee`) : ligne 2700-2722

```python
def get_main_value(key: str, default_value: Any = None) -> tuple[Any, str]:
    # Priorité 1: USER
    if key in cls._user_data_keys:
        return user_value, "user"
    
    # Priorité 2: DB (depuis db_data_map)
    if key in db_data_map:
        return db_value, "db"
    
    # Priorité 3: DEFAULT
    return final_value, "default"
```

### Pour les valeurs d'introduction : ligne 2725-2755

```python
def get_intro_value(key: str, default_value: Any = None) -> tuple[Any, str]:
    # Priorité 1: USER (via modal)
    if "introduction" in cls._user_data_keys:
        if user_value != default_value:
            return user_value, "user"
    
    # Priorité 2: DB (depuis db_intro_data)
    if key in db_intro_data:
        return db_value, "db"
    
    # Priorité 3: DEFAULT
    return final_value, "default"
```

---

## 📍 Lignes Clés

| Fonction/Rôle | Ligne | Description |
|---------------|-------|-------------|
| **Variables de classe** | 55-64 | Définition des sets de tracking |
| **Initialisation USER** | 686-692 | Marquage des données USER |
| **Récupération DB** | 2638-2684 | Marquage des données DB |
| **Décision principale** | 71-95 | `_determine_data_source_for_canvas()` |
| **Valeurs principales** | 2700-2722 | `get_main_value()` |
| **Valeurs introduction** | 2725-2755 | `get_intro_value()` |
| **Formatage par source** | 164-183 | `_format_data_by_source()` |

---

## 🎨 Application du Styling

Une fois la source déterminée, le styling est appliqué :

```python
# Ligne 178-183
if source == "user":
    return cls._format_user_data(text)      # Vert
elif source == "db":
    return cls._format_db_data(text)        # Bold+Italique
else:  # default
    return cls._format_default_data(text)   # Rouge
```

---

## ✅ Exemple Concret

**Scénario** : Nom du ministère

1. **Valeur par défaut** (DEFAULT_DATA) : `"MINISTERE DU PATRIMOINE..."`
2. **Dans SystemSettings** : `minister_role = "Ministre du Patrimoine..."`
3. **Récupération** (ligne 2646-2659) :
   - Extraction du nom depuis `minister_role`
   - Ajout à `db_data_map["ministere"]`
   - Marquage : `_db_data_keys.add("ministere")` → **DB**
4. **Décision** (ligne 2709-2718) :
   - Si `"ministere"` dans `_user_data_keys` → **USER** (vert)
   - Sinon si `"ministere"` dans `db_data_map` → **DB** (bold+italique)
   - Sinon → **DEFAULT** (rouge)

**Résultat** : Le nom du ministère sera stylé en **bold+italique** (DB) car il vient de SystemSettings.

