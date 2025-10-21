# ☁️ Déploiement MPPEEP avec Cloudflare Tunnel

## 📋 Vue d'Ensemble

Votre application MPPEEP Dashboard est déployée derrière **Cloudflare Tunnel**, ce qui signifie :
- ✅ Pas besoin de Nginx (Cloudflare fait le reverse proxy)
- ✅ SSL/HTTPS automatique (certificat Cloudflare)
- ✅ Protection DDoS incluse
- ✅ CDN global pour les fichiers statiques
- ✅ Zero Trust Access (pas de ports ouverts publiquement)

---

## 🌐 Architecture avec Cloudflare

```
┌─────────────────────────────────────────────────────────────┐
│                      UTILISATEUR                            │
│  https://mppeep.skpartners.consulting/mppeep/              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ DNS Resolution
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  ☁️  CLOUDFLARE EDGE NETWORK (CDN Global)                   │
├─────────────────────────────────────────────────────────────┤
│  Rôles :                                                    │
│  • DNS Management (skpartners.consulting)                  │
│  • SSL/TLS Termination (certificat auto)                   │
│  • DDoS Protection (WAF)                                    │
│  • CDN Cache global (200+ datacenters)                     │
│  • Rate Limiting & Bot Protection                           │
│  • Compression (Brotli/gzip)                               │
│  • Analytics & Logs                                         │
│  • Headers Injection (CF-*, X-Forwarded-*)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ ☁️ Cloudflare Tunnel (chiffré)
                     │ Connection SORTANTE depuis votre serveur
                     │ → Pas de port 80/443 ouvert publiquement
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  VOTRE SERVEUR                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │  cloudflared (Agent Tunnel)                        │   │
│  │  • Connexion permanente vers Cloudflare            │   │
│  │  • Proxy vers → http://localhost:9000              │   │
│  └────────────────────┬───────────────────────────────┘   │
│                       │                                    │
│                       ▼                                    │
│  ┌─────────────────────────────────────────────────┐      │
│  │  Docker: mppeep-app (FastAPI)                   │      │
│  │  Port 9000 (localhost uniquement)               │      │
│  └────┬──────────────────────┬─────────────────────┘      │
│       │                      │                             │
│       ▼                      ▼                             │
│  ┌──────────┐         ┌──────────┐                        │
│  │PostgreSQL│         │  Redis   │                        │
│  │ Port 5432│         │ Port 6379│                        │
│  └──────────┘         └──────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

**🔒 Sécurité** :
- Cloudflare Tunnel = **Connection SORTANTE** du serveur vers Cloudflare
- Aucun port public ouvert (80/443 fermés)
- Impossible d'attaquer directement le serveur
- Seul Cloudflare peut joindre l'application

---

## ⚙️ Configuration Actuelle

### ✅ 1. Docker Compose (docker-compose.prod.yml)

```yaml
services:
  app:
    ports:
      - "9000:9000"  # ← Port exposé sur localhost pour cloudflared
    environment:
      - DEBUG=False
      - ENABLE_CLOUDFLARE=True        # ← Middleware activé
      - ENABLE_FORWARD_PROTO=True     # ← Détecte HTTPS
      - ENABLE_HTTPS_REDIRECT=False   # ← Cloudflare gère HTTPS
      - ROOT_PATH=/mppeep             # ← Préfixe d'URL
      - CORS_ORIGINS=["https://mppeep.skpartners.consulting"]
