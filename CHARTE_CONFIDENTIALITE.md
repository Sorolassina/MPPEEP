# 📋 Charte de Confidentialité - Documentation

## 🎯 Vue d'ensemble

La charte de confidentialité est un mécanisme obligatoire qui force chaque utilisateur à accepter les règles de confidentialité et de protection des données du ministère lors de sa première connexion.

---

## 🔧 Fonctionnalités

### ✅ **Acceptation obligatoire**
- À la première connexion, l'utilisateur est automatiquement redirigé vers la charte
- L'accès à l'application n'est possible qu'après acceptation
- Une session temporaire (10 minutes) est créée pour afficher la charte

### 📝 **Traçabilité complète**
- Date et heure d'acceptation enregistrées
- Version de la charte acceptée stockée
- Activité loggée dans l'historique utilisateur

### 🔄 **Gestion des versions**
- Version actuelle : `1.0`
- Possibilité de forcer une nouvelle acceptation en changeant la version

---

## 📊 Schéma de la base de données

### Nouveaux champs dans la table `user` :

```sql
privacy_policy_accepted BOOLEAN DEFAULT FALSE
privacy_policy_accepted_at TIMESTAMP
privacy_policy_version VARCHAR(20)
```

---

## 🚀 Installation et Migration

### 1. **Appliquer la migration**

```bash
# Depuis le dossier mppeep/
python scripts/add_privacy_policy_fields.py
```

Cette commande ajoute les colonnes nécessaires à la table `user`.

### 2. **Configuration**

Dans `.env` ou `config.py` :

```python
PRIVACY_POLICY_VERSION = "1.0"  # Version actuelle
PRIVACY_POLICY_REQUIRED = True  # Forcer l'acceptation (True par défaut)
```

---

## 🔐 Flux d'authentification

### **Avant (sans charte)** :
```
Login → Vérification identifiants → Accueil
```

### **Après (avec charte)** :
```
Login → Vérification identifiants → Vérification charte
  ├─ ✅ Acceptée → Accueil
  └─ ❌ Pas acceptée → Page charte → Acceptation → Accueil
```

---

## 📄 Contenu de la charte

La charte couvre les points suivants :

1. **📋 Objet** : Définition des règles de confidentialité
2. **🔒 Collecte des données** : Types de données accessibles
3. **⚖️ Engagements** : 
   - Confidentialité
   - Usage professionnel
   - Sécurité des identifiants
   - Responsabilité
   - Traçabilité
4. **🛡️ Protection des données** : Conformité RGPD
5. **⚠️ Sanctions** : Conséquences en cas de manquement
6. **📞 Contact** : Délégué à la Protection des Données

---

## 🎨 Interface utilisateur

### **Design** :
- ✨ Effet glassmorphism (verre dépoli)
- 🖼️ Images de fond en rotation (10 secondes)
- 🕐 Horloge temps réel en haut à gauche
- © Copyright "Soro Lassina W." en bas à droite
- 📜 Contenu scrollable avec scrollbar personnalisée
- ✅ Checkbox obligatoire + bouton désactivé jusqu'à acceptation

### **Responsive** :
- 📱 S'adapte aux petits écrans
- 💻 Optimisé pour desktop et mobile

---

## 🔧 Configuration avancée

### **Désactiver la charte temporairement** :

Dans `.env` :
```
PRIVACY_POLICY_REQUIRED=False
```

### **Forcer une nouvelle acceptation** :

1. Changer la version dans `config.py` :
```python
PRIVACY_POLICY_VERSION = "2.0"
```

2. Les utilisateurs ayant accepté la v1.0 devront réaccepter la v2.0

### **Personnaliser le délai d'expiration** :

Dans `auth.py` (ligne 84) :
```python
max_age=600,  # 10 minutes (600 secondes)
```

---

## 📈 Suivi et Analytics

### **Vérifier l'acceptation des utilisateurs** :

```sql
SELECT 
    full_name,
    email,
    privacy_policy_accepted,
    privacy_policy_accepted_at,
    privacy_policy_version
FROM "user"
ORDER BY privacy_policy_accepted_at DESC;
```

### **Utilisateurs n'ayant pas encore accepté** :

```sql
SELECT full_name, email, created_at
FROM "user"
WHERE privacy_policy_accepted = FALSE;
```

### **Taux d'acceptation** :

```sql
SELECT 
    COUNT(*) FILTER (WHERE privacy_policy_accepted = TRUE) * 100.0 / COUNT(*) AS taux_acceptation,
    COUNT(*) FILTER (WHERE privacy_policy_accepted = TRUE) AS acceptations,
    COUNT(*) AS total_users
FROM "user";
```

---

## 🧪 Tests

### **Tester le flux complet** :

1. Créer un nouvel utilisateur
2. Se connecter avec ses identifiants
3. Vérifier la redirection vers `/privacy-policy`
4. Tester l'acceptation et la redirection vers l'accueil
5. Vérifier qu'une deuxième connexion ne demande pas la charte

### **Tester avec un utilisateur existant** :

```sql
UPDATE "user" 
SET privacy_policy_accepted = FALSE, 
    privacy_policy_accepted_at = NULL,
    privacy_policy_version = NULL
WHERE email = 'test@example.com';
```

---

## 🔍 Logs

Les logs de la charte sont préfixés par :
- 📋 : Affichage de la charte
- ✅ : Acceptation réussie
- ⚠️ : Refus ou session invalide

**Exemples** :
```
📋 Redirection vers charte de confidentialité pour admin@mppeep.cd
📋 Affichage de la charte pour admin@mppeep.cd
✅ Charte acceptée par admin@mppeep.cd (version 1.0)
```

---

## 🛡️ Sécurité

### **Mesures de protection** :

1. ✅ Session temporaire (10 min) pour l'affichage de la charte
2. ✅ Vérification de la session avant acceptation
3. ✅ Redirection automatique si déjà acceptée
4. ✅ Traçabilité complète (date, version, utilisateur)
5. ✅ Log de toutes les actions dans l'historique

### **Prévention des contournements** :

- Impossible d'accéder à l'application sans accepter
- Redirection automatique vers la charte si non acceptée
- Session expirée = retour au login

---

## 📞 Support

Pour toute question concernant la charte de confidentialité :

- **Développeur** : Soro Lassina W.
- **Version** : 1.0
- **Date d'implémentation** : Octobre 2024

---

## ✅ Checklist de déploiement

- [ ] Exécuter le script de migration (`add_privacy_policy_fields.py`)
- [ ] Vérifier la configuration (`.env`)
- [ ] Tester avec un utilisateur de test
- [ ] Informer les utilisateurs du nouveau processus
- [ ] Surveiller les logs pour détecter d'éventuels problèmes
- [ ] Documenter le processus auprès de l'équipe

---

**🎉 La charte de confidentialité est maintenant opérationnelle !**

