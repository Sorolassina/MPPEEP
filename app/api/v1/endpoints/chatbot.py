"""
Routes pour le chatbot Ollama
"""

import json
import httpx
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session
from starlette.requests import Request

from app.api.v1.endpoints.auth import get_current_user
from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.path_config import path_config
from app.db.session import get_session
from app.models.user import User
from app.services.activity_service import ActivityService
from app.services.chatbot_rag_service import ChatbotRAGService
from app.services.document_extractor import DocumentExtractor

logger = get_logger(__name__)

router = APIRouter()


def normalize_document_text(text: str) -> str:
    """
    Normalise le texte d'un document pour réduire sa taille et améliorer les performances.
    Similaire à la normalisation utilisée pour les modèles PTR/NLP.
    Supprime les stop words, déterminants et mots sans sens en utilisant NLTK.
    
    Args:
        text: Texte à normaliser
        
    Returns:
        Texte normalisé (stop words supprimés, espaces normalisés, lignes vides supprimées)
    """
    if not text:
        return ""
    
    try:
        # Utiliser NLTK pour les stop words français
        import nltk
        from nltk.corpus import stopwords
        
        # Télécharger les stop words si nécessaire (seulement la première fois)
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)
        
        # Récupérer les stop words français
        stop_words = set(stopwords.words('french'))
        
        # Ajouter des stop words supplémentaires spécifiques au français
        stop_words.update({
            'être', 'avoir', 'faire', 'dire', 'aller', 'voir', 'savoir',
            'vouloir', 'devoir', 'pouvoir', 'falloir', 'paraître',
            'de', 'du', 'des', 'de la', 'au', 'aux', 'à la', 'à les'
        })
        
    except ImportError:
        # Fallback si NLTK n'est pas installé : utiliser une liste basique
        logger.warning("NLTK n'est pas installé, utilisation d'une liste basique de stop words")
        stop_words = {
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'ce', 'cet', 'cette', 'ces',
            'à', 'au', 'aux', 'avec', 'sans', 'sous', 'sur', 'dans', 'pour', 'par',
            'et', 'ou', 'mais', 'donc', 'or', 'ni', 'car', 'que', 'qui', 'quoi',
            'il', 'elle', 'ils', 'elles', 'nous', 'vous', 'je', 'tu', 'on',
            'est', 'sont', 'était', 'étaient', 'être', 'avoir', 'a', 'ont'
        }
    
    # Normaliser les espaces multiples en un seul espace
    text = re.sub(r'\s+', ' ', text)
    
    # Supprimer les lignes vides multiples (garder au maximum 2 sauts de ligne consécutifs)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # Supprimer les espaces en début et fin de ligne
    lines = text.split('\n')
    normalized_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            normalized_lines.append('')
            continue
        
        # Tokeniser la ligne en mots (en minuscules pour la comparaison)
        words = re.findall(r'\b\w+\b', line.lower())
        
        # Filtrer les stop words
        filtered_words = [word for word in words if word not in stop_words]
        
        # Reconstruire la ligne avec les mots filtrés
        if filtered_words:
            normalized_line = ' '.join(filtered_words)
            normalized_lines.append(normalized_line)
        else:
            # Si tous les mots sont des stop words, garder la ligne vide
            normalized_lines.append('')
    
    text = '\n'.join(normalized_lines)
    
    # Supprimer les lignes vides multiples après filtrage
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # Supprimer les espaces multiples entre les mots (garder un seul espace)
    text = re.sub(r' +', ' ', text)
    
    # Supprimer les espaces en début et fin
    text = text.strip()
    
    return text


def is_greeting(message: str) -> bool:
    """
    Détermine si le message est une simple salutation.
    
    Args:
        message: Message de l'utilisateur
        
    Returns:
        True si c'est une salutation, False sinon
    """
    message_lower = message.lower().strip()
    
    # Liste des salutations courantes (français et anglais)
    greetings = [
        'bonjour',
        'bonsoir',
        'salut',
        'hello',
        'hi',
        'hey',
        'coucou',
        'bon matin',
        'bon après-midi',
        'bonne soirée',
        'bonne nuit',
        'bonjour à tous',
        'salut tout le monde',
        'hey there',
        'good morning',
        'good afternoon',
        'good evening',
    ]
    
    # Vérifier si le message est exactement une salutation (ou salutation + ponctuation)
    message_clean = re.sub(r'[^\w\s]', '', message_lower)  # Enlever la ponctuation
    words = message_clean.split()
    
    # Si le message contient seulement 1-3 mots et qu'un de ces mots est une salutation
    if len(words) <= 3:
        for greeting in greetings:
            if greeting in words:
                return True
    
    return False


def is_document_question_required(message: str, document_context: Optional[str]) -> bool:
    """
    Détermine si le message de l'utilisateur nécessite une réponse basée sur le document.
    Règle simple : utiliser le document uniquement si le message commence par "dans ce document".
    
    Args:
        message: Message de l'utilisateur
        document_context: Contexte du document (si disponible)
        
    Returns:
        True si le message commence par "dans ce document", False sinon
    """
    if not document_context:
        return False
    
    message_lower = message.lower().strip()
    
    # Vérifier si le message commence par "dans ce document" (avec variations)
    document_prefixes = [
        'dans ce document',
        'dans ce doc',
        'dans le document',
        'dans le doc',
        'ce document',
        'le document',
        'document'
    ]
    
    # Vérifier si le message commence par un de ces préfixes
    for prefix in document_prefixes:
        if message_lower.startswith(prefix):
            return True
    
    return False


