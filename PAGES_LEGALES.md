# 📜 Pages Légales - Documentation

## 🎯 Vue d'ensemble

Le système MPPEEP Dashboard dispose de deux pages légales essentielles pour la conformité juridique et la protection des données.

---

## 📋 1. Conditions Générales d'Utilisation (CGU)

### **Accès :** 
- URL : `/api/v1/cgu`
- Lien footer : "CGU"

### **Contenu :**

#### **📋 Article 1 - Objet**
Définit l'objectif des CGU et le cadre d'utilisation du système.

#### **🔐 Article 2 - Accès au Système**
- Conditions d'accès réservé aux agents autorisés
- Gestion des identifiants personnels
- Processus d'activation des comptes

#### **✅ Article 3 - Obligations de l'Utilisateur**
- Usage professionnel exclusif
- Interdictions (usage personnel, divulgation de données, etc.)
- Obligations de confidentialité
- Mesures de sécurité à respecter

#### **🛡️ Article 4 - Protection des Données Personnelles**
- Conformité RGPD
- Types de données collectées
- Finalités du traitement
- Droits des utilisateurs (accès, rectification, effacement, etc.)

#### **📊 Article 5 - Traçabilité et Audit**
- Enregistrement de toutes les actions
- Conservation des journaux d'activité
- Possibilité d'audit

#### **⚖️ Article 6 - Responsabilités**
- Responsabilités du Ministère
- Responsabilités de l'utilisateur
- Limitations de responsabilité

#### **⚠️ Article 7 - Sanctions**
- Suspension de l'accès
- Sanctions disciplinaires
- Poursuites judiciaires possibles

#### **🔄 Article 8 - Modification des CGU**
Droit de modification et notification des utilisateurs.

#### **📞 Article 9 - Contact**
Coordonnées pour toute question.

#### **©️ Article 10 - Propriété Intellectuelle** ⭐
- **Propriété de Soro Lassina W.**
- Protection du code source et de l'architecture
- Interdiction de reproduction non autorisée
- Licence d'utilisation au Ministère
- **© 2025 Soro Lassina W. - Tous droits réservés**

#### **📅 Article 11 - Entrée en Vigueur**
Date d'application et version.

---

## 🔒 2. Charte de Confidentialité

### **Accès :**
- URL : `/api/v1/privacy-policy`
- Lien footer : "Charte de Confidentialité"
- **Obligatoire à la première connexion**

### **Contenu :**

#### **📋 Objet de la Charte**
Règles de confidentialité et protection des données.

#### **🔒 Collecte et Traitement des Données**
Types de données sensibles accessibles :
- Informations personnelles des agents
- Données budgétaires et financières
- Informations sur les entreprises publiques
- Documents administratifs confidentiels

#### **⚖️ Engagements de l'Utilisateur**
- Confidentialité absolue
- Usage professionnel uniquement
- Sécurité des identifiants
- Responsabilité personnelle
- Acceptation de la traçabilité

#### **🛡️ Protection des Données**
- Conformité RGPD et lois nationales
- Traitement licite et transparent
- Conservation limitée dans le temps
- Sécurité renforcée
- Respect des droits des utilisateurs

#### **⚠️ Sanctions**
Conséquences en cas de manquement :
- Sanctions disciplinaires
- Poursuites judiciaires possibles

#### **📞 Contact**
Délégué à la Protection des Données (DPO).

---

## 🔗 Intégration dans le Footer

Le footer de toutes les pages affiche désormais :

```html
<footer>
    <div class="footer-content">
        © 2025 MPPEEP Dashboard. Tous droits réservés.
        Développé par Soro Lassina W.
    </div>
    <div class="footer-links">
        [Contact] [CGU] [Charte de Confidentialité]
    </div>
</footer>
```

---

## 🎨 Design

Les deux pages utilisent le même design :
- ✅ Layout responsive
- ✅ Typographie claire et lisible
- ✅ Sections bien structurées
- ✅ Couleurs cohérentes avec le thème
- ✅ Navigation facile (retour à l'accueil)

---

## ⚖️ Conformité Juridique

### **RGPD**
✅ Mentions obligatoires présentes :
- Finalités du traitement
- Base légale
- Durée de conservation
- Droits des personnes
- Coordonnées du DPO

### **Propriété Intellectuelle**
✅ **Mentions de propriété :**
- Nom du développeur (Soro Lassina W.)
- Copyright © 2025
- Protection du code source
- Licence d'utilisation

### **Obligations légales**
✅ CGU conformes aux exigences :
- Identification du service
- Conditions d'accès
- Obligations des utilisateurs
- Responsabilités
- Droit applicable

---

## 🔐 Flux de Conformité

### **Première connexion :**
```
Login → Charte obligatoire → Acceptation → Accès
```

### **Connexions suivantes :**
```
Login → Accès direct (charte déjà acceptée)
```

### **Consultation des CGU :**
```
Footer "CGU" → Page CGU complète → Lecture libre
```

---

## 📊 Traçabilité

### **Acceptation de la charte :**
- ✅ Date et heure enregistrées
- ✅ Version acceptée stockée
- ✅ Utilisateur identifié
- ✅ Log dans l'historique d'activité

### **Consultation des CGU :**
- Pas d'acceptation requise
- Accès libre pour consultation
- Pas de traçabilité (consultation simple)

---

## 🛠️ Maintenance

### **Mise à jour des CGU :**

1. Modifier le fichier : `app/templates/legal/cgu.html`
2. Changer la version dans le template
3. Informer les utilisateurs si changements majeurs

### **Mise à jour de la Charte :**

1. Modifier : `app/templates/auth/privacy_policy.html`
2. Changer la version dans `config.py` :
   ```python
   PRIVACY_POLICY_VERSION = "2.0"
   ```
3. **Tous les utilisateurs devront réaccepter** la nouvelle version

---

## 📝 Personnalisation

### **Ajouter des sections aux CGU :**

Éditer `app/templates/legal/cgu.html` :

```html
<section class="legal-section">
    <h2>🆕 Article X - Nouveau Sujet</h2>
    <p>Contenu de la nouvelle section...</p>
</section>
```

### **Modifier les coordonnées de contact :**

Modifier l'Article 9 avec les bonnes coordonnées :
- Email du service informatique
- Nom et contact du DPO
- Téléphone de l'administration

---

## ✅ Checklist de Conformité

- [x] CGU créées et accessibles
- [x] Charte de confidentialité créée
- [x] Propriété intellectuelle mentionnée (Soro Lassina W.)
- [x] Conformité RGPD assurée
- [x] Droits des utilisateurs détaillés
- [x] Sanctions clairement définies
- [x] Liens dans le footer fonctionnels
- [x] Traçabilité de l'acceptation de la charte
- [x] Design professionnel et responsive

---

## 📞 Support

Pour toute question juridique concernant ces documents :
- **Développeur** : Soro Lassina W.
- **Contact administratif** : Service juridique du Ministère
- **DPO** : Délégué à la Protection des Données

---

**Les pages légales sont maintenant complètes et conformes ! 📜✅**

