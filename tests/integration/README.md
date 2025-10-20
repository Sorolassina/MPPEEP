# 🔗 Tests d'Intégration

## Description

Tests des interactions entre composants : API, base de données, authentification.

## Exécution

```bash
pytest tests/integration/ -m critical
```

## Tests inclus

- `test_database_initialization.py` - Initialisation complète de la DB
- `test_auth_api.py` - API d'authentification (login, JWT)
- `test_health.py` - Santé de l'application

## Critères de succès

✅ Base de données initialisée correctement
✅ Authentification fonctionnelle
✅ Toutes les routes enregistrées