class ChatMessage(BaseModel):
    message: str
    model: str = "llama3.2"  # Modèle par défaut
    stream: bool = False
    document_context: Optional[str] = None  # Contexte des documents uploadés


@router.post("/chat")
async def chat_with_ollama(
    chat_message: ChatMessage,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Envoie un message au chatbot Ollama et retourne la réponse
    
    Args:
        chat_message: Le message de l'utilisateur et les paramètres
        current_user: L'utilisateur actuel (authentifié)
    
    Returns:
        La réponse du chatbot Ollama
    """
    try:
        # URL de l'API Ollama (par défaut localhost:11434)
        ollama_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
        ollama_api_url = f"{ollama_url}/api/generate"
        
        # Vérifier si c'est une simple salutation
        is_simple_greeting = is_greeting(chat_message.message)
        
        # Récupérer le contexte de la base de données (RAG) seulement si ce n'est pas une salutation
        if is_simple_greeting:
            db_context = None
            logger.info(f"👋 Salutation détectée: '{chat_message.message}' - Contexte RAG ignoré")
        else:
            db_context = ChatbotRAGService.get_context_for_query(session, chat_message.message)
        
        # Traiter le contexte des documents uploadés séparément (priorité élevée)
        document_context = None
        if chat_message.document_context:
            logger.info(f"📄 Document context reçu: {len(chat_message.document_context)} caractères")
            # Normaliser le contenu du document pour réduire la taille et améliorer les performances
            document_context = normalize_document_text(chat_message.document_context)
            logger.info(f"📝 Document context normalisé: {len(document_context)} caractères (réduction: {len(chat_message.document_context) - len(document_context)} caractères)")
            logger.info(f"📚 Contexte document préparé: {len(document_context)} caractères")
        
        # Vérifier si le message nécessite une réponse basée sur le document
        use_document_context = is_document_question_required(chat_message.message, document_context)
        
        # Préparer le prompt avec un contexte système simplifié pour améliorer les performances
        # Adapter le prompt selon si un document est disponible
        document_instruction = ""
        if document_context:
            if use_document_context:
                document_instruction = "\n\nDOCUMENT: L'utilisateur a dit 'dans ce document'. Utilise le document ci-dessous pour répondre."
            else:
                document_instruction = "\n\nNOTE: Document uploadé mais non demandé. Réponds avec tes connaissances générales, SANS mentionner le document."
        
        # Adapter le prompt si c'est une salutation
        greeting_instruction = ""
        if is_simple_greeting:
            greeting_instruction = "\n\n⚠️ ATTENTION : L'utilisateur a simplement dit bonjour/bonsoir/salut. Réponds UNIQUEMENT par une salutation simple et naturelle (ex: 'Bonjour ! Comment puis-je vous aider ?'). NE récite PAS tes missions, ton rôle, ou la liste des modules. Sois BRIÈV et NATUREL, comme un collègue."
        
        # Système prompt simplifié pour améliorer les performances
        system_prompt = f"""Tu es SYGEP AI, assistant du système MPPEEP Dashboard.{document_instruction}{greeting_instruction}

RÔLE: Aide les utilisateurs avec les modules (RH, Personnel, Performance, Budget, Stock, Référentiels, Workflows).

RÈGLES IMPORTANTES:
- Pour les SALUTATIONS (bonjour, bonsoir, salut, hello, hi, bonsoir, etc.) : Réponds SIMPLEMENT et NATURELLEMENT, comme un collègue. Par exemple : "Bonjour ! Comment puis-je vous aider ?" ou "Salut ! Qu'est-ce qui vous amène ?" NE récite PAS tes missions ou ton rôle.
- Guide vers l'interface utilisateur, JAMAIS les routes API (/api/v1/...)
- Sois concis et précis
- Utilise les données fournies ci-dessous
- Si tu ne sais pas, dis-le clairement

TON RÔLE:
1. AIDER À COMPRENDRE LES MODULES: Explique clairement comment fonctionnent les différents modules du système:
   - Module RH (Ressources Humaines): Gestion des demandes (congés, missions, formations), workflows, validation hiérarchique
   - Module Personnel: Gestion des agents, grades, services, directions, documents
   - Module Performance: Objectifs, indicateurs (KPIs), rapports, tableaux de bord
   - Module Budget: SIGOBE, fiches hiérarchiques, programmes budgétaires
   - Module Stock: Articles, lots périssables, amortissement, mouvements, inventaires
   - Module Référentiels: Services, grades, programmes, directions
   - Module Workflows: Configuration des workflows personnalisés

2. AIDER À MANIPULER LE SYSTÈME: Guide l'utilisateur étape par étape pour:
   - Naviguer dans les différentes sections
   - Créer, modifier, supprimer des données
   - Utiliser les fonctionnalités disponibles
   - Comprendre les workflows et processus
   - Résoudre les problèmes courants

3. RÉPONDRE AUX QUESTIONS: Utilise les données de la base de données fournies ci-dessous pour donner des réponses précises et à jour.

RÈGLES IMPORTANTES POUR LES INSTRUCTIONS DE NAVIGATION:
- NE JAMAIS mentionner les routes API techniques (comme /api/v1/performance, /api/v1/rh, etc.)
- TOUJOURS donner des instructions basées sur l'interface utilisateur (menus, boutons, liens)
- Utilise des descriptions de navigation comme:
  * "Allez sur la page d'accueil, puis cliquez sur le module 'Suivi de la performance'"
  * "Dans le module Performance, cliquez sur le bouton 'Configurer les indicateurs'"
  * "Utilisez le menu de navigation en haut de la page"
  * "Cliquez sur le bouton 'Gérer les objectifs' dans la section Actions rapides"
- Décris les étapes visuelles que l'utilisateur doit suivre dans l'interface
- Mentionne les noms des boutons, sections et menus tels qu'ils apparaissent à l'écran

EXEMPLES DE BONNES INSTRUCTIONS:
✅ "Pour créer un indicateur: 1) Allez sur la page d'accueil, 2) Cliquez sur 'Suivi de la performance', 3) Dans la section 'Actions rapides', cliquez sur 'Configurer les indicateurs', 4) Cliquez sur le bouton 'Nouvel indicateur'"
✅ "Pour accéder au module RH: Depuis la page d'accueil, cliquez sur le bouton 'Gestion des ressources humaines' dans la section 'Modules disponibles'"

EXEMPLES DE MAUVAISES INSTRUCTIONS (À ÉVITER):
❌ "Accédez à /api/v1/performance"
❌ "Utilisez la route /api/v1/rh"
❌ "Faites une requête POST vers /api/v1/..."

STYLE DE RÉPONSE:
- Sois clair, concis et professionnel
- Utilise un langage accessible, même pour les fonctionnalités complexes
- Donne des exemples concrets quand c'est possible
- Si tu ne connais pas la réponse exacte, utilise les informations disponibles pour donner une réponse utile
- Propose des alternatives ou des pistes de solution
- TOUJOURS privilégier les instructions d'interface utilisateur plutôt que les routes techniques
- Si un guide spécifique est fourni dans le contexte, utilise-le comme base pour ta réponse
- Si aucun guide spécifique n'est disponible, utilise tes connaissances générales sur les systèmes de gestion et les données fournies

GESTION DES CAS SPÉCIFIQUES:
1. QUESTIONS TRÈS SPÉCIFIQUES NON DOCUMENTÉES:
   - Utilise les données de la base de données pour trouver des informations pertinentes
   - Si l'information n'est pas disponible, sois honnête et guide l'utilisateur vers la page d'aide ou l'administrateur
   - Propose des alternatives basées sur les fonctionnalités similaires disponibles

3. FONCTIONNALITÉS RÉCEMMENT AJOUTÉES:
   - Reconnais que la fonctionnalité peut être nouvelle
   - Utilise les données disponibles pour donner des informations
   - Guide l'utilisateur à explorer l'interface pour découvrir la fonctionnalité
   - Propose de consulter la documentation ou l'administrateur

4. CAS D'ERREUR TRÈS PARTICULIERS:
   - Sois empathique et rassurant
   - Propose des solutions étape par étape (actualiser, vider cache, vérifier session, etc.)
   - Si l'erreur est complexe, guide vers l'administrateur avec les informations nécessaires (message d'erreur, étapes, navigateur)
   - Utilise les données de la base pour vérifier si c'est un problème de données

5. QUESTIONS NÉCESSITANT DES INFORMATIONS EXTERNES:
   - Identifie clairement que l'information n'est pas dans le système MPPEEP
   - Utilise les données disponibles dans MPPEEP pour donner un contexte
   - Guide vers les sources d'information externes appropriées
   - Si c'est une question d'intégration, guide vers l'administrateur technique

IMPORTANT: 
- Utilise les informations de la base de données fournies ci-dessous pour répondre aux questions
- Si les informations ne sont pas disponibles dans le contexte, utilise tes connaissances générales pour donner une réponse utile
- Guide toujours l'utilisateur vers l'interface utilisateur, jamais vers les routes API techniques
- Si tu n'es pas certain d'une information, dis-le clairement et propose de consulter la page d'aide du module concerné
- Pour les cas très spécifiques, sois honnête sur les limites et guide vers les bonnes ressources

GESTION DES QUESTIONS HORS CONTEXTE:
- Si une question n'est PAS liée au système MPPEEP Dashboard (ex: questions sur l'actualité, la géographie, l'histoire, etc.):
  * Tu peux répondre en utilisant tes connaissances générales
  * Sois utile et informatif
  * Mentionne poliment que tu es principalement conçu pour aider avec MPPEEP Dashboard
  * Propose de revenir à des questions sur le système si l'utilisateur a besoin d'aide
- NE force PAS à ramener la question vers MPPEEP si elle n'a aucun lien
- Réponds naturellement et de manière utile, même si c'est hors contexte"""
        
        # Construire le prompt avec le contexte
        # Priorité 1: Document context (si disponible)
        # Priorité 2: DB context (si disponible)
        
        context_parts = []
        
        # Ajouter le contexte des documents seulement si nécessaire
        if document_context and use_document_context:
            # Limiter encore plus la taille du document_context pour améliorer les performances
            max_doc_length = 8000  # Réduire à 8000 caractères max pour accélérer
            if len(document_context) > max_doc_length:
                document_context = document_context[:max_doc_length] + "\n\n[... contenu tronqué ...]"
                logger.info(f"📏 Document context tronqué à {max_doc_length} caractères pour optimiser les performances")
            
            context_parts.append(f"DOCUMENT:\n{document_context}\n\nRéponds en te basant sur ce document.")
        elif document_context and not use_document_context:
            logger.info("ℹ️ Document disponible mais message ne nécessite pas de réponse basée sur le document (message de politesse ou court)")
        
        # Ajouter le contexte de la base de données ensuite
        is_out_of_scope = "QUESTION HORS CONTEXTE" in db_context if db_context else False
        
        if is_out_of_scope:
            # Pour les questions hors contexte, modifier le prompt pour permettre des réponses générales
            context_parts.append(f"{db_context}\n\nIMPORTANT: Cette question n'est pas liée au système MPPEEP. Tu peux répondre en utilisant tes connaissances générales. Sois utile et informatif, mais mentionne poliment que tu es principalement conçu pour aider avec le système MPPEEP Dashboard.\n")
        elif db_context:
            # Limiter aussi la taille du contexte DB pour améliorer les performances
            max_db_length = 2000  # Limiter le contexte DB à 2000 caractères
            if len(db_context) > max_db_length:
                db_context = db_context[:max_db_length] + "\n[... données tronquées ...]"
            context_parts.append(f"DONNÉES:\n{db_context}\n")
        
        # Construire la section de contexte
        if context_parts:
            context_section = "\n\n" + "\n\n".join(context_parts) + "\n"
        else:
            context_section = "\n\nNote: Aucune donnée spécifique n'est disponible pour cette question.\n"
        
        # Ajouter une instruction spéciale pour les questions hors contexte
        if is_out_of_scope:
            system_prompt += "\n\nATTENTION: La question de l'utilisateur semble être hors du contexte du système MPPEEP Dashboard. Tu peux répondre à la question en utilisant tes connaissances générales, mais sois poli et mentionne que tu es principalement conçu pour aider avec MPPEEP. Réponds de manière utile et informative."
        
        full_prompt = f"{system_prompt}{context_section}\nUtilisateur: {chat_message.message}\nAssistant:"
        
        logger.info(f"📝 Prompt final préparé: {len(full_prompt)} caractères")
        logger.info(f"📤 PROMPT ENVOYÉ À OLLAMA (premiers 2000 caractères):\n{full_prompt[:2000]}")
        if len(full_prompt) > 2000:
            logger.info(f"📤 ... (suite, {len(full_prompt) - 2000} caractères restants)")
            logger.info(f"📤 PROMPT ENVOYÉ À OLLAMA (derniers 1000 caractères):\n...{full_prompt[-1000:]}")
        
        # Préparer la requête pour Ollama
        ollama_payload = {
            "model": chat_message.model,
            "prompt": full_prompt,
            "stream": chat_message.stream,
            "options": {
                "temperature": 0.6,  # Réduire pour des réponses plus directes et rapides
                "top_p": 0.85,  # Réduire pour accélérer
                "num_predict": 1000,  # Réduire encore pour accélérer (1000 tokens max)
                "top_k": 30,  # Réduire pour accélérer
                "repeat_penalty": 1.1,  # Éviter les répétitions
            }
        }
        
        logger.info(f"📦 Payload Ollama: model={ollama_payload['model']}, stream={ollama_payload['stream']}, prompt_length={len(ollama_payload['prompt'])}")
        
        # Si streaming est activé, retourner un stream
        if chat_message.stream:
            async def generate_stream():
                logger.info("🔄 Démarrage du stream vers Ollama...")
                async with httpx.AsyncClient(timeout=120.0) as client:  # Timeout de 2 minutes (suffisant avec les optimisations)
                    try:
                        logger.info(f"📤 Envoi de la requête à Ollama: {ollama_api_url}")
                        async with client.stream(
                            "POST",
                            ollama_api_url,
                            json=ollama_payload
                        ) as response:
                            logger.info(f"📥 Réponse Ollama reçue: {response.status_code}")
                            if response.status_code != 200:
                                error_text = await response.aread()
                                error_json = json.dumps({"error": error_text.decode()})
                                logger.error(f"❌ Erreur Ollama: {error_text.decode()}")
                                yield f"data: {error_json}\n\n"
                                return
                            
                            full_response = ""
                            line_count = 0
                            chunk_count = 0
                            
                            # Lire le stream par chunks pour éviter les problèmes de buffer
                            async for chunk in response.aiter_bytes():
                                chunk_count += 1
                                if chunk_count == 1:
                                    logger.info(f"📦 Premier chunk reçu d'Ollama: {len(chunk)} bytes")
                                
                                # Décoder le chunk
                                chunk_text = chunk.decode('utf-8', errors='ignore')
                                
                                # Traiter chaque ligne dans le chunk
                                for line in chunk_text.split('\n'):
                                    line = line.strip()
                                    if not line:
                                        continue
                                    
                                    line_count += 1
                                    if line_count == 1:
                                        logger.info(f"📡 Première ligne reçue d'Ollama: {line[:200]}...")
                                    
                                    try:
                                        # Parser la ligne JSON d'Ollama
                                        ollama_data = json.loads(line)
                                        
                                        # Extraire la réponse partielle
                                        if "response" in ollama_data:
                                            response_text = ollama_data["response"]
                                            full_response += response_text
                                            
                                            # Envoyer la réponse accumulée
                                            stream_data = json.dumps({
                                                "response": response_text,
                                                "done": ollama_data.get("done", False)
                                            })
                                            yield f"data: {stream_data}\n\n"
                                            
                                            if line_count <= 3:
                                                logger.info(f"📤 Données envoyées au client: {len(response_text)} caractères")
                                        
                                        # Si terminé, envoyer un message final
                                        if ollama_data.get("done", False):
                                            logger.info(f"✅ Stream terminé, {len(full_response)} caractères générés, {line_count} lignes traitées")
                                            final_data = json.dumps({
                                                "response": "",
                                                "done": True
                                            })
                                            yield f"data: {final_data}\n\n"
                                            return
                                    except json.JSONDecodeError:
                                        # Si ce n'est pas du JSON valide, continuer
                                        if line_count <= 3:
                                            logger.warning(f"⚠️ Ligne non-JSON ignorée: {line[:200]}")
                                        continue
                                    except Exception as e:
                                        logger.error(f"Erreur lors du parsing du stream: {e}, ligne: {line[:200]}")
                                        continue
                            
                            logger.warning(f"⚠️ Stream terminé sans 'done', {line_count} lignes reçues, {chunk_count} chunks")
                    except httpx.TimeoutException:
                        error_json = json.dumps({"error": "Timeout: La requête a pris trop de temps"})
                        yield f"data: {error_json}\n\n"
                    except Exception as e:
                        logger.error(f"Erreur lors du streaming Ollama: {e}")
                        error_json = json.dumps({"error": str(e)})
                        yield f"data: {error_json}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream"
            )
        
        # Sinon, requête normale
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    ollama_api_url,
                    json=ollama_payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Extraire la réponse
                response_text = result.get("response", "")
                
                return {
                    "success": True,
                    "response": response_text,
                    "model": chat_message.model,
                    "done": result.get("done", True)
                }
                
            except httpx.TimeoutException:
                logger.error("Timeout lors de la requête Ollama")
                raise HTTPException(
                    status_code=504,
                    detail="Timeout: La requête a pris trop de temps. Veuillez réessayer."
                )
            except httpx.HTTPStatusError as e:
                logger.error(f"Erreur HTTP Ollama: {e}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Erreur lors de la communication avec Ollama: {e.response.text}"
                )
            except httpx.RequestError as e:
                logger.error(f"Erreur de connexion Ollama: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Impossible de se connecter à Ollama. Vérifiez que Ollama est démarré sur le serveur."
                )
            except Exception as e:
                logger.error(f"Erreur inattendue lors de l'appel Ollama: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur interne: {str(e)}"
                )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue dans chat_with_ollama: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne du serveur: {str(e)}"
        )


