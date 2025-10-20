# 🔬 Tests Unitaires

## Description

Tests des composants isolés : configuration, sécurité, modèles, utilitaires.

## Exécution

```bash
pytest tests/unit/ -m critical
```

## Tests inclus

- `test_config.py` - Configuration et variables d'environnement
- `test_security.py` - Hachage bcrypt et JWT
- `test_models.py` - Validation des modèles SQLModel

## Critères de succès

✅ Tous les tests critiques passent (marqués `@pytest.mark.critical`)
