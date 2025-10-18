# 🛡️ Configuration des Middlewares - Guide

## 📋 Activation automatique selon l'environnement

Les middlewares sont **configurés automatiquement** selon les variables `DEBUG` et `ENV` pour optimiser le développement et la production.

---

## 🔄 Tableau de configuration

| Middleware | Dev (DEBUG=True) | Prod (DEBUG=False) | Description |
|------------|------------------|--------------------|------------------------------------------------------------|
| **HTTPS Redirect** | ❌ Désactivé | ✅ Activé | Redirige HTTP → HTTPS (inutile en local) |
| **Trusted Hosts** | ✅ `["*"]` | ✅ ALLOWED_HOSTS | Valide le domaine de la requête |
| **CORS** | ✅ Activé | ✅ Activé | Autorise les requêtes cross-origin |
| **Error Handling** | ✅ Activé | ✅ Activé | Capture les erreurs non gérées |
| **Request Size Limit** | ✅ Activé | ✅ Activé | Limite à 10MB par requête |
| **IP Filter** | ❌ Optionnel | ❌ Optionnel | Bloque les IPs malveillantes (si configuré) |
| **User-Agent Filter** | ❌ Optionnel | ❌ Optionnel | Bloque les bots malveillants (si configuré) |
| **Logging** | ✅ Activé | ✅ Activé | Log toutes les requêtes |
| **Request ID** | ✅ Activé | ✅ Activé | Ajoute X-Request-ID unique |
| **GZip** | ❌ Désactivé | ✅ Activé | Compression des réponses (debug + facile sans) |
| **Cache Control** | ❌ Désactivé | ✅ Activé | Gère le cache HTTP (toujours frais en dev) |
| **Security Headers** | ❌ Désactivé | ✅ Activé | X-Frame-Options, X-XSS-Protection, etc. |
| **CSP** | ❌ Désactivé | ✅ Activé | Content Security Policy (strict en prod) |
| **Forward Proto** | ❌ Désactivé | ✅ Activé | Lit X-Forwarded-Proto (proxy/Cloudflare) |
| **Cloudflare** | ❌ Désactivé | ✅ Activé | Capture CF-Ray, CF-Connecting-IP, etc. |

---

## 🎯 Configuration dans `.env`

### **Développement local**

```env
DEBUG=true
ENV=dev

# Middlewares configurés automatiquement :
# - HTTPS Redirect : OFF
# - GZip : OFF (réponses non compressées pour debug)
# - Cache Control : OFF (toujours du contenu frais)
# - Security Headers : OFF (moins restrictif)
# - CSP : OFF (pas de blocage strict)
# - Forward Proto : OFF (pas de proxy en local)
# - Cloudflare : OFF (pas de headers CF-*)
```

### **Production (Cloudflare)**

```env
DEBUG=false
ENV=production
ROOT_PATH=/mppeep

# Middlewares configurés automatiquement :
# - HTTPS Redirect : ON (force HTTPS)
# - GZip : ON (compression des réponses)
# - Cache Control : ON (optimisation du cache)
# - Security Headers : ON (protection maximale)
# - CSP : ON (Content Security Policy strict)
# - Forward Proto : ON (lit X-Forwarded-Proto)
# - Cloudflare : ON (capture CF-*)
```

---

## 🔧 Override manuel

Si vous voulez **forcer l'activation** d'un middleware en dev (pour tester), modifiez le `.env` :

```env
DEBUG=true

# Forcer Cloudflare en dev (pour tests)
ENABLE_CLOUDFLARE=true

# Forcer GZip en dev
ENABLE_GZIP=true
```

**Priorité :**
1. Valeur dans `.env` (si définie)
2. Logique automatique selon `DEBUG`/`ENV`

---

## 📊 Logs de démarrage

Au démarrage, vous verrez les middlewares activés :

### **En développement** :
```
✅ Trusted Hosts : ['*']
🌐 CORS configuré : ['http://localhost', 'https://localhost', ...]
💥 Error Handling activé
📏 Request Size Limit : 10MB
📝 Request Logging activé
🎫 Request ID activé
✅ Configuration middlewares terminée
```

### **En production** :
```
🔒 HTTPS Redirect activé
✅ Trusted Hosts : ['skpartners.consulting', '*.skpartners.consulting']
🌐 CORS configuré : ['https://skpartners.consulting', ...]
💥 Error Handling activé
📏 Request Size Limit : 10MB
📝 Request Logging activé
🎫 Request ID activé
📦 GZip activé
💾 Cache Control activé
🔒 Security Headers activés
🛡️ CSP activé
🔗 Forward Proto activé
☁️  Cloudflare Middleware activé
✅ Configuration middlewares terminée
```

---

## 🐛 Debug : Vérifier la configuration active

Créez un endpoint de debug :

```python
@app.get("/debug/middlewares")
def debug_middlewares():
    return {
        "debug": settings.DEBUG,
        "env": settings.ENV,
        "middlewares": {
            "https_redirect": settings.should_enable_https_redirect,
            "gzip": settings.should_enable_gzip,
            "cache_control": settings.should_enable_cache_control,
            "security_headers": settings.should_enable_security_headers,
            "csp": settings.should_enable_csp,
            "forward_proto": settings.should_enable_forward_proto,
            "cloudflare": settings.should_enable_cloudflare,
        }
    }
```

**Test** :
```bash
curl http://localhost:9000/debug/middlewares
```

**Réponse (dev)** :
```json
{
  "debug": true,
  "env": "dev",
  "middlewares": {
    "https_redirect": false,
    "gzip": false,
    "cache_control": false,
    "security_headers": false,
    "csp": false,
    "forward_proto": false,
    "cloudflare": false
  }
}
```

---

## 🎯 Résumé

✅ **En développement** : Middlewares légers pour faciliter le debug  
✅ **En production** : Tous les middlewares activés pour sécurité et performance  
✅ **Configuration automatique** : Pas besoin de gérer manuellement  
✅ **Override possible** : Via `.env` si besoin de tester

**Tout est maintenant configuré pour s'adapter automatiquement ! 🚀**