@router.get("/test-upload")
async def test_upload_endpoint(current_user: User = Depends(get_current_user)):
    """
    Endpoint de test pour vérifier que l'endpoint est accessible
    """
    logger.info(f"✅ Test endpoint accessible pour {current_user.email}")
    return {
        "success": True,
        "message": "Endpoint accessible",
        "user": current_user.email
    }


@router.post("/test-upload-file")
async def test_upload_file_endpoint(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de test pour vérifier que l'upload de fichier fonctionne
    Accepte n'importe quel fichier et retourne juste sa taille
    """
    logger.info(f"📥 ===== TEST UPLOAD FILE REÇU =====")
    logger.info(f"📥 URL: {request.url}")
    logger.info(f"📥 Method: {request.method}")
    logger.info(f"📥 Headers: {dict(request.headers)}")
    logger.info(f"📥 Filename: {file.filename if file.filename else 'N/A'}")
    
    try:
        # Lire juste les premiers bytes pour tester
        content = await file.read()
        file_size = len(content)
        
        logger.info(f"✅ Fichier reçu: {file.filename}, taille: {file_size} bytes")
        
        return {
            "success": True,
            "message": "Fichier reçu avec succès",
            "filename": file.filename,
            "size": file_size,
            "user": current_user.email
        }
    except Exception as e:
        logger.error(f"❌ Erreur dans test-upload-file: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du test: {str(e)}"
        )


@router.get("/models")
async def get_ollama_models(current_user: User = Depends(get_current_user)):
    """
    Récupère la liste des modèles disponibles dans Ollama
    
    Args:
        current_user: L'utilisateur actuel (authentifié)
    
    Returns:
        Liste des modèles disponibles
    """
    try:
        ollama_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
        ollama_api_url = f"{ollama_url}/api/tags"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(ollama_api_url)
                response.raise_for_status()
                
                result = response.json()
                models = [model.get("name", "") for model in result.get("models", [])]
                
                return {
                    "success": True,
                    "models": models
                }
                
            except httpx.RequestError as e:
                logger.error(f"Erreur de connexion Ollama: {e}")
                return {
                    "success": False,
                    "error": "Impossible de se connecter à Ollama",
                    "models": []
                }
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des modèles: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "models": []
                }
    
    except Exception as e:
        logger.error(f"Erreur inattendue dans get_ollama_models: {e}")
        return {
            "success": False,
            "error": str(e),
            "models": []
        }


@router.post("/upload-document-base64")
async def upload_chatbot_document_base64(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Upload un document pour le chatbot via base64 (contournement pour les fichiers Word bloqués par le proxy)
    
    Accepte un JSON avec:
    - filename: nom du fichier
    - file_data: contenu du fichier en base64
    - file_type: type MIME du fichier (optionnel)
    """
    try:
        body = await request.json()
        filename = body.get("filename")
        file_data_base64 = body.get("file_data")
        file_type = body.get("file_type", "")
        
        if not filename or not file_data_base64:
            raise HTTPException(status_code=400, detail="filename et file_data (base64) sont requis")
        
        # Décoder le base64
        import base64
        try:
            content = base64.b64decode(file_data_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erreur lors du décodage base64: {str(e)}")
        
        # Vérifier le type de fichier
        filename_lower = filename.lower()
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.md']
        
        if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=400,
                detail=f"Type de fichier non supporté. Types acceptés: {', '.join(allowed_extensions)}"
            )
        
        # Vérifier la taille (max 10 MB)
        MAX_SIZE = 10 * 1024 * 1024  # 10 MB
        file_size = len(content)
        
        if file_size > MAX_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Fichier trop volumineux (max 10 MB, reçu {file_size / (1024*1024):.2f} MB)"
            )
        
        if not content:
            raise HTTPException(status_code=400, detail="Le fichier est vide.")
        
        # Générer un nom de fichier unique
        extension = Path(filename).suffix.lower()
        if not extension:
            extension = ".txt"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{uuid4().hex[:8]}{extension}"
        
        # Créer le dossier pour les documents du chatbot
        docs_dir = path_config.UPLOADS_DIR / "chatbot" / "documents"
        path_config.ensure_directory_exists(docs_dir)
        
        # Sauvegarder le fichier
        destination = docs_dir / unique_filename
        destination.write_bytes(content)
        
        # Générer les chemins relatifs et URL
        relative_path = f"chatbot/documents/{unique_filename}"
        file_url = path_config.get_file_url("uploads", relative_path)
        
        # Extraire le texte
        logger.info(f"🔍 Extraction du texte pour {filename} (type: {extension})...")
        try:
            text = DocumentExtractor.extract_text_from_content(content, filename)
            logger.info(f"✅ Texte extrait: {len(text) if text else 0} caractères")
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'extraction du texte: {e}", exc_info=True)
            if destination.exists():
                destination.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors de l'extraction du texte: {str(e)}"
            )
        
        if not text or len(text.strip()) == 0:
            logger.warning(f"⚠️ Document vide: {filename}")
            if destination.exists():
                destination.unlink()
            raise HTTPException(
                status_code=400,
                detail="Le document ne contient pas de texte extractible."
            )
        
        # Logger l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="upload",
            target_type="chatbot_document",
            description=f"Upload d'un document pour le chatbot ({filename}) via base64",
            icon="📄",
        )
        
        logger.info(f"✅ Document traité et sauvegardé: {filename} ({len(text)} caractères)")
        
        return {
            "success": True,
            "filename": filename,
            "saved_filename": unique_filename,
            "path": relative_path,
            "url": file_url,
            "file_size": file_size,
            "text": text,
            "text_length": len(text)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors de l'upload du document (base64): {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement du document: {str(e)}"
        )


