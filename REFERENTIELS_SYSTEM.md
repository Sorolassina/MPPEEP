# 📚 Système de Gestion des Référentiels

## 📋 Vue d'Ensemble

Le système de référentiels permet de gérer les **données de référence** utilisées dans la gestion du personnel :
- 📁 **Programmes** : Programmes budgétaires
- 🏢 **Directions** : Directions organisationnelles
- 📋 **Services** : Services opérationnels
- 🎓 **Grades** : Grades et catégories

---

## 🏗️ Structure Hiérarchique

```
Programme (P01, P02, P03)
    └── Direction (DG, DAF, DRH, DPE, DPAT)
            └── Service (SCPT, SBUD, SCAR, etc.)

Grade (A1, A2, B1, B2, C1, C2, D1, D2)
    └── Catégorie (A, B, C, D)
```

---

## 📊 Données Pré-Initialisées

### Programmes (3)
| Code | Libellé |
|------|---------|
| P01 | Pilotage et Soutien Institutionnel |
| P02 | Gestion du Portefeuille de l'État |
| P03 | Gestion du Patrimoine de l'État |

### Directions (5)
| Code | Libellé | Programme |
|------|---------|-----------|
| DG | Direction Générale | P01 |
| DAF | Direction Administrative et Financière | P01 |
| DRH | Direction des Ressources Humaines | P01 |
| DPE | Direction du Portefeuille de l'État | P02 |
| DPAT | Direction du Patrimoine de l'État | P03 |

### Services (10)
| Code | Libellé | Direction |
|------|---------|-----------|
| SCPT | Service Comptabilité | DAF |
| SBUD | Service Budget | DAF |
| SAPV | Service Approvisionnement | DAF |
| SCAR | Service Carrière | DRH |
| SPAY | Service Paie | DRH |
| SFOR | Service Formation | DRH |
| SPAR | Service Participations | DPE |
| SETU | Service Études | DPE |
| SGIM | Service Gestion Immobilière | DPAT |
| SINV | Service Inventaire | DPAT |

### Grades (11)
| Code | Libellé | Catégorie | Échelons |
|------|---------|-----------|----------|
| A1 | Administrateur Civil | A | 1-7 |
| A2 | Attaché d'Administration | A | 1-6 |
| A3 | Secrétaire d'Administration | A | 1-5 |
| B1 | Contrôleur des Services Administratifs | B | 1-6 |
| B2 | Contrôleur du Trésor | B | 1-5 |
| B3 | Secrétaire d'Administration | B | 1-5 |
| C1 | Commis des Services Administratifs | C | 1-5 |
| C2 | Agent Administratif | C | 1-4 |
| C3 | Aide Administratif | C | 1-3 |
| D1 | Agent de Bureau | D | 1-4 |
| D2 | Homme de Service | D | 1-3 |

---

## 🔧 Opérations CRUD

### Accès
```
Accueil → Paramètres → Gérer les Référentiels
```
Ou directement : `http://localhost:8000/api/v1/referentiels/`

### Interface
- **Onglets** : Programmes | Directions | Services | Grades
- **Tableaux** : Liste de toutes les données
- **Actions** : Créer, Modifier, Désactiver

### Opérations Disponibles

#### Créer
1. Cliquer sur **"➕ Nouveau [Type]"**
2. Remplir le formulaire modal
3. Cliquer sur **"Enregistrer"**

#### Modifier
1. Cliquer sur l'icône **✏️** dans le tableau
2. Modifier les champs
3. Cliquer sur **"Enregistrer"**

#### Supprimer (Soft Delete)
1. Cliquer sur l'icône **🗑️** dans le tableau
2. Confirmer la désactivation
3. L'élément passe en statut "Inactif"

---

## 🛣️ Endpoints API

### Programmes
```
GET    /api/v1/referentiels/api/programmes         # Liste
POST   /api/v1/referentiels/api/programmes         # Créer
PUT    /api/v1/referentiels/api/programmes/{id}    # Modifier
DELETE /api/v1/referentiels/api/programmes/{id}    # Désactiver
```

### Directions
```
GET    /api/v1/referentiels/api/directions         # Liste
POST   /api/v1/referentiels/api/directions         # Créer
PUT    /api/v1/referentiels/api/directions/{id}    # Modifier
DELETE /api/v1/referentiels/api/directions/{id}    # Désactiver
```

### Services
```
GET    /api/v1/referentiels/api/services           # Liste
POST   /api/v1/referentiels/api/services           # Créer
PUT    /api/v1/referentiels/api/services/{id}      # Modifier
DELETE /api/v1/referentiels/api/services/{id}      # Désactiver
```

### Grades
```
GET    /api/v1/referentiels/api/grades             # Liste
POST   /api/v1/referentiels/api/grades             # Créer
PUT    /api/v1/referentiels/api/grades/{id}        # Modifier
DELETE /api/v1/referentiels/api/grades/{id}        # Désactiver
```

