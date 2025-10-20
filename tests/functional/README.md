# 📋 Tests Fonctionnels

## Description

Tests des workflows complets (scénarios bout-en-bout).

## Exécution

```bash
pytest tests/functional/ -m critical
```

## Tests inclus

- `test_database_init_workflow.py` - Workflow d'initialisation DB
- `test_password_recovery_workflow.py` - Workflow de récupération de mot de passe

## Critères de succès

✅ Workflows critiques fonctionnent de bout en bout