@router.post("/test-upload-raw")
async def test_upload_raw(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de test qui lit le body brut pour diagnostiquer les problèmes de parsing multipart
    """
    logger.info(f"🔍 ===== TEST UPLOAD RAW (BODY BRUT) =====")
    logger.info(f"🔍 URL: {request.url}")
    logger.info(f"🔍 Method: {request.method}")
    logger.info(f"🔍 Content-Type: {request.headers.get('content-type', 'N/A')}")
    logger.info(f"🔍 Content-Length: {request.headers.get('content-length', 'N/A')}")
    logger.info(f"🔍 User: {current_user.email if current_user else 'N/A'}")
    
    try:
        # Lire le body brut
        body = await request.body()
        body_size = len(body)
        logger.info(f"📊 Body brut lu: {body_size} bytes")
        
        # Logger les premiers et derniers bytes
        if body_size > 0:
            logger.info(f"📊 Premiers 100 bytes (hex): {body[:100].hex()}")
            logger.info(f"📊 Premiers 100 bytes (repr): {repr(body[:100])}")
            if body_size > 100:
                logger.info(f"📊 Derniers 100 bytes (hex): {body[-100:].hex()}")
                logger.info(f"📊 Derniers 100 bytes (repr): {repr(body[-100:])}")
        
        # Essayer de parser manuellement le multipart
        content_type = request.headers.get('content-type', '')
        if 'multipart/form-data' in content_type:
            # Extraire le boundary
            boundary_match = content_type.split('boundary=')
            if len(boundary_match) > 1:
                boundary = boundary_match[1].strip()
                logger.info(f"📊 Boundary détecté: {boundary}")
                logger.info(f"📊 Boundary dans le body: {boundary.encode() in body}")
        
        return {
            "success": True,
            "body_size": body_size,
            "content_type": content_type,
            "message": "Body brut lu avec succès",
            "first_bytes_hex": body[:50].hex() if body_size > 0 else None
        }
    except Exception as e:
        logger.error(f"❌ Erreur lors de la lecture du body brut: {e}", exc_info=True)
        logger.error(f"❌ Type d'erreur: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/warmup")
async def warmup_chatbot(
    current_user: User = Depends(get_current_user)
):
    """
    Préchauffe le chatbot Ollama en arrière-plan.
    
    Cette fonction charge le modèle Ollama en mémoire pour réduire
    la latence lors des premiers appels de l'utilisateur.
    
    Args:
        current_user: L'utilisateur actuel (authentifié)
    
    Returns:
        Statut du préchauffage
    """
    try:
        from app.services.chatbot_warmup_service import ChatbotWarmupService
        
        # Lancer le préchauffage en arrière-plan (non-bloquant)
        import asyncio
        asyncio.create_task(ChatbotWarmupService.warmup_model())
        
        return {
            "success": True,
            "message": "Préchauffage du chatbot lancé en arrière-plan"
        }
    except Exception as e:
        logger.error(f"❌ Erreur lors du préchauffage: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/test-upload-minimal")
async def test_upload_minimal(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),  # Garder l'auth pour cohérence
):
    """
    Endpoint de test minimal - accepte n'importe quel fichier sans validation
    Pour diagnostiquer les problèmes d'upload
    """
    logger.info(f"🔍 ===== TEST UPLOAD MINIMAL =====")
    logger.info(f"🔍 URL: {request.url}")
    logger.info(f"🔍 Method: {request.method}")
    logger.info(f"🔍 Content-Type: {request.headers.get('content-type', 'N/A')}")
    logger.info(f"🔍 Content-Length: {request.headers.get('content-length', 'N/A')}")
    logger.info(f"🔍 User: {current_user.email if current_user else 'N/A'}")
    
    try:
        # Essayer de lire le fichier
        logger.info(f"📤 Tentative de lecture du fichier: {file.filename}")
        logger.info(f"📤 File Content-Type: {file.content_type}")
        logger.info(f"📤 File Headers: {dict(file.headers) if hasattr(file, 'headers') else 'N/A'}")
        
        content = await file.read()
        file_size = len(content)
        logger.info(f"📊 Fichier lu avec succès: {file_size} bytes")
        
        # Vérifier les premiers bytes pour identifier le type réel
        if content:
            first_bytes = content[:20]
            logger.info(f"📊 Premiers bytes (hex): {first_bytes.hex()}")
            logger.info(f"📊 Premiers bytes (repr): {repr(first_bytes)}")
        
        return {
            "success": True,
            "filename": file.filename,
            "size": file_size,
            "content_type": file.content_type,
            "message": "Fichier reçu avec succès",
            "first_bytes_hex": content[:20].hex() if content else None
        }
    except Exception as e:
        logger.error(f"❌ Erreur lors de la lecture du fichier: {e}", exc_info=True)
        logger.error(f"❌ Type d'erreur: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.post("/upload-document")
async def upload_chatbot_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Upload un document pour le chatbot, le sauvegarde et extrait son texte
    
    Le document est sauvegardé dans uploads/chatbot/documents/ et son texte est extrait
    pour être utilisé dans la conversation du chatbot.
    
    Args:
        file: Fichier à uploader (PDF, Word, TXT, MD)
        current_user: Utilisateur actuel
        session: Session de base de données
        
    Returns:
        Texte extrait du document et informations sur le fichier sauvegardé
    """
    # TODO: Retirer ce log de debug après résolution du problème
    logger.info(f"🔍 ===== UPLOAD DOCUMENT ENDPOINT APPELÉ =====")
    logger.info(f"🔍 URL: {request.url}")
    logger.info(f"🔍 Method: {request.method}")
    logger.info(f"🔍 Headers: {dict(request.headers)}")
    logger.info(f"🔍 Content-Type: {request.headers.get('content-type', 'N/A')}")
    logger.info(f"🔍 Content-Length: {request.headers.get('content-length', 'N/A')}")
    
    try:
        logger.info(f"📤 ===== UPLOAD DOCUMENT DÉBUT =====")
        logger.info(f"📤 Upload de document reçu: {file.filename if file.filename else 'N/A'} par {current_user.email}")
        logger.info(f"📤 File Content-Type: {file.content_type if hasattr(file, 'content_type') else 'N/A'}")
        logger.info(f"📤 File Headers: {dict(file.headers) if hasattr(file, 'headers') else 'N/A'}")
        
        # Vérifier le type de fichier
        if not file.filename:
            logger.warning("⚠️ Nom de fichier manquant")
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        filename_lower = file.filename.lower()
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.md']
        
        if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
            logger.warning(f"⚠️ Type de fichier non supporté: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Type de fichier non supporté. Types acceptés: {', '.join(allowed_extensions)}"
            )
        
        # Vérifier la taille (max 10 MB)
        MAX_SIZE = 10 * 1024 * 1024  # 10 MB
        content = await file.read()
        file_size = len(content)
        logger.info(f"📊 Taille du fichier: {file_size / 1024:.2f} KB")
        
        if file_size > MAX_SIZE:
            logger.warning(f"⚠️ Fichier trop volumineux: {file_size / (1024*1024):.2f} MB")
            raise HTTPException(
                status_code=400,
                detail=f"Fichier trop volumineux (max 10 MB, reçu {file_size / (1024*1024):.2f} MB)"
            )
        
        if not content:
            raise HTTPException(status_code=400, detail="Le fichier est vide.")
        
        # Générer un nom de fichier unique
        extension = Path(file.filename).suffix.lower()
        if not extension:
            extension = ".txt"  # Par défaut si pas d'extension
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{uuid4().hex[:8]}{extension}"
        
        # Créer le dossier pour les documents du chatbot
        docs_dir = path_config.UPLOADS_DIR / "chatbot" / "documents"
        path_config.ensure_directory_exists(docs_dir)
        
        # Sauvegarder le fichier
        destination = docs_dir / unique_filename
        destination.write_bytes(content)
        
        # Générer les chemins relatifs et URL
        relative_path = f"chatbot/documents/{unique_filename}"
        file_url = path_config.get_file_url("uploads", relative_path)
        
        # Extraire le texte directement depuis le contenu
        logger.info(f"🔍 Extraction du texte pour {file.filename} (type: {Path(file.filename).suffix.lower()})...")
        try:
            text = DocumentExtractor.extract_text_from_content(content, file.filename)
            logger.info(f"✅ Texte extrait: {len(text) if text else 0} caractères")
            if not text or len(text.strip()) == 0:
                logger.warning(f"⚠️ Texte extrait mais vide pour {file.filename}")
        except ImportError as e:
            logger.error(f"❌ Bibliothèque manquante: {e}", exc_info=True)
            # Supprimer le fichier si l'extraction échoue
            if destination.exists():
                destination.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Bibliothèques manquantes pour traiter ce type de fichier. Installez python-docx pour Word (pip install python-docx) ou PyPDF2/pdfplumber pour PDF (pip install PyPDF2 ou pip install pdfplumber)."
            )
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'extraction du texte: {e}", exc_info=True)
            # Supprimer le fichier si l'extraction échoue
            if destination.exists():
                destination.unlink()
            error_msg = str(e)
            if "python-docx" in error_msg.lower() or "docx" in error_msg.lower():
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur lors de l'extraction du texte Word: {error_msg}. Vérifiez que python-docx est installé (pip install python-docx)."
                )
            elif "pdf" in error_msg.lower() or "pypdf" in error_msg.lower():
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur lors de l'extraction du texte PDF: {error_msg}. Vérifiez que PyPDF2 ou pdfplumber est installé."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur lors de l'extraction du texte: {error_msg}"
                )
        
        if not text:
            logger.warning(f"⚠️ Aucun texte extrait de {file.filename}")
            # Supprimer le fichier si aucun texte n'a été extrait
            if destination.exists():
                destination.unlink()
            raise HTTPException(
                status_code=400,
                detail="Impossible d'extraire le texte du document. Vérifiez que le fichier n'est pas corrompu ou protégé par mot de passe."
            )
        
        if len(text.strip()) == 0:
            logger.warning(f"⚠️ Document vide: {file.filename}")
            # Supprimer le fichier si le document est vide
            if destination.exists():
                destination.unlink()
            raise HTTPException(
                status_code=400,
                detail="Le document ne contient pas de texte extractible."
            )
        
        # Logger l'activité
        ActivityService.log_activity(
            db_session=session,
            user_id=current_user.id,
            user_email=current_user.email,
            user_full_name=current_user.full_name,
            action_type="upload",
            target_type="chatbot_document",
            description=f"Upload d'un document pour le chatbot ({file.filename})",
            icon="📄",
        )
        
        logger.info(f"✅ Document sauvegardé: {unique_filename} ({len(text)} caractères)")
        logger.info(f"📤 ===== UPLOAD DOCUMENT SUCCÈS =====")
        
        return {
            "success": True,
            "filename": file.filename,
            "saved_filename": unique_filename,
            "path": relative_path,
            "url": file_url,
            "text": text,
            "text_length": len(text),
            "file_size": file_size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors de l'upload du document: {e}", exc_info=True)
        logger.info(f"📤 ===== UPLOAD DOCUMENT ÉCHEC (Exception) =====")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du traitement du document: {str(e)}"
        )

