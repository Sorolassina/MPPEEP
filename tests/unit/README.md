# 🔬 Tests Unitaires

## 🤔 Pourquoi "Unitaire" ?

Le mot "**unitaire**" vient de "**unité**", comme une brique de Lego. On teste **une seule pièce à la fois**, isolée du reste.

### 🏗️ Analogie Simple

Imaginez que vous construisez une maison :

- ✅ **Test Unitaire** = Vérifier qu'une seule brique est solide
- ⚠️ **Pas unitaire** = Vérifier que toute la maison tient debout

**Exemples concrets dans notre application :**

| Ce qu'on teste | Ce que ça fait |
|----------------|----------------|
| `get_password_hash()` | Transformer un mot de passe en code secret |
| `verify_password()` | Vérifier si un mot de passe est correct |
| `Settings()` | Charger la configuration de l'app |

---

## 🎯 Objectif des Tests Unitaires

### Pour quoi faire ?

1. **Vérifier qu'une fonction fait ce qu'elle doit faire**
   - Exemple : Si je hashe "password123", ça ne doit PAS donner "password123" en clair
   
2. **Détecter les bugs rapidement**
   - Si une fonction est cassée, on le sait tout de suite
   
3. **Documenter le code**
   - Les tests montrent comment utiliser une fonction

### 📊 Avantages

✅ **Très rapide** - Quelques millisecondes par test  
✅ **Facile à déboguer** - On sait exactement quelle fonction pose problème  
✅ **Fiable** - Pas d'effets de bord (pas de réseau, pas de fichiers)

---

## ⚙️ Comment ça Fonctionne ?

### Principe Simple

```
1. Préparer les données d'entrée
2. Appeler la fonction à tester
3. Vérifier que le résultat est correct
```

### 🎬 Exemple Concret

**Test : Vérifier que le hashing de mot de passe fonctionne**

```python
def test_password_hashing():
    # 1. PRÉPARATION (Arrange)
    password = "MonMotDePasse123"
    
    # 2. ACTION (Act)
    password_haché = get_password_hash(password)
    
    # 3. VÉRIFICATION (Assert)
    # Le hash ne doit PAS être le mot de passe en clair
    assert password_haché != "MonMotDePasse123"
    # Le hash doit commencer par $2b$ (format bcrypt)
    assert password_haché.startswith("$2b$")
```

**Ce qui se passe :**
1. On donne "MonMotDePasse123" à la fonction
2. La fonction retourne quelque chose comme "$2b$12$xyz..."
3. On vérifie que c'est bien un hash, pas le mot de passe en clair

---

## 🚀 Lancer les Tests Unitaires

### 📝 Commandes Simples

```bash
# Tous les tests unitaires
pytest tests/unit/

# Avec plus de détails
pytest tests/unit/ -v

# Un seul fichier
pytest tests/unit/test_security.py

# Une seule fonction
pytest tests/unit/test_security.py::test_password_hashing
```

### 🎨 Comprendre les Résultats

**✅ Succès (PASSED)** - Tout va bien !
```
tests/unit/test_security.py::test_password_hashing PASSED [100%]
```

**❌ Échec (FAILED)** - Quelque chose ne va pas
```
tests/unit/test_security.py::test_password_hashing FAILED [100%]
AssertionError: assert False
```

---

## 📂 Fichiers de Tests Unitaires

### `test_config.py` - Configuration

**Ce qu'on teste :**
- Est-ce que DEBUG=true utilise bien SQLite ?
- Est-ce que DEBUG=false utilise bien PostgreSQL ?
- Est-ce que les variables d'environnement sont bien lues ?

**Pourquoi c'est important :**  
Si la config est mal lue, l'app peut utiliser la mauvaise base de données !

**Exemple :**
```python
def test_database_url_auto_sqlite_debug_true():
    settings = Settings(DEBUG=True)
    # Vérifie qu'on utilise SQLite en mode debug
    assert settings.database_url.startswith("sqlite:///")
```

---

### `test_security.py` - Sécurité

