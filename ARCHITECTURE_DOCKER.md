# 🏗️ Architecture Docker - MPPEEP Dashboard

## 📋 Vue d'Ensemble

Votre application MPPEEP Dashboard utilise une architecture **microservices** avec 3 services Docker derrière **Cloudflare Tunnel** :

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERNET / UTILISATEUR                   │
│     https://skpartners.consulting/mppeep/           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │  ☁️  CLOUDFLARE EDGE NETWORK       │
        │  • SSL/TLS                         │
        │  • DDoS Protection                 │
        │  • CDN Global                      │
        │  • WAF (Firewall)                  │
        └────────┬───────────────────────────┘
                 │
                 │ Cloudflare Tunnel (chiffré)
                 │ Connection SORTANTE (pas de port ouvert)
                 ▼
        ┌────────────────────────────────────┐
        │  cloudflared (Tunnel Agent)        │
        │  Proxy → localhost:9000            │
        └────────┬───────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │  FASTAPI       │
        │  (Port 9000)   │
        │  🐍 App Python │
        └────┬─────┬─────┘
             │     │
    Données  │     │ Cache/Sessions
             │     │
             ▼     ▼
    ┌────────┐   ┌────────┐
    │ POSTGRES│   │ REDIS  │
    │ :5432   │   │ :6379  │
    │ 💾 BDD  │   │ ⚡Cache │
    └─────────┘   └────────┘