```

### ✅ 2. Application (app/core/config.py)

```python
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "*.skpartners.consulting",  # ← Accepte tous les sous-domaines
    "skpartners.consulting"
]
```

### ✅ 3. Middleware Cloudflare

Le middleware capture automatiquement :
- `CF-Connecting-IP` : IP réelle du client
- `CF-Ray` : ID unique de la requête
- `CF-IPCountry` : Pays du client
- `CF-Visitor` : Protocole (http/https)

---

## 🔧 Configuration Cloudflare Tunnel

### Fichier config.yml

Selon votre message, vous avez déjà configuré :

```yaml
# ~/.cloudflared/config.yml
tunnel: <votre-tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # MPPEEP Dashboard
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  
  # Option A : Sous-domaine dédié
  - hostname: mppeep.skpartners.consulting
    service: http://localhost:9000
    originRequest:
      noTLSVerify: true  # Pas de SSL entre cloudflared et FastAPI
      connectTimeout: 30s
      httpHostHeader: mppeep.skpartners.consulting
  
  # Option B : Sous-chemin sur domaine principal
  # - hostname: skpartners.consulting
  #   path: /mppeep/*
  #   service: http://localhost:9000
  
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # Autres sous-applications
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - hostname: app2.skpartners.consulting
    service: http://localhost:8080
  
  - hostname: app3.skpartners.consulting
    service: http://localhost:3000
  
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # Catch-all (OBLIGATOIRE - doit être en dernier)
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - service: http_status:404
```

### Démarrage du Tunnel

```bash
# Vérifier que le tunnel tourne
sudo systemctl status cloudflared

# OU si lancé manuellement
cloudflared tunnel run <tunnel-name>