---

## 💾 Initialisation

### Automatique (Recommandé)
Les données sont **initialisées automatiquement** au démarrage de l'application via `scripts/init_db.py`.

### Manuelle
```bash
python scripts/init_personnel_data.py
```

### Vérifier les Données
```bash
# Via Python
python scripts/show_config.py

# Via SQLite
sqlite3 app.db "SELECT * FROM programme;"
sqlite3 app.db "SELECT * FROM direction;"
sqlite3 app.db "SELECT * FROM service;"
sqlite3 app.db "SELECT * FROM grade_complet;"
```

---

## 🔒 Sécurité

### Authentification Required
✅ Toutes les opérations nécessitent une authentification (`get_current_user`)

### Soft Delete
✅ La suppression est un **soft delete** (mise à `actif=False`)
- Les données restent en base
- Elles n'apparaissent plus dans les listes actives
- Possibilité de réactivation

### Validation
✅ Codes uniques (pas de doublon)
✅ Champs requis vérifiés
✅ Logging de toutes les opérations

---

## 🎨 Interface Utilisateur

### Design
- **Onglets** pour naviguer entre les types
- **Tableaux** avec hover effects
- **Modal** pour créer/modifier
- **Badges** pour le statut (Actif/Inactif)
- **Action icons** avec animations

### UX
- ✅ Overlay pendant les opérations
- ✅ Rechargement automatique après succès
- ✅ Confirmation avant suppression
- ✅ Messages d'erreur clairs

---

## 📱 Responsive

✅ Adapté pour mobile/tablette/desktop
✅ Tables scrollables sur petits écrans
✅ Modal adaptatif

---

## 🔄 Utilisation dans l'Application

### Formulaire Nouvel Agent
Les listes déroulantes sont **automatiquement peuplées** :
```html
<select name="programme_id">
  {% for prog in programmes %}
    <option value="{{ prog.id }}">{{ prog.code }} - {{ prog.libelle }}</option>
  {% endfor %}
</select>
```

### Filtrage Hiérarchique
Programme → Direction → Service (cascading selects)

### Statistiques
Les KPIs de la page Personnel utilisent ces données pour calculer :
- Effectif par catégorie (via Grades)
- Répartition par service
- Répartition par direction

---

## 📝 Exemple de Workflow

### Ajouter un Nouveau Service

1. **Accueil** → **Paramètres** → **Gérer les Référentiels**
2. Onglet **Services**
3. Click **"➕ Nouveau Service"**
4. Remplir :
   - Code : `SINF`
   - Libellé : `Service Informatique`
   - Direction : `DAF`
5. **Enregistrer**
6. ✅ Service créé et visible dans les formulaires !

---

## 🧪 Tests

### Vérifier l'Initialisation
```bash
python scripts/init_personnel_data.py
```

**Output attendu** :
```
📊 RÉSUMÉ :
  • Programmes : 3
  • Directions : 5
  • Services : 10
  • Grades : 11
```

### Tester l'Interface
1. Démarrer : `uvicorn app.main:app --reload`
2. Naviguer : http://localhost:8000/api/v1/referentiels/
3. Créer, modifier, supprimer des éléments
4. Vérifier qu'ils apparaissent dans le formulaire agent

---

## 🚀 Fichiers Créés

```
app/api/v1/endpoints/referentiels.py     ← Endpoints CRUD (350 lignes)
app/templates/pages/referentiels.html    ← Interface web (510 lignes)
scripts/init_personnel_data.py           ← Script d'initialisation (192 lignes)
REFERENTIELS_SYSTEM.md                   ← Ce fichier
```

---

## 📊 Impact

### Avant
- ❌ Listes déroulantes vides dans formulaire agent
- ❌ Impossible d'ajouter des programmes/services
- ❌ Données en dur dans le code

### Après
- ✅ Listes déroulantes peuplées automatiquement
- ✅ CRUD complet via interface web
- ✅ Données dans la base de données
- ✅ Initialisation automatique au démarrage
- ✅ Extensible facilement

---

## 🎯 Avantages

1. **Flexibilité** : Modifier l'organigramme sans toucher au code
2. **Scalabilité** : Ajouter autant de services/directions que nécessaire
3. **Maintenance** : Interface admin simple et intuitive
4. **Traçabilité** : Toutes les opérations sont loggées
5. **Sécurité** : Soft delete + authentification obligatoire

---

## 🔜 Évolutions Futures

- [ ] Import/Export CSV des référentiels
- [ ] Historique des modifications
- [ ] Organigramme visuel (arbre hiérarchique)
- [ ] Validation des dépendances (ex: ne pas supprimer un service utilisé)
- [ ] Archivage des éléments inactifs

---

**✅ Système de référentiels production-ready !**

