# ============================================
# DOCKERFILE MULTI-STAGE POUR MPPEEP DASHBOARD
# ============================================
# Stage 1 : Builder - Installation des dépendances
# Stage 2 : Production - Image finale légère
# ============================================

# ============================================
# STAGE 1: BUILDER
# ============================================
FROM python:3.11-slim as builder

# Métadonnées
LABEL maintainer="MPPEEP Dashboard"
LABEL description="FastAPI Boilerplate Production-Ready"

# Variables d'environnement pour Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Répertoire de travail
WORKDIR /build

# Installer uv (gestionnaire de packages rapide)
RUN pip install uv

# Copier les fichiers de dépendances
COPY pyproject.toml ./
COPY uv.lock ./

# Installer les dépendances de production dans un venv
RUN uv sync --no-dev --no-editable

# ============================================
# STAGE 2: PRODUCTION
# ============================================
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    DEBUG=false \
    ENV=production

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/logs && \
    chown -R appuser:appuser /app

# Répertoire de travail
WORKDIR /app

# Copier le venv depuis le builder
COPY --from=builder --chown=appuser:appuser /build/.venv /app/.venv

# Copier le code de l'application
COPY --chown=appuser:appuser ./app ./app
COPY --chown=appuser:appuser ./scripts ./scripts
COPY --chown=appuser:appuser pyproject.toml ./

# Changer vers l'utilisateur non-root
USER appuser

# Exposer le port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/ping || exit 1

# Commande par défaut
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

