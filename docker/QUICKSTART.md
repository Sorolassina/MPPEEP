# 🚀 Docker Quick Start (5 Minutes)

## ⚡ Démarrage Ultra-Rapide

```bash
# 1. Copier le fichier d'environnement
cp docker/env.docker.example .env

# 2. Démarrer l'application
docker-compose up -d

# 3. Voir les logs
docker-compose logs -f

# 4. Ouvrir dans le navigateur
open http://localhost:8000
```

**✅ Application + PostgreSQL démarrés en 1 minute ! 🎉**

---

## 🔑 Connexion

**Application :**
- URL : http://localhost:8000
- Login : http://localhost:8000/api/v1/login
- Docs : http://localhost:8000/docs

**Identifiants admin (créés automatiquement) :**
- Email : `admin@mppeep.com`
- Password : `admin123`

⚠️ **Changez ce mot de passe en production !**

---

## 📋 Commandes Essentielles

```bash
# Démarrer
docker-compose up -d

# Arrêter
docker-compose down

# Logs
docker-compose logs -f

# Redémarrer
docker-compose restart

# Reconstruire
docker-compose up -d --build

# Shell dans l'app
docker-compose exec app bash

# Accéder à PostgreSQL
docker-compose exec db psql -U postgres -d mppeep
```

---

## 🛠️ Développement avec Hot-Reload

```bash
# Utiliser le docker-compose de dev
docker-compose -f docker-compose.dev.yml up -d

# Modifier le code dans app/
# → Changements détectés automatiquement ✅
# → Application redémarre ✅
```

---

## 🗄️ Accéder à pgAdmin (Interface Web DB)

```bash
# Démarrer avec pgAdmin
docker-compose --profile tools up -d

# Ouvrir
open http://localhost:5050

# Login
Email: admin@mppeep.com
Password: admin

# Ajouter serveur :
Host: db
Port: 5432
User: postgres
Password: (votre POSTGRES_PASSWORD du .env)
```

---

## 🔄 Backup et Restore

### Backup

```bash
# Backup manuel
docker-compose exec db pg_dump -U postgres mppeep > backup.sql

# Ou avec le script
bash docker/scripts/docker-backup.sh
```

---

### Restore

```bash
# Restore depuis un fichier
docker-compose exec -T db psql -U postgres mppeep < backup.sql
```

---

## 🐛 Problèmes Courants

### Port 8000 déjà utilisé

```bash
# Changer dans .env
APP_PORT=8001

# Redémarrer
docker-compose up -d
```

---

### L'app ne démarre pas

```bash
# Voir les logs d'erreur
docker-compose logs app

# Vérifier que la DB est prête
docker-compose ps db
```

---

### Reconstruire complètement

```bash
# Tout arrêter
docker-compose down -v

# Reconstruire
docker-compose up -d --build
```

---

## 📖 Documentation Complète

Voir `docker/README.md` pour :
- Configuration détaillée
- Tous les cas d'usage
- Optimisations
- Sécurité
- Troubleshooting complet

---

**🐳 Votre application Docker est prête ! 🚀**