# Vérifier les logs
sudo journalctl -u cloudflared -f
```

---

## 🌍 URLs d'Accès

### Option A : Sous-domaine Dédié (RECOMMANDÉ)

Si configuré avec `hostname: mppeep.skpartners.consulting` :

```
✅ Page de connexion : https://mppeep.skpartners.consulting/mppeep/
✅ Accueil : https://mppeep.skpartners.consulting/mppeep/accueil
✅ Documentation API : https://mppeep.skpartners.consulting/mppeep/docs
✅ Health Check : https://mppeep.skpartners.consulting/mppeep/api/v1/health
```

**Note** : Le `/mppeep` est nécessaire car `ROOT_PATH=/mppeep` (ligne 54 docker-compose)

**Pour supprimer `/mppeep` de l'URL** :
```yaml
# docker-compose.prod.yml
- ROOT_PATH=  # Vide !
```

Alors les URLs deviennent :
```
✅ https://mppeep.skpartners.consulting/
✅ https://mppeep.skpartners.consulting/login
✅ https://mppeep.skpartners.consulting/docs
```

### Option B : Sous-chemin

Si configuré avec `path: /mppeep/*` sur `skpartners.consulting` :

```
✅ https://skpartners.consulting/mppeep/
✅ https://skpartners.consulting/mppeep/login
✅ https://skpartners.consulting/mppeep/docs
```

**Dans ce cas, `ROOT_PATH=/mppeep` est obligatoire** (déjà configuré ✅)

---

## 🔍 Diagnostic

### Vérifier que tout fonctionne

#### 1. Test Local (avant Cloudflare)

```bash
# Démarrer les containers
docker-compose -f docker-compose.prod.yml up -d

# Tester en local
curl http://localhost:9000/mppeep/api/v1/health

# Doit retourner :
# {"status": "healthy", ...}
```

#### 2. Test via Cloudflare

```bash
# Depuis n'importe où dans le monde
curl https://mppeep.skpartners.consulting/mppeep/api/v1/health

# Doit retourner :
# {"status": "healthy", ...}
```

#### 3. Vérifier les Headers Cloudflare

```bash
# Voir les headers reçus par FastAPI
docker logs mppeep-app | grep "Cloudflare Ray"

# Doit afficher :
# ☁️  Cloudflare Ray: 8d3f2e1a9b7c5d4f-CDG | Country: CM | IP: 197.234.XXX.XX
```

---

## 🚀 Déploiement Complet

### Étape 1 : Préparer le Code

```bash
# 1. S'assurer que le code est à jour
cd ~/mppeep

# 2. Vérifier la configuration
cat docker-compose.prod.yml | grep -A 10 "environment:"

# Doit montrer :
#   - ENABLE_CLOUDFLARE=True
#   - ROOT_PATH=/mppeep
#   - CORS_ORIGINS=["https://mppeep.skpartners.consulting"]
```

### Étape 2 : Builder l'Image Docker

```bash
# Builder l'image avec le nouveau code
docker-compose -f docker-compose.prod.yml build --no-cache

# Vérifier que l'image est créée
docker images | grep mppeep
```

### Étape 3 : Démarrer les Containers

```bash
# Démarrer tous les services
docker-compose -f docker-compose.prod.yml up -d

# Vérifier le statut
docker-compose -f docker-compose.prod.yml ps

# Voir les logs
docker-compose -f docker-compose.prod.yml logs -f app
```

### Étape 4 : Vérifier Cloudflare Tunnel

```bash
# Statut du tunnel
sudo systemctl status cloudflared

# Logs du tunnel
sudo journalctl -u cloudflared -f

# Doit afficher :
# Connection established with Cloudflare
# Registered tunnel connection
# Serving tunnel mppeep -> http://localhost:9000
```

### Étape 5 : Test de Connexion

```bash
# Test local
curl http://localhost:9000/mppeep/api/v1/health

# Test via Cloudflare
curl https://mppeep.skpartners.consulting/mppeep/api/v1/health

# Test de la page de connexion
curl -I https://mppeep.skpartners.consulting/mppeep/login

# Doit retourner HTTP 200
```

---

## 📊 Comparaison : Avec vs Sans Cloudflare

### ❌ Sans Cloudflare (Nginx classique)

```
Client → Internet → Votre IP Publique (exposée) → Nginx:80/443 → FastAPI:9000
```

**Inconvénients** :
- ❌ IP publique exposée (risque d'attaque)
- ❌ Ports 80/443 ouverts publiquement
- ❌ Gestion manuelle des certificats SSL
- ❌ Pas de protection DDoS
- ❌ Pas de CDN (lent depuis l'étranger)
- ❌ Un seul serveur (pas de redondance)

### ✅ Avec Cloudflare Tunnel

```
Client → Cloudflare Edge (200+ DC) → Tunnel Chiffré → localhost:9000
```

**Avantages** :
- ✅ **IP serveur cachée** (pas d'attaque directe possible)
- ✅ **Aucun port public ouvert** (firewall fermé)
- ✅ **SSL automatique** (certificat Cloudflare)
- ✅ **Protection DDoS** (Cloudflare filtre)
- ✅ **CDN global** (rapide partout dans le monde)
- ✅ **Analytics** (trafic, attaques bloquées)
- ✅ **Zero Trust** (policies d'accès avancées)

---

## 🔑 Configuration Cloudflare Tunnel

### Votre Configuration Actuelle

Selon votre setup, vous avez :

```yaml
# ~/.cloudflared/config.yml (sur votre serveur)

tunnel: <votre-tunnel-id>
credentials-file: ~/.cloudflared/<tunnel-id>.json

ingress:
  # MPPEEP Dashboard
  - hostname: mppeep.skpartners.consulting
    service: http://localhost:9000
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
      httpHostHeader: mppeep.skpartners.consulting
  
  # Autres sous-applications...
  - hostname: app2.skpartners.consulting
    service: http://localhost:8080
  
  # Catch-all (OBLIGATOIRE)
  - service: http_status:404
```

### Options de Routing

Vous avez **2 options** pour router le trafic :

#### Option 1 : Sous-domaine Dédié (Actuel)

**Configuration Cloudflare** :
```yaml
- hostname: mppeep.skpartners.consulting
  service: http://localhost:9000
```

**URLs résultantes** :
```
https://mppeep.skpartners.consulting/mppeep/
                                      ⬆️
                              ROOT_PATH configuré dans FastAPI
```

**Avantages** :
- ✅ Isolation claire (chaque sous-app a son sous-domaine)
- ✅ Certificat SSL dédié
- ✅ Analytics séparées
- ✅ Peut avoir des policies d'accès différentes

#### Option 2 : Sous-chemin

**Configuration Cloudflare** :
```yaml
- hostname: skpartners.consulting
  path: /mppeep/*
  service: http://localhost:9000
```

**URLs résultantes** :
```
https://skpartners.consulting/mppeep/
```

**Avantages** :
- ✅ Tout sous un domaine principal
- ✅ Pas de sous-domaines multiples à gérer
- ✅ Partage du certificat SSL

---

## 🎯 Configuration Recommandée pour Vous

Avec **sous-domaine dédié** : `mppeep.skpartners.consulting`

### 1. Configuration Docker (✅ Déjà fait)

```yaml
# docker-compose.prod.yml
environment:
  - ROOT_PATH=/mppeep                    # ← Préfixe d'URL
  - ENABLE_CLOUDFLARE=True               # ← Middleware activé
  - ENABLE_FORWARD_PROTO=True            # ← Détecte HTTPS
  - ENABLE_HTTPS_REDIRECT=False          # ← Cloudflare gère
  - CORS_ORIGINS=["https://mppeep.skpartners.consulting"]

ports:
  - "9000:9000"  # ← cloudflared se connecte ici
```

### 2. DNS Cloudflare

Dans le dashboard Cloudflare :

```
Type    Nom      Valeur                    Proxy   TTL
─────────────────────────────────────────────────────────
CNAME   mppeep   <tunnel-id>.cfargotunnel.com   ☁️     Auto
```

**☁️ = Proxied (obligatoire pour Tunnel)**

### 3. URL Finale

Votre application sera accessible à :

```
🌐 https://mppeep.skpartners.consulting/mppeep/

📧 Identifiants par défaut :
   Email    : admin@mppeep.com
   Password : admin123
```

---

## 🔄 Workflow de Requête Complète

```
1. Utilisateur tape : https://mppeep.skpartners.consulting/mppeep/
   │
   ▼
2. DNS Resolution
   ├─ mppeep.skpartners.consulting → Cloudflare IP (104.21.XXX.XXX)
   └─ Connexion à Cloudflare Edge (datacenter le plus proche)
   │
   ▼
3. Cloudflare Edge Network
   ├─ WAF : Vérification (bot ? attaque ?)
   ├─ SSL : Déchiffrement HTTPS
   ├─ Cache : Vérifie si réponse en cache
   │  └─ Cache MISS (requête dynamique)
   ├─ Headers ajoutés :
   │  ├─ CF-Connecting-IP: 197.234.XXX.XX (IP réelle)
   │  ├─ CF-Ray: 8d3f2e1a9b7c5d4f-CDG
   │  ├─ CF-IPCountry: CM
   │  └─ X-Forwarded-Proto: https
   └─ Envoie via Tunnel Chiffré
   │
   ▼
4. Cloudflare Tunnel (cloudflared sur votre serveur)
   ├─ Reçoit la requête via tunnel
   ├─ Déchiffre
   └─ Proxy local → http://localhost:9000/mppeep/
   │
   ▼
5. FastAPI (Container mppeep-app)
   ├─ CloudflareMiddleware : Capture CF-* headers
   │  └─ request.state.cf_ray = "8d3f2e1a9b7c5d4f-CDG"
   │  └─ request.state.client_ip = "197.234.XXX.XX"
   │
   ├─ Vérifie la session
   │  └─ Redis.get('session:xyz') → ⚡ 1ms
   │
   ├─ Traite la requête
   │  └─ Requête PostgreSQL si nécessaire
   │
   └─ Retourne HTML
   │
   ▼
6. cloudflared → Cloudflare (via tunnel)
   │
   ▼
7. Cloudflare Edge
   ├─ Compression (Brotli/gzip)
   ├─ Cache (selon headers)
   ├─ Headers de sécurité
   └─ Envoie au client (HTTPS)
   │
   ▼
8. Client reçoit la page ✅
```

**Temps total** : ~200-400ms (avec Cloudflare CDN)

---

## 📊 Avantages de Votre Configuration

| Aspect | Sans Cloudflare | Avec Cloudflare Tunnel |
|--------|----------------|------------------------|
| **Sécurité** | IP exposée | ✅ IP cachée |
| **Ports ouverts** | 80, 443 | ✅ Aucun (tunnel sortant) |
| **SSL** | Certificat à gérer | ✅ Auto (Cloudflare) |
| **DDoS** | Serveur vulnérable | ✅ Cloudflare bloque |
| **CDN** | Lent depuis l'étranger | ✅ 200+ datacenters |
| **Firewall** | Règles complexes | ✅ WAF Cloudflare |
| **Analytics** | À configurer | ✅ Inclus (gratuit) |
| **Coût** | Serveur + SSL | ✅ Gratuit (Cloudflare Free) |

---

## 🛠️ Commandes de Déploiement

### Déploiement Initial

```bash
# 1. Arrêter les containers (si tournent)
docker-compose -f docker-compose.prod.yml down

# 2. Builder l'image avec la nouvelle config
docker-compose -f docker-compose.prod.yml build --no-cache

# 3. Démarrer les containers
docker-compose -f docker-compose.prod.yml up -d

# 4. Vérifier que FastAPI écoute sur 9000
netstat -tlnp | grep 9000
# Doit montrer : 0.0.0.0:9000

# 5. Test local
curl http://localhost:9000/mppeep/api/v1/health

# 6. Redémarrer cloudflared (si nécessaire)
sudo systemctl restart cloudflared

# 7. Test via Cloudflare
curl https://mppeep.skpartners.consulting/mppeep/api/v1/health

# ✅ Si ça marche → Ouvrir dans le navigateur
# https://mppeep.skpartners.consulting/mppeep/
```

### Via Makefile

```bash
# Rebuild complet
make docker-rebuild-prod

# Le port 9000 est maintenant exposé pour cloudflared ✅
```

---

## 🔍 Troubleshooting Cloudflare

### Erreur : 502 Bad Gateway

**Symptôme** : Cloudflare affiche "502 Bad Gateway"

**Causes possibles** :

#### 1. FastAPI ne tourne pas
```bash
docker ps | grep mppeep-app
# Si absent :
docker-compose -f docker-compose.prod.yml up -d
```

#### 2. Port 9000 non accessible
```bash
# Test depuis le serveur
curl http://localhost:9000/mppeep/api/v1/health

# Si échec → Vérifier les logs
docker logs mppeep-app
```

#### 3. cloudflared ne tourne pas
```bash
sudo systemctl status cloudflared

# Si arrêté :
sudo systemctl start cloudflared
sudo journalctl -u cloudflared -f
```

#### 4. Mauvaise configuration du tunnel
```bash
# Vérifier la config
cat ~/.cloudflared/config.yml

# Tester le tunnel
cloudflared tunnel info <tunnel-name>
```

### Erreur : 403 Forbidden / CORS Error

**Symptôme** : Navigateur affiche erreur CORS

**Solution** :
```yaml
# docker-compose.prod.yml - Vérifier CORS_ORIGINS
- CORS_ORIGINS=["https://mppeep.skpartners.consulting","https://skpartners.consulting"]
                  ⬆️ Votre domaine Cloudflare
```

Puis rebuild :
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up --build -d
```

### Erreur : 404 Not Found sur toutes les pages

**Symptôme** : Toutes les URLs retournent 404

**Cause** : Mauvais `ROOT_PATH`

**Vérification** :
```bash
# Voir la valeur actuelle
docker exec mppeep-app printenv | grep ROOT_PATH

# Si ROOT_PATH=/mppeep, les URLs doivent inclure /mppeep :
# ✅ https://mppeep.skpartners.consulting/mppeep/
# ❌ https://mppeep.skpartners.consulting/
```

---

## 📊 Monitoring

### Logs Cloudflare

Dans le dashboard Cloudflare :
```
Analytics → Traffic → mppeep.skpartners.consulting
```

Vous verrez :
- Requêtes par seconde
- Bande passante
- Attaques bloquées
- Pays d'origine
- Status codes (200, 404, 502...)

### Logs FastAPI

```bash
# Voir les logs en temps réel
docker logs -f mppeep-app

# Filtrer les requêtes Cloudflare
docker logs mppeep-app | grep "Cloudflare Ray"

# Exemple de sortie :
# ☁️  Cloudflare Ray: 8d3f2e1a9b7c5d4f-CDG | Country: CM | IP: 197.234.123.45
```

### Métriques Docker

```bash
# Utilisation ressources
docker stats mppeep-app mppeep-db mppeep-redis

# Espace disque
docker system df

# Logs de tous les services
docker-compose -f docker-compose.prod.yml logs --tail=100
```

---

## 🎯 Configuration Optimale

### Dans docker-compose.prod.yml (✅ Déjà configuré)

```yaml
environment:
  - DEBUG=False                          # ← Production
  - ENABLE_CLOUDFLARE=True               # ← Capture CF-* headers
  - ENABLE_FORWARD_PROTO=True            # ← Détecte HTTPS
  - ENABLE_HTTPS_REDIRECT=False          # ← Cloudflare gère déjà
  - ROOT_PATH=/mppeep                    # ← Préfixe d'URL
  - CORS_ORIGINS=["https://mppeep.skpartners.consulting"]
  
ports:
  - "9000:9000"  # ← Pour cloudflared (localhost uniquement)
```

### Services Nécessaires

Avec Cloudflare Tunnel, votre stack devient :

```yaml
services:
  app:      # ✅ NÉCESSAIRE - Votre application
  db:       # ✅ NÉCESSAIRE - Base de données
  redis:    # ✅ RECOMMANDÉ - Cache & Sessions
  nginx:    # ❌ OPTIONNEL - Cloudflare le remplace
```

**Vous pouvez désactiver Nginx** (Cloudflare fait déjà le travail) :

```bash
# Commenter nginx dans docker-compose.prod.yml
# OU lancer seulement les services nécessaires :
docker-compose -f docker-compose.prod.yml up -d app db redis
```

---

## 🔐 Sécurité Renforcée

### Firewall Serveur

Avec Cloudflare Tunnel, vous pouvez **fermer tous les ports** :

```bash
# Bloquer tout le trafic entrant (sauf SSH)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp  # SSH uniquement
sudo ufw enable

# Vérifier
sudo ufw status

# Résultat :
# 22/tcp  ALLOW   Anywhere
# Tout le reste : DENY
```

**L'application reste accessible** via Cloudflare Tunnel (connection SORTANTE) !

### Zero Trust Access (Optionnel)

Cloudflare Tunnel permet d'ajouter une authentification **avant** d'accéder à l'app :

```
Utilisateur → Cloudflare Login (email/OTP) → MPPEEP Login
```

Configuration dans Cloudflare Dashboard :
```
Access → Applications → Add Application
  - Subdomain: mppeep
  - Domain: skpartners.consulting
  - Policies: Email ends with @skpartners.consulting
```

---

## 📚 Résumé

### ✅ Ce qui est déjà configuré

- [x] Middleware Cloudflare (`CloudflareMiddleware`)
- [x] ALLOWED_HOSTS avec `*.skpartners.consulting`
- [x] ENABLE_CLOUDFLARE=True dans docker-compose
- [x] ENABLE_FORWARD_PROTO=True (détecte HTTPS)
- [x] ENABLE_HTTPS_REDIRECT=False (Cloudflare gère)
- [x] ROOT_PATH=/mppeep configuré
- [x] Port 9000 exposé pour cloudflared
- [x] CORS configuré avec votre domaine

### 🚀 Pour Déployer

```bash
# 1. Rebuild l'image avec la config Cloudflare
make docker-rebuild-prod

# 2. Vérifier que cloudflared tourne
sudo systemctl status cloudflared

# 3. Tester
curl https://mppeep.skpartners.consulting/mppeep/

# 4. Ouvrir dans le navigateur
# https://mppeep.skpartners.consulting/mppeep/
```

### 🌐 URLs d'Accès

Avec votre configuration actuelle :

```
🔗 Page de connexion : https://mppeep.skpartners.consulting/mppeep/
🔗 Accueil : https://mppeep.skpartners.consulting/mppeep/accueil
🔗 Documentation API : https://mppeep.skpartners.consulting/mppeep/docs
🔗 Health Check : https://mppeep.skpartners.consulting/mppeep/api/v1/health

📧 Identifiants :
   Email    : admin@mppeep.com
   Password : admin123
```

---

## 💡 Option Alternative : Supprimer /mppeep de l'URL

Si vous voulez des URLs plus simples :

```
https://mppeep.skpartners.consulting/        au lieu de
https://mppeep.skpartners.consulting/mppeep/
```

**Modifiez simplement** :
```yaml
# docker-compose.prod.yml
- ROOT_PATH=  # Vide !
```

Puis rebuild. Les URLs deviennent :
```
✅ https://mppeep.skpartners.consulting/
✅ https://mppeep.skpartners.consulting/login
✅ https://mppeep.skpartners.consulting/docs
```

---

**Documentation créée le** : 2025-10-20  
**Version** : 1.0.0  
**Domaine** : mppeep.skpartners.consulting  
**Tunnel** : Cloudflare Tunnel (Zero Trust)