```

**Note** : Nginx est désactivé car Cloudflare Tunnel remplace toutes ses fonctions (reverse proxy, SSL, compression, CDN).

---

## 🌐 NGINX - Le Reverse Proxy (⚠️ DÉSACTIVÉ - Cloudflare Utilisé)

> **Note** : Dans votre configuration actuelle, Nginx est **désactivé** car vous utilisez **Cloudflare Tunnel** qui remplace toutes ses fonctions. Cette section est conservée pour référence.

### 🎯 Rôle Principal
**Serveur web qui sert d'intermédiaire entre Internet et votre application FastAPI**

**⚠️ Remplacé par Cloudflare dans votre déploiement** :
- Cloudflare fait le reverse proxy
- Cloudflare gère SSL/TLS
- Cloudflare compresse les réponses
- Cloudflare sert de CDN pour les fichiers statiques

### 📋 Responsabilités

#### 1. **Reverse Proxy** 🔄
```nginx
location / {
    proxy_pass http://mppeep_app;  # ← Redirige vers app:9000
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

**Flux** :
```
Client → Nginx:80 → FastAPI:9000 → Nginx:80 → Client
```

**Avantages** :
- ✅ Masque l'application réelle (sécurité)
- ✅ Point d'entrée unique
- ✅ Peut changer l'app backend sans impacter les clients

#### 2. **Serveur de Fichiers Statiques** 📁
```nginx
location /static/ {
    alias /usr/share/nginx/html/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

**Pourquoi Nginx et pas FastAPI ?**

| Aspect | Nginx | FastAPI/Python |
|--------|-------|----------------|
| **Vitesse** | ⚡⚡⚡ ~0.1ms | ⚡ ~5-10ms |
| **Concurrence** | 10,000+ req/s | ~100-500 req/s |
| **CPU** | Très faible | Élevé |
| **Mémoire** | ~2MB | ~50-100MB par worker |
| **Optimisé pour** | I/O fichiers | Logique métier |

**Résultat** : Nginx sert les fichiers **50x plus vite** que Python !

#### 3. **SSL/TLS (HTTPS)** 🔒
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256...';
}
```

**Avantages** :
- ✅ Chiffrement des données
- ✅ Certificats SSL gérés par Nginx (pas Python)
- ✅ Redirection automatique HTTP → HTTPS
- ✅ HSTS (HTTP Strict Transport Security)

#### 4. **Compression** 📦
```nginx
gzip on;
gzip_comp_level 6;
gzip_types text/css application/javascript application/json;
```

**Impact** :
```
Fichier CSS : 150 KB → 25 KB (compression 83%)
Fichier JS  : 300 KB → 60 KB (compression 80%)
JSON API    : 50 KB  → 8 KB  (compression 84%)
```

**Économie de bande passante** : ~80% !

#### 5. **Load Balancing** ⚖️
```nginx
upstream mppeep_app {
    server app1:9000 weight=3;  # Instance 1 (prioritaire)
    server app2:9000 weight=2;  # Instance 2
    server app3:9000 weight=1;  # Instance 3 (backup)
}
```

**Utilité** :
- Haute disponibilité
- Répartition de charge
- Zero-downtime deployment

#### 6. **Sécurité** 🛡️
```nginx
# Headers de sécurité
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000";
add_header Referrer-Policy "strict-origin-when-cross-origin";

# Protection DDoS basique
limit_req_zone $binary_remote_addr zone=one:10m rate=10r/s;
limit_req zone=one burst=20 nodelay;
```

**Protection contre** :
- Clickjacking (X-Frame-Options)
- MIME sniffing (X-Content-Type-Options)
- XSS (X-XSS-Protection)
- DDoS basique (rate limiting)

#### 7. **Cache HTTP** 🗄️
```nginx
location /static/ {
    expires 30d;                          # Cache 30 jours
    add_header Cache-Control "public";
}

location /api/ {
    expires -1;                           # Pas de cache
    add_header Cache-Control "no-cache";
}
```

---

## ⚡ REDIS - Le Cache Ultra-Rapide

### 🎯 Rôle Principal
**Base de données en mémoire (RAM) pour le cache et les données temporaires**

### 📋 Responsabilités

#### 1. **Cache des Données** 💾

**Exemple : Cache des statistiques du dashboard**
```python
import redis
import json
from datetime import timedelta

r = redis.Redis(host='redis', port=6379, decode_responses=True)

def get_dashboard_stats(user_id):
    cache_key = f'dashboard_stats:{user_id}'
    
    # 1. Chercher dans Redis
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)  # ⚡ Retour immédiat (1ms)
    
    # 2. Pas de cache → Calculer (requête PostgreSQL)
    stats = expensive_query_to_postgres()  # 🐌 Lent (200ms)
    
    # 3. Mettre en cache pour 5 minutes
    r.setex(cache_key, 300, json.dumps(stats))
    
    return stats
```

**Performance** :
```
Sans Redis : 200ms par requête
Avec Redis : 1ms (requête cachée) + 200ms (1ère fois seulement)

Pour 1000 utilisateurs :
- Sans cache : 200,000ms = 200 secondes
- Avec cache  : 1,000ms + 200ms = 1.2 secondes

Gain : 166x plus rapide ! 🚀
```

#### 2. **Sessions Utilisateur** 🎫

**Stockage des sessions côté serveur**
```python
def create_session(user_id, data):
    session_id = generate_uuid()
    session_data = {
        'user_id': user_id,
        'email': data['email'],
        'logged_in_at': datetime.now().isoformat(),
        'ip_address': request.remote_addr
    }
    
    # Stocker dans Redis avec expiration 7 jours
    r.setex(
        f'session:{session_id}',
        7 * 24 * 60 * 60,  # 7 jours
        json.dumps(session_data)
    )
    
    return session_id  # Cookie côté client

def verify_session(session_id):
    session_data = r.get(f'session:{session_id}')
    if session_data:
        return json.loads(session_data)  # ✅ Session valide
    return None  # ❌ Session expirée ou invalide
```

**Avantages** :
- ✅ **Sécurité** : Données sensibles côté serveur, pas dans le cookie
- ✅ **Révocation immédiate** : `r.delete(f'session:{id}')` déconnecte l'utilisateur
- ✅ **Expiration automatique** : Redis supprime les sessions expirées
- ✅ **Scalable** : Plusieurs serveurs FastAPI partagent les sessions

#### 3. **Rate Limiting (Anti-Spam)** 🚦

**Limiter les tentatives de connexion**
```python
def check_login_attempts(ip_address):
    key = f'login_attempts:{ip_address}'
    
    # Incrémenter le compteur
    attempts = r.incr(key)
    
    # Première tentative : définir expiration 15 min
    if attempts == 1:
        r.expire(key, 15 * 60)
    
    # Plus de 5 tentatives ?
    if attempts > 5:
        raise HTTPException(
            status_code=429,
            detail="Trop de tentatives. Réessayez dans 15 minutes."
        )
    
    return attempts
```

**Protection** :
- Anti-brute force sur le login
- Anti-spam sur l'API
- Limitation par IP ou par utilisateur

#### 4. **Compteurs et Statistiques Temps Réel** 📊

**Tracking des pages vues**
```python
# Incrémenter un compteur
r.incr('page_views:dashboard')
r.incr(f'user_actions:{user_id}:today')

# Top pages visitées (sorted set)
r.zincrby('popular_pages', 1, '/dashboard')

# Récupérer le top 10
top_pages = r.zrevrange('popular_pages', 0, 9, withscores=True)
# → [('/dashboard', 1543), ('/rh', 892), ...]
```

#### 5. **Cache de Requêtes Lourdes** 🐌→⚡

**Exemple : Liste du personnel avec calculs**
```python
def get_personnel_with_stats():
    cache_key = 'personnel_list_with_stats'
    
    # Chercher dans Redis
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Requête lourde (joins multiples, calculs)
    personnel = db.execute("""
        SELECT p.*, 
               COUNT(a.id) as absences_count,
               AVG(e.note) as avg_evaluation
        FROM personnel p
        LEFT JOIN absences a ON p.id = a.personnel_id
        LEFT JOIN evaluations e ON p.id = e.personnel_id
        GROUP BY p.id
    """)  # 🐌 500ms
    
    # Mettre en cache 10 minutes
    r.setex(cache_key, 600, json.dumps(personnel))
    
    return personnel
```

#### 6. **Queues (Files d'Attente)** 📮

**Exemple : Envoi d'emails en arrière-plan**
```python
# Ajouter à la queue
def send_email_async(to, subject, body):
    email_data = {
        'to': to,
        'subject': subject,
        'body': body,
        'created_at': datetime.now().isoformat()
    }
    r.lpush('email_queue', json.dumps(email_data))

# Worker qui traite la queue (processus séparé)
while True:
    # Attendre et récupérer un email
    email_json = r.brpop('email_queue', timeout=5)
    if email_json:
        email_data = json.loads(email_json[1])
        send_email(email_data)  # Envoi réel
```

**Utilité** :
- Tâches asynchrones
- Pas de blocage de l'utilisateur
- Retry automatique en cas d'erreur

#### 7. **Verrous Distribués** 🔐

**Éviter les actions simultanées**
```python
def process_salary_with_lock(personnel_id):
    lock_key = f'salary_processing:{personnel_id}'
    
    # Essayer d'acquérir le verrou (5 minutes max)
    lock = r.set(lock_key, 'locked', nx=True, ex=300)
    
    if not lock:
        raise Exception("Un autre processus traite déjà ce salaire")
    
    try:
        # Traiter le salaire
        process_salary(personnel_id)
    finally:
        # Libérer le verrou
        r.delete(lock_key)
```

---

## 📊 Comparaison des Services

### Configuration Actuelle (avec Cloudflare Tunnel)

| Service | Rôle | Type de Données | Vitesse | Persistance | Taille | Statut |
|---------|------|----------------|---------|-------------|--------|--------|
| **Cloudflare** | Proxy, SSL, CDN | Aucune | ⚡⚡⚡ <1ms | ❌ Non | Cloud | ✅ Actif |
| **FastAPI** | Logique métier | Temporaires | ⚡⚡ 5-50ms | ❌ Non | ~300MB | ✅ Actif |
| **Redis** | Cache, Sessions | Temporaires | ⚡⚡⚡ 1ms | ⚠️ Optionnelle | ~256MB RAM | ✅ Actif |
| **PostgreSQL** | Base de données | Permanentes | ⚡ 10-500ms | ✅ Oui | ~100MB + données | ✅ Actif |
| **Nginx** | Proxy, Statiques | Aucune | ⚡⚡⚡ <1ms | ❌ Non | ~20MB | ❌ Désactivé |

---

## 🔄 Flux de Requêtes Typiques

### Scénario 1 : Chargement d'une Page HTML

```
1. Utilisateur → https://mppeep.skpartners.consulting/mppeep/dashboard
   │
   ▼
2. CLOUDFLARE EDGE (CDN le plus proche)
   ├─ WAF : Vérifie (bot ? attaque ?)
   ├─ SSL : Déchiffrement HTTPS
   ├─ Cache : Vérifie si page en cache
   │  └─ Cache MISS (page dynamique)
   ├─ Headers ajoutés :
   │  ├─ CF-Connecting-IP: 197.234.XXX.XX
   │  ├─ CF-Ray: 8d3f2e1a9b7c5d4f-CDG
   │  └─ X-Forwarded-Proto: https
   └─ Envoie via Tunnel → localhost:9000
   │
   ▼
3. cloudflared (Tunnel Agent sur serveur)
   └─ Proxy local → http://localhost:9000/mppeep/dashboard
   │
   ▼
4. FASTAPI (Port 9000)
   ├─ CloudflareMiddleware : Capture CF-* headers
   │  └─ request.state.cf_ray = "8d3f2e1a9b7c5d4f-CDG"
   │
   ├─ Vérifie la session
   │  └─ Redis.get('session:abc123') → ⚡ 1ms
   │     ✅ Session valide
   │
   ├─ Récupère les stats du dashboard
   │  └─ Redis.get('dashboard_stats') → ⚡ 1ms
   │     ✅ Cache valide (pas de requête PostgreSQL !)
   │
   └─ Rendu du template HTML
   │
   ▼
5. cloudflared → CLOUDFLARE (via tunnel)
   │
   ▼
6. CLOUDFLARE traite la réponse
   ├─ Compression Brotli (150KB → 25KB)
   ├─ Headers Cache-Control
   ├─ Headers de sécurité
   └─ Envoie au client (HTTPS)
   │
   ▼
7. Client reçoit la page → ⏱️ 200-300ms total

8. Client demande les fichiers statiques
   └─ GET /mppeep/static/css/style.css
      │
      ▼
   CLOUDFLARE CDN (cache edge)
   └─ Fichier déjà en cache → ⚡ <10ms
```

**Temps total** : ~200-300ms (rapide partout dans le monde grâce au CDN !)

### Scénario 2 : Requête API (Création d'un Personnel)

```
1. Client → POST /mppeep/api/v1/personnel
   │
   ▼
2. CLOUDFLARE
   ├─ WAF : Vérifie la requête
   ├─ Rate Limiting : Vérifie le quota
   └─ Tunnel → localhost:9000
   │
   ▼
3. cloudflared → FASTAPI
   │
   ▼
4. FASTAPI
   ├─ Validation des données (Pydantic)
   ├─ Vérification des permissions
   │
   ▼
5. POSTGRESQL
   ├─ INSERT INTO personnel VALUES (...)
   └─ COMMIT → ⏱️ 50ms
   │
   ▼
6. FASTAPI
   ├─ Invalide le cache Redis
   │  └─ Redis.delete('personnel_list')
   │  └─ Redis.delete('dashboard_stats')
   │
   └─ Retourne la réponse JSON
   │
   ▼
7. cloudflared → CLOUDFLARE → Client
```

**Temps total** : ~200-250ms (incluant latence Cloudflare)

### Scénario 3 : Tentative de Connexion

```
1. Client → POST /mppeep/login
   │  username=john@mppeep.com
   │  password=secret123
   │
   ▼
2. CLOUDFLARE
   ├─ WAF : Vérifie (pas d'injection SQL, XSS)
   ├─ Rate Limiting Cloudflare (global)
   └─ Tunnel → localhost:9000
   │
   ▼
3. cloudflared → FASTAPI
   │
   ▼
4. FASTAPI - Rate Limiting (applicatif)
   ├─ Vérifier le nombre de tentatives
   │  └─ Redis.incr('login_attempts:197.234.XXX.XX')
   │     └─ Résultat : 3 tentatives
   │        ✅ < 5 tentatives → OK
   │
   ▼
5. POSTGRESQL
   ├─ SELECT * FROM users WHERE email = 'john@mppeep.com'
   └─ Vérifier le mot de passe (hash bcrypt) → ⏱️ 50ms
      ✅ Mot de passe correct !
   │
   ▼
6. FASTAPI - Créer la session
   ├─ Générer session_id = 'sess_abc123xyz'
   ├─ Stocker dans Redis
   │  └─ Redis.setex('session:sess_abc123xyz', 604800, user_data) → ⚡ 1ms
   ├─ Réinitialiser compteur
   │  └─ Redis.delete('login_attempts:197.234.XXX.XX') → ⚡ 1ms
   │
   └─ RedirectResponse vers /mppeep/accueil
   │
   ▼
7. cloudflared → CLOUDFLARE
   │
   ▼
8. Client reçoit :
   └─ Cookie: session_id=sess_abc123xyz; Max-Age=604800; Secure; HttpOnly
   └─ Redirect → /mppeep/accueil
```

**Prochaine requête** :
```
Client → /mppeep/dashboard
   + Cookie: session_id=sess_abc123xyz
   │
   ▼
FastAPI vérifie :
   └─ Redis.get('session:sess_abc123xyz') → ⚡ 1ms
      ✅ Session valide → Utilisateur authentifié
      ❌ Pas de requête PostgreSQL nécessaire !
```

---

## 💰 Économies de Performance

### Sans Redis (PostgreSQL seul)

```
Dashboard chargé par 100 utilisateurs :
├─ 100 requêtes pour vérifier les sessions → PostgreSQL
├─ 100 requêtes pour les stats dashboard → PostgreSQL
└─ Total : 200 requêtes SQL

Temps moyen par requête : 50ms
Temps total : 200 × 50ms = 10,000ms = 10 secondes ! 🐌

PostgreSQL surchargé ⚠️
```

### Avec Redis

```
Dashboard chargé par 100 utilisateurs :
├─ 100 vérifications de session → Redis (cache)
├─ 1 requête stats (1ère fois) → PostgreSQL → Mise en cache Redis
├─ 99 requêtes stats suivantes → Redis (cache)
└─ Total : 100 Redis + 1 PostgreSQL

Temps Redis : 1ms
Temps PostgreSQL : 50ms
Temps total : (100 × 1ms) + 50ms = 150ms ⚡

PostgreSQL au repos ✅
```

**Gain : 66x plus rapide !** 🚀

---

## 🏗️ Architecture Finale Complète

```
┌──────────────────────────────────────────────────────────────────┐
│                      CLIENT / NAVIGATEUR                         │
│  Envoie : http://localhost/mppeep/dashboard                     │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ Port 80 (HTTP)
                         │ ou 443 (HTTPS en prod)
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  SERVICE 1 : NGINX (Container mppeep-nginx)                     │
├──────────────────────────────────────────────────────────────────┤
│  Rôles :                                                         │
│  • Reverse Proxy vers FastAPI                                   │
│  • Serveur de fichiers statiques (/static, /uploads)           │
│  • SSL/TLS termination (HTTPS)                                  │
│  • Compression gzip                                              │
│  • Headers de sécurité                                           │
│  • Rate limiting basique                                         │
│  • Cache des fichiers statiques                                  │
│                                                                  │
│  Configuration : deploiement_docker/nginx.conf                  │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     │ proxy_pass http://app:9000
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│  SERVICE 2 : FASTAPI (Container mppeep-app)                     │
├──────────────────────────────────────────────────────────────────┤
│  Rôles :                                                         │
│  • Logique métier (Python)                                      │
│  • API REST (/api/v1/...)                                       │
│  • Authentification & Autorisation                              │
│  • Validation des données (Pydantic)                            │
│  • Rendu des templates HTML (Jinja2)                            │
│  • CRUD sur la base de données                                   │
│  • Gestion des fichiers uploadés                                 │
│                                                                  │
│  Image : mppeep:latest (buildée depuis Dockerfile.prod)         │
│  Commande : uvicorn app.main:app --workers 4                    │
└────┬──────────────────────────┬──────────────────────────────────┘
     │                           │
     │ Données permanentes      │ Cache & Sessions
     │                           │
     ▼                           ▼
┌────────────────────┐   ┌────────────────────┐
│  SERVICE 3 :       │   │  SERVICE 4 :       │
│  POSTGRESQL        │   │  REDIS             │
│  (mppeep-db)       │   │  (mppeep-redis)    │
├────────────────────┤   ├────────────────────┤
│  Rôles :           │   │  Rôles :           │
│  • Users           │   │  • Cache queries   │
│  • Personnel       │   │  • Sessions users  │
│  • Documents       │   │  • Rate limiting   │
│  • Activities      │   │  • Compteurs stats │
│  • System Settings │   │  • Queues (emails) │
│  • Files           │   │  • Pub/Sub         │
│                    │   │                    │
│  Stockage :        │   │  Stockage :        │
│  • Volume Docker   │   │  • RAM (volatile)  │
│  • Persistant      │   │  • + AOF (backup)  │
│                    │   │                    │
│  Port : 5432       │   │  Port : 6379       │
│  Taille : ~1GB+    │   │  Taille : 256MB    │
└────────────────────┘   └────────────────────┘
```

---

## 🎯 Pourquoi 4 Services au Lieu d'1 ?

### ❌ Architecture Monolithique (1 seul service)

```
┌─────────────────────────────────────────┐
│  UN SEUL CONTAINER                      │
│  ├─ Python                              │
│  ├─ FastAPI                             │
│  ├─ PostgreSQL                          │
│  ├─ Redis                               │
│  └─ Nginx                               │
└─────────────────────────────────────────┘
```

**Problèmes** :
- ❌ Difficile à scaler
- ❌ Mise à jour = tout redémarrer
- ❌ Pas d'isolation (sécurité)
- ❌ Un crash = tout tombe
- ❌ Ressources mal distribuées

### ✅ Architecture Microservices (4 services)

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Nginx   │  │ FastAPI  │  │PostgreSQL│  │  Redis   │
│  Alpine  │  │  Python  │  │ Alpine   │  │  Alpine  │
│  ~20MB   │  │  ~300MB  │  │  ~150MB  │  │  ~30MB   │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```

**Avantages** :
- ✅ **Scalabilité** : Ajouter des instances FastAPI facilement
- ✅ **Résilience** : Un service tombe ≠ tout tombe
- ✅ **Maintenance** : Mise à jour d'un service sans impacter les autres
- ✅ **Isolation** : Sécurité renforcée
- ✅ **Spécialisation** : Chaque service fait ce qu'il fait le mieux
- ✅ **Monitoring** : Logs et métriques par service

---

## 🚀 Exemple Réel : Que se passe-t-il quand vous vous connectez ?

```
Étape 1 : Vous ouvrez http://localhost/mppeep/
┌─────────────────────────────────────────────────────────────┐
│  Navigateur envoie : GET / HTTP/1.1                        │
│                      Host: localhost                        │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  NGINX (Port 80)                                            │
│  • Reçoit la requête                                        │
│  • Ajoute headers de sécurité                               │
│  • proxy_pass → http://app:9000/mppeep/                    │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  FASTAPI (Port 9000)                                        │
│  • Route "/" → RedirectResponse vers "/mppeep/login"       │
│  • Pas de session valide → Affiche login.html              │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
   Retour : Page HTML de login

Étape 2 : Vous entrez email + password et cliquez "Connexion"
┌─────────────────────────────────────────────────────────────┐
│  Navigateur envoie : POST /mppeep/login                    │
│                      username=admin@mppeep.com             │
│                      password=admin123                      │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  NGINX → FASTAPI                                            │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  FASTAPI - Authentification                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 1. Rate Limiting                                      │ │
│  │    └─ Redis.incr('login:192.168.1.100') → 2 ⚡ 1ms   │ │
│  │       ✅ < 5 tentatives, OK                           │ │
│  │                                                        │ │
│  │ 2. Vérifier les identifiants                          │ │
│  │    └─ PostgreSQL:                                     │ │
│  │       SELECT * FROM users                              │ │
│  │       WHERE email = 'admin@mppeep.com'                │ │
│  │       → ⏱️ 30ms                                        │ │
│  │       ✅ User trouvé, hash vérifié                    │ │
│  │                                                        │ │
│  │ 3. Créer la session                                   │ │
│  │    └─ session_id = 'sess_xyz789'                     │ │
│  │    └─ Redis.setex('session:sess_xyz789',             │ │
│  │                   604800,  # 7 jours                  │ │
│  │                   user_data) → ⚡ 1ms                 │ │
│  │                                                        │ │
│  │ 4. Réinitialiser le compteur de tentatives            │ │
│  │    └─ Redis.delete('login:192.168.1.100') ⚡ 1ms     │ │
│  │                                                        │ │
│  │ 5. Redirection vers /mppeep/accueil                   │ │
│  │    + Cookie: session_id=sess_xyz789                   │ │
│  └───────────────────────────────────────────────────────┘ │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
   Retour : RedirectResponse + Cookie
   
Étape 3 : Navigateur redirigé vers /mppeep/accueil
┌─────────────────────────────────────────────────────────────┐
│  GET /mppeep/accueil                                        │
│  Cookie: session_id=sess_xyz789                             │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  FASTAPI - Vérification Session                             │
│  └─ Redis.get('session:sess_xyz789') → ⚡ 1ms              │
│     ✅ Session valide, user_id=1                           │
│                                                             │
│  Récupération stats dashboard :                             │
│  └─ Redis.get('dashboard_stats:1') → ⚡ 1ms                │
│     ❌ Pas de cache → Requête PostgreSQL                   │
│     └─ SELECT COUNT(*) FROM users... → ⏱️ 100ms           │
│     └─ Redis.setex('dashboard_stats:1', 300, stats) ⚡ 1ms │
│                                                             │
│  Rendu du template accueil.html                             │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
   Page d'accueil avec stats ✅
```

---

## 🔧 Configuration Redis dans Votre Projet

```yaml
redis:
  image: redis:7-alpine
  command: redis-server 
    --appendonly yes          # ← Persistance (fichier AOF)
    --maxmemory 256mb         # ← Limite RAM : 256 MB
    --maxmemory-policy allkeys-lru  # ← Éviction LRU
```

**Paramètres** :
- `appendonly yes` : Sauvegarde sur disque (backup)
- `maxmemory 256mb` : Maximum 256 MB de RAM utilisée
- `allkeys-lru` : Quand plein, supprime les données **les moins récemment utilisées**

**LRU (Least Recently Used)** :
```
Redis est plein (256 MB) → Besoin de stocker nouvelle donnée
├─ Trouve la donnée la moins récemment utilisée
├─ La supprime
└─ Stocke la nouvelle donnée
```

---

## 📚 Résumé en Une Image

```
NGINX       =  Portier & Gardien
               • Filtre qui rentre
               • Sécurise l'entrée
               • Dirige vers la bonne porte

FASTAPI     =  Cerveau de l'Application
               • Prend les décisions
               • Applique la logique métier
               • Traite les demandes

REDIS       =  Mémoire Courte (RAM)
               • Très rapide
               • Données temporaires
               • Oublie les vieilles données

POSTGRESQL  =  Mémoire Longue (Disque)
               • Plus lent mais fiable
               • Données permanentes
               • N'oublie jamais
```

---

## 💡 Peut-on s'en Passer ?

### Sans Nginx (Votre Config Actuelle) ?
```
✅ Nginx DÉSACTIVÉ dans votre configuration :
- ✅ Cloudflare Tunnel fait le reverse proxy
- ✅ Cloudflare gère SSL/TLS automatiquement
- ✅ Cloudflare compresse (Brotli/gzip)
- ✅ Cloudflare sert de CDN global
- ✅ Cloudflare protège contre DDoS

Nginx n'est nécessaire QUE si vous n'utilisez PAS Cloudflare !
```

### Sans Redis ?
```
✅ Possible (Redis marqué "optionnel" dans votre docker-compose) :
- ⚠️ Performance réduite
- ⚠️ PostgreSQL plus sollicité
- ⚠️ Sessions dans PostgreSQL (plus lent)
- ⚠️ Pas de rate limiting efficace
- ⚠️ Difficile de scaler horizontalement

Mais l'app fonctionnera quand même !
```

---

## 🎯 Recommandations

### ✅ Votre Configuration (Production avec Cloudflare)

```
Stack Docker :
├─ FastAPI      ✅ OBLIGATOIRE
├─ PostgreSQL   ✅ OBLIGATOIRE
├─ Redis        ✅ FORTEMENT RECOMMANDÉ
└─ Nginx        ❌ DÉSACTIVÉ (Cloudflare le remplace)

Infrastructure :
└─ Cloudflare Tunnel  ✅ ACTIF
```

### 📊 Autres Scénarios

**En développement local (sans Cloudflare)** :
- FastAPI : Nécessaire
- PostgreSQL ou SQLite : Nécessaire
- Redis : Optionnel mais recommandé
- Nginx : Optionnel (accès direct FastAPI:9000 OK)

**En production SANS Cloudflare** :
- Nginx : **OBLIGATOIRE** (reverse proxy, SSL, sécurité)
- FastAPI : **OBLIGATOIRE**
- PostgreSQL : **OBLIGATOIRE**
- Redis : **FORTEMENT RECOMMANDÉ**

**En production AVEC Cloudflare (VOTRE CAS)** :
- Cloudflare Tunnel : **OBLIGATOIRE**
- FastAPI : **OBLIGATOIRE**
- PostgreSQL : **OBLIGATOIRE**
- Redis : **FORTEMENT RECOMMANDÉ**
- Nginx : **PAS NÉCESSAIRE** ❌

---

**Documentation créée le** : 2025-10-20  
**Version** : 1.0.0  
**Maintenu par** : MPPEEP Team

