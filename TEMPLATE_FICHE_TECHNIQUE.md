# 📥 Système de Template Excel pour Fiches Techniques

## 🎯 **Objectif**

Permettre aux utilisateurs de télécharger un modèle Excel pré-formaté pour créer des fiches techniques budgétaires conformes, réduisant ainsi les erreurs lors de l'import.

---

## 🚀 **Fonctionnalités Implémentées**

### **1. API de Téléchargement du Template**

**Route** : `GET /api/v1/budget/api/telecharger-template-fiche?annee=2025`

**Paramètres** :
- `annee` (optionnel) : Année budgétaire (défaut: 2025)

**Retour** : Fichier Excel `.xlsx` nommé `Modele_Fiche_Technique_{annee}.xlsx`

---

### **2. Structure du Template Excel**

#### **Feuille 1 : "Fiche Technique"**

**Colonnes** :
1. `CODE / LIBELLE` - Libellé de la ligne (Action, Service, Activité, Ligne budgétaire)
2. `BUDGET VOTÉ {N}` - Budget voté année N
3. `BUDGET ACTUEL {N}` - Budget actuel année N
4. `ENVELOPPE {N+1}` - Enveloppe demandée année N+1
5. `COMPLEMENT SOLLICITÉ` - Complément sollicité
6. `BUDGET SOUHAITÉ` - Budget souhaité
7. `ENGAGEMENT DE L'ETAT` - Engagement de l'État
8. `AUTRE COMPLEMENT` - Autre complément
9. `PROJET DE BUDGET {N+1}` - Projet de budget année N+1
10. `JUSTIFICATIFS` - Justification de la ligne

**Formatage** :
- ✅ En-têtes en **bleu foncé** avec texte blanc
- ✅ Bordures sur toutes les cellules
- ✅ Largeurs de colonnes ajustées
- ✅ Première ligne figée (freeze panes)
- ✅ Exemples en **gris clair**

**Exemples inclus** :
```
BIENS ET SERVICES
  Action : Pilotage et gouvernance
    Service Bénéficiaire : Direction Générale
      Activité : Coordination administrative
        Fournitures de bureau
        Matériel informatique

PERSONNEL
  Action : Gestion des ressources humaines

INVESTISSEMENT
  Action : Équipements et infrastructures
```

---

#### **Feuille 2 : "📋 Instructions"**

Contient :
- 📌 **Structure hiérarchique** détaillée
- ⚠️ **Règles importantes** à respecter
- 💡 **Exemples** concrets
- ✅ **Préfixes obligatoires** : `Action :`, `Service Bénéficiaire :`, `Activité :`

---

## 🎨 **Interface Utilisateur**

### **Bouton dans le Modal "Charger une Fiche"**

Ajout d'une zone bleue en haut du formulaire avec :
- 📥 **Titre** : "Besoin d'un modèle ?"
- 💬 **Description** : "Téléchargez notre modèle Excel pré-formaté avec des exemples"
- 🔘 **Bouton** : "📥 Télécharger le modèle Excel"

**Emplacement** : Page `/api/v1/budget/fiches` → Modal "📂 Charger une Fiche"

---

## 📋 **Hiérarchie Stricte**

```
1️⃣ NATURE DE DÉPENSE (MAJUSCULES)
   ↓
2️⃣ Action : [Libellé de l'action]
   ↓
3️⃣ Service Bénéficiaire : [Nom du service]
   ↓
4️⃣ Activité : [Nom de l'activité]
   ↓
5️⃣ Lignes budgétaires (sans préfixe)
```

---

## ✅ **Règles de Validation**

1. ✅ Les montants doivent être **numériques** (sans espaces ni symboles)
2. ✅ La colonne `CODE / LIBELLE` ne doit **JAMAIS** être vide
3. ✅ Respecter les **préfixes** exacts :
   - `Action :` ou `- Action :`
   - `Service Bénéficiaire :` ou `- Service Bénéficiaire :`
   - `Activité :` ou `- Activité :`