**Ce qu'on teste :**
- Le hashing des mots de passe
- La vérification des mots de passe
- Cas spéciaux (caractères spéciaux, mots de passe longs, etc.)

**Pourquoi c'est important :**  
La sécurité des mots de passe est CRITIQUE ! Un bug ici = faille de sécurité.

**Exemples de tests :**
- ✅ Un mot de passe hashé n'est pas en clair
- ✅ Le même mot de passe = 2 hashs différents (grâce au "sel")
- ✅ Vérifier un mauvais mot de passe retourne False

---

### `test_models.py` - Modèles de Données

**Ce qu'on teste :**
- Création d'utilisateurs en base
- Valeurs par défaut (is_active=True, etc.)
- Contraintes (email unique)

**Pourquoi c'est important :**  
Les modèles définissent la structure de vos données. S'ils sont cassés, toute l'app est cassée.

**Exemples de tests :**
- ✅ Créer un utilisateur enregistre bien toutes les infos
- ✅ On ne peut pas créer 2 users avec le même email
- ✅ Un utilisateur créé est actif par défaut

---

## 💡 Conseils pour Comprendre

### 🔍 Lire un Test Unitaire

Tous nos tests suivent le pattern **AAA** :

```python
def test_quelque_chose():
    # ========== A - ARRANGE (Préparer) ==========
    # On prépare les données
    password = "secret123"
    
    # ========== A - ACT (Agir) ==========
    # On appelle la fonction
    result = get_password_hash(password)
    
    # ========== A - ASSERT (Vérifier) ==========
    # On vérifie le résultat
    assert result != password
```

### 🎯 Ce qu'on NE teste PAS en unitaire

❌ Plusieurs fonctions ensemble  
❌ L'API HTTP  
❌ La base de données réelle  
❌ Le réseau  

→ Ces choses sont testées dans les **tests d'intégration**

---

## 🆘 Problèmes Courants

### Mon test échoue, que faire ?

1. **Lire le message d'erreur**
   ```
   AssertionError: assert 'password123' != 'password123'
   ```
   → Le hash retourne le mot de passe en clair (BUG!)

2. **Lancer juste ce test avec détails**
   ```bash
   pytest tests/unit/test_security.py::test_password_hashing -vvs
   ```

3. **Vérifier le code de la fonction testée**
   - Aller dans `app/core/security.py`
   - Voir ce qui ne va pas

---

## 📊 Statistiques Actuelles

| Fichier | Nombre de Tests | Temps Moyen |
|---------|-----------------|-------------|
| `test_config.py` | 8 tests | ~5ms |
| `test_security.py` | 8 tests | ~100ms (bcrypt est lent) |
| `test_models.py` | 5 tests | ~20ms |

**Total : 21 tests unitaires** ⚡

---

## 🎓 Pour Aller Plus Loin

### Questions Fréquentes

**Q: Pourquoi les tests de sécurité sont plus lents ?**  
R: Le hashing bcrypt est volontairement lent pour la sécurité (éviter le bruteforce).

**Q: C'est grave si un test unitaire échoue ?**  
R: OUI ! Ça veut dire qu'une fonction de base est cassée. À corriger en priorité.

**Q: Combien de tests unitaires faut-il ?**  
R: Règle d'or : **70% des tests doivent être unitaires** (ils sont rapides et fiables).

### Ressources

- 📖 [Comprendre les Tests Unitaires](https://fr.wikipedia.org/wiki/Test_unitaire)
- 🎥 Tutoriel vidéo : Chercher "pytest tutorial" sur YouTube
- 📚 Documentation Pytest : https://docs.pytest.org/

---

## ✨ En Résumé

| Aspect | Explication Simple |
|--------|-------------------|
| **Nom** | "Unitaire" = tester UNE seule chose |
| **Objectif** | Vérifier qu'une fonction fonctionne bien toute seule |
| **Vitesse** | ⚡ Très rapide (< 100ms) |
| **Quand** | À chaque modification de code |
| **Commande** | `pytest tests/unit/` |

**💡 Pensez aux tests unitaires comme des "mini-vérifications" de chaque pièce de votre application !**

