"""
Service de préchauffage du chatbot Ollama pour réduire la latence au démarrage.

Ce service permet de "chauffer" le modèle Ollama en arrière-plan pour que
l'utilisateur n'ait pas à attendre le chargement du modèle au premier appel.

Stratégie:
1. Préchauffage initial au démarrage de l'app
2. Keep-alive périodique pour maintenir le modèle en mémoire
3. Préchauffage intelligent basé sur le modèle par défaut
"""

import httpx
import asyncio
from typing import Optional
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ChatbotWarmupService:
    """Service pour préchauffer et maintenir le chatbot Ollama actif"""
    
    # Variable de classe pour stocker l'état de préchauffage
    _warmup_completed = False
    _warmup_in_progress = False
    _default_model: Optional[str] = None
    
    @classmethod
    async def check_ollama_availability(cls) -> bool:
        """
        Vérifie si Ollama est disponible et récupère les modèles disponibles.
        
        Returns:
            True si Ollama est disponible, False sinon
        """
        try:
            ollama_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
            ollama_api_url = f"{ollama_url}/api/tags"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(ollama_api_url)
                response.raise_for_status()
                
                result = response.json()
                models = [model.get("name", "") for model in result.get("models", [])]
                
                if models:
                    # Utiliser le premier modèle disponible comme modèle par défaut
                    cls._default_model = models[0]
                    logger.info(f"✅ Ollama disponible avec {len(models)} modèle(s): {models}")
                    logger.info(f"🔧 Modèle par défaut sélectionné: {cls._default_model}")
                    return True
                else:
                    logger.warning("⚠️ Ollama disponible mais aucun modèle installé")
                    return False
                    
        except Exception as e:
            logger.debug(f"⚠️ Ollama non disponible: {e}")
            return False
    
    @classmethod
    async def warmup_model(cls, model: Optional[str] = None) -> bool:
        """
        Préchauffe un modèle Ollama en envoyant une requête simple.
        
        Cette fonction charge le modèle en mémoire, réduisant ainsi la latence
        pour les requêtes suivantes de l'utilisateur.
        
        Args:
            model: Nom du modèle à préchauffer. Si None, utilise le modèle par défaut.
            
        Returns:
            True si le préchauffage a réussi, False sinon
        """
        # Éviter les préchauffages simultanés
        if cls._warmup_in_progress:
            logger.debug("⏳ Préchauffage déjà en cours, attente...")
            return False
        
        cls._warmup_in_progress = True
        
        try:
            # Utiliser le modèle fourni ou le modèle par défaut
            target_model = model or cls._default_model or "llama3.2"
            
            if not await cls.check_ollama_availability():
                logger.warning("⚠️ Ollama non disponible, préchauffage annulé")
                cls._warmup_in_progress = False
                return False
            
            # Utiliser le modèle par défaut détecté si aucun n'est fourni
            if not model and cls._default_model:
                target_model = cls._default_model
            
            ollama_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
            ollama_api_url = f"{ollama_url}/api/generate"
            
            # Requête de préchauffage ultra-légère (juste pour charger le modèle)
            warmup_payload = {
                "model": target_model,
                "prompt": "OK",  # Prompt minimal pour juste charger le modèle
                "stream": False,
                "options": {
                    "num_predict": 1,  # Générer seulement 1 token pour minimiser le temps
                    "temperature": 0.1,
                }
            }
            
            logger.info(f"🔥 Début du préchauffage du modèle Ollama: {target_model}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        ollama_api_url,
                        json=warmup_payload
                    )
                    response.raise_for_status()
                    
                    cls._warmup_completed = True
                    logger.info(f"✅ Modèle Ollama préchauffé avec succès: {target_model}")
                    return True
                    
                except httpx.TimeoutException:
                    logger.warning(f"⏱️ Timeout lors du préchauffage du modèle {target_model}")
                    return False
                except httpx.RequestError as e:
                    logger.warning(f"⚠️ Erreur de connexion lors du préchauffage: {e}")
                    return False
                except Exception as e:
                    logger.warning(f"⚠️ Erreur lors du préchauffage: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Erreur inattendue lors du préchauffage: {e}")
            return False
        finally:
            cls._warmup_in_progress = False
    
    @classmethod
    async def keep_alive(cls, model: Optional[str] = None) -> bool:
        """
        Envoie une requête keep-alive pour maintenir le modèle chargé en mémoire.
        
        Cette fonction est appelée périodiquement pour éviter que le modèle
        soit déchargé par Ollama après une période d'inactivité.
        
        Args:
            model: Nom du modèle à maintenir. Si None, utilise le modèle par défaut.
            
        Returns:
            True si le keep-alive a réussi, False sinon
        """
        try:
            target_model = model or cls._default_model or "llama3.2"
            
            ollama_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
            ollama_api_url = f"{ollama_url}/api/generate"
            
            # Requête keep-alive encore plus légère
            keepalive_payload = {
                "model": target_model,
                "prompt": ".",  # Un seul caractère
                "stream": False,
                "options": {
                    "num_predict": 1,
                }
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(ollama_api_url, json=keepalive_payload)
                logger.debug(f"💓 Keep-alive envoyé pour le modèle {target_model}")
                return True
                
        except Exception as e:
            logger.debug(f"⚠️ Keep-alive échoué (normal si Ollama est arrêté): {e}")
            return False
    
    @classmethod
    def warmup_sync(cls, model: Optional[str] = None) -> bool:
        """
        Version synchrone du préchauffage pour être appelée depuis le scheduler.
        
        Args:
            model: Nom du modèle à préchauffer
            
        Returns:
            True si le préchauffage a réussi
        """
        try:
            # Vérifier si une boucle d'événements existe
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Si une boucle est déjà en cours, créer une nouvelle tâche dans un thread
                    import threading
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            new_loop.run_until_complete(cls.warmup_model(model))
                        finally:
                            new_loop.close()
                    
                    thread = threading.Thread(target=run_in_thread, daemon=True)
                    thread.start()
                    return True
                else:
                    # Boucle existe mais pas en cours d'exécution
                    return loop.run_until_complete(cls.warmup_model(model))
            except RuntimeError:
                # Pas de boucle d'événements, créer une nouvelle
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(cls.warmup_model(model))
                    return result
                finally:
                    loop.close()
        except Exception as e:
            logger.error(f"❌ Erreur lors du préchauffage synchrone: {e}")
            return False
    
    @classmethod
    def keep_alive_sync(cls, model: Optional[str] = None) -> bool:
        """
        Version synchrone du keep-alive pour être appelée depuis le scheduler.
        
        Args:
            model: Nom du modèle à maintenir
            
        Returns:
            True si le keep-alive a réussi
        """
        try:
            # Vérifier si une boucle d'événements existe
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Si une boucle est déjà en cours, créer une nouvelle tâche dans un thread
                    import threading
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            new_loop.run_until_complete(cls.keep_alive(model))
                        finally:
                            new_loop.close()
                    
                    thread = threading.Thread(target=run_in_thread, daemon=True)
                    thread.start()
                    return True
                else:
                    # Boucle existe mais pas en cours d'exécution
                    return loop.run_until_complete(cls.keep_alive(model))
            except RuntimeError:
                # Pas de boucle d'événements, créer une nouvelle
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(cls.keep_alive(model))
                    return result
                finally:
                    loop.close()
        except Exception as e:
            logger.debug(f"⚠️ Keep-alive échoué: {e}")
            return False
    
    @classmethod
    def is_warmup_completed(cls) -> bool:
        """Retourne True si le préchauffage initial a été complété"""
        return cls._warmup_completed
    
    @classmethod
    def get_default_model(cls) -> Optional[str]:
        """Retourne le modèle par défaut détecté"""
        return cls._default_model