4. ✅ Les natures de dépenses en **MAJUSCULES** :
   - `BIENS ET SERVICES`
   - `PERSONNEL`
   - `INVESTISSEMENT` ou `INVESTISSEMENTS`
   - `TRANSFERTS`
5. ✅ Ne pas supprimer les **en-têtes** de colonnes

---

## 🔧 **Code Backend**

### **Fichier** : `mppeep/app/api/v1/endpoints/budget.py`

**Fonction principale** : `api_telecharger_template_fiche()`

**Dépendances** :
```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
```

**Styles appliqués** :
- `header_fill` : Bleu #4472C4
- `header_font` : Gras, blanc, taille 11
- `example_fill` : Gris #E7E6E6
- `border_style` : Bordures fines sur tout le pourtour

---

## 📊 **Workflow Utilisateur**

```
1. Utilisateur clique sur "📂 Charger une Fiche"
   ↓
2. Modal s'ouvre avec le bouton "📥 Télécharger le modèle Excel"
   ↓
3. Utilisateur télécharge le modèle
   ↓
4. Utilisateur remplit le modèle (supprime les exemples)
   ↓
5. Utilisateur sélectionne le programme
   ↓
6. Utilisateur charge le fichier rempli
   ↓
7. Système analyse et importe la structure hiérarchique
   ↓
8. Fiche technique créée avec Actions → Services → Activités → Lignes
```

---

## 🧪 **Test**

### **Étapes pour tester** :

1. Démarrer l'application
```bash
cd mppeep
uv run uvicorn app.main:app --reload
```

2. Naviguer vers : `http://localhost:8000/api/v1/budget/fiches`

3. Cliquer sur **"📂 Charger une Fiche"**

4. Cliquer sur **"📥 Télécharger le modèle Excel"**

5. Ouvrir le fichier téléchargé :
   - Vérifier la feuille "Fiche Technique"
   - Vérifier la feuille "📋 Instructions"
   - Supprimer les exemples (lignes grises)
   - Remplir avec vos données
   - Sauvegarder

6. Recharger le fichier dans le modal

7. Vérifier que l'import fonctionne correctement

---

## 🎨 **Aperçu Visuel**

### **Modal "Charger une Fiche"**

```
┌─────────────────────────────────────────────────────────┐
│  📂 Charger une Fiche Technique                    [×] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ╔═══════════════════════════════════════════════════╗ │
│  ║ 📥 Besoin d'un modèle ?                           ║ │
│  ║ Téléchargez notre modèle Excel pré-formaté        ║ │
│  ║                                                   ║ │
│  ║         [📥 Télécharger le modèle Excel]          ║ │
│  ╚═══════════════════════════════════════════════════╝ │
│                                                         │
│  Programme *                                            │
│  [-- Sélectionner un programme --        ▼]            │
│                                                         │
│  Fichier (.xlsx, .xls, .pdf)                            │
│  [Choisir un fichier]                                   │
│  💡 Utilisez le modèle Excel ci-dessus pour garantir   │
│     la conformité                                       │
│                                                         │
│                    [Annuler]  [📂 Charger la fiche]    │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 **Logs**

Lors du téléchargement du template :
```
INFO: 📥 Template de fiche technique téléchargé par user@example.com
```

---

## 🔒 **Sécurité**

- ✅ Authentification requise (`get_current_user`)
- ✅ Pas de données sensibles dans le template
- ✅ Fichier généré à la volée (pas de stockage)

---

## 🚀 **Améliorations Futures**

1. 💾 **Modèles personnalisables** par programme
2. 🎨 **Logo de l'organisation** dans le template
3. 📊 **Formules Excel** pour calculs automatiques
4. 🔒 **Protection de certaines cellules** (en-têtes)
5. 📋 **Validation de données** (listes déroulantes pour natures de dépenses)
6. 🌍 **Multilingue** (FR/EN)

---

## 📚 **Documentation Associée**

- `BUDGET_SYSTEM.md` : Système budgétaire complet
- `app/api/v1/endpoints/budget.py` : Code source de l'API
- `app/templates/pages/budget_fiches_hierarchique.html` : Interface utilisateur

---

**✅ Système de template Excel opérationnel et prêt à l'emploi !** 🎉

