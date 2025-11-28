"""
Fonctions utilitaires pour l'envoi d'emails
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    to_email: str | list[str],
    subject: str,
    body: str,
    html_body: str | None = None,
    from_email: str | None = None,
    from_name: str | None = None,
) -> bool:
    """
    Envoie un email via SendGrid (si configuré) ou en mode simulation

    Args:
        to_email: Email(s) destinataire(s)
        subject: Sujet de l'email
        body: Contenu texte brut
        html_body: Contenu HTML (optionnel)
        from_email: Email expéditeur (utilise SENDGRID_FROM_EMAIL si non fourni)
        from_name: Nom expéditeur (utilise SENDGRID_FROM_NAME si non fourni)

    Returns:
        True si envoyé avec succès, False sinon

    Example:
        await send_email(
            "user@example.com",
            "Bienvenue !",
            "Contenu de l'email"
        )
    """
    # Normaliser les emails (toujours une liste)
    if isinstance(to_email, str):
        to_email_list = [to_email]
    else:
        to_email_list = to_email

    # Déterminer l'expéditeur
    from_email_final = from_email or settings.SENDGRID_FROM_EMAIL
    from_name_final = from_name or settings.SENDGRID_FROM_NAME

    # Priorité 1: SendGrid si configuré
    if settings.SENDGRID_API_KEY:
        return await _send_via_sendgrid(
            to_email_list=to_email_list,
            subject=subject,
            body=body,
            html_body=html_body,
            from_email=from_email_final,
            from_name=from_name_final,
        )

    # Priorité 2: SMTP si configuré (TODO: implémenter SMTP)
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        logger.warning("⚠️  SMTP configuré mais non implémenté, passage en mode simulation")
        # TODO: Implémenter l'envoi SMTP
        # return await _send_via_smtp(...)

    # Mode simulation (pour dev/debug)
    logger.info(f"📧 [SIMULATION] Email envoyé à {', '.join(to_email_list)}: {subject}")
    if settings.DEBUG:
        print("=" * 60)
        print("📧 EMAIL SIMULÉ (mode développement)")
        print("=" * 60)
        print(f"De: {from_name_final} <{from_email_final or 'non configuré'}>")
        print(f"À: {', '.join(to_email_list)}")
        print(f"Sujet: {subject}")
        print(f"Corps texte:\n{body[:200]}...")
        if html_body:
            print(f"Corps HTML: [présent, {len(html_body)} caractères]")
        print("=" * 60)
    return True


async def _send_via_sendgrid(
    to_email_list: list[str],
    subject: str,
    body: str,
    html_body: str | None = None,
    from_email: str = "",
    from_name: str = "",
) -> bool:
    """
    Envoie un email via SendGrid API

    Args:
        to_email_list: Liste des emails destinataires
        subject: Sujet de l'email
        body: Contenu texte brut
        html_body: Contenu HTML (optionnel)
        from_email: Email expéditeur
        from_name: Nom expéditeur

    Returns:
        True si envoyé avec succès, False sinon
    """
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, Content

        # Vérifier que l'email expéditeur est configuré
        if not from_email:
            logger.error("❌ SENDGRID_FROM_EMAIL non configuré dans les paramètres")
            return False

        # Créer le client SendGrid
        sg = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)

        # Préparer l'email
        from_email_obj = Email(from_email, from_name) if from_name else Email(from_email)

        # Créer l'objet Mail
        message = Mail(
            from_email=from_email_obj,
            to_emails=to_email_list,
            subject=subject,
            plain_text_content=body,
        )

        # Ajouter le contenu HTML si présent
        if html_body:
            message.html_content = html_body

        # Envoyer l'email
        response = sg.send(message)

        # Vérifier le statut de la réponse
        if 200 <= response.status_code < 300:
            logger.info(f"✅ Email envoyé via SendGrid à {', '.join(to_email_list)}: {subject}")
            logger.debug(f"   Status: {response.status_code}")
            return True
        else:
            logger.error(
                f"❌ Erreur SendGrid (status {response.status_code}): {response.body.decode('utf-8') if response.body else 'Pas de détails'}"
            )
            return False

    except ImportError:
        logger.error("❌ Package sendgrid non installé. Installez-le avec: pip install sendgrid")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'envoi via SendGrid: {e}", exc_info=True)
        return False


async def send_verification_email(email: str, verification_code: str) -> bool:
    """
    Envoie un email de vérification de compte

    Args:
        email: Email du destinataire
        verification_code: Code de vérification à 6 chiffres

    Returns:
        True si envoyé avec succès
    """
    subject = "Vérification de votre compte"
    body = f"""
Bonjour,

Votre code de vérification est : {verification_code}

Ce code expire dans 15 minutes.

Si vous n'avez pas demandé ce code, ignorez cet email.

Cordialement,
L'équipe
    """

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Vérification de votre compte</h2>
        <p>Votre code de vérification est :</p>
        <div style="background: #f0f0f0; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; border-radius: 8px;">
            {verification_code}
        </div>
        <p style="color: #666; font-size: 14px; margin-top: 20px;">
            Ce code expire dans 15 minutes.
        </p>
        <p style="color: #666; font-size: 12px; margin-top: 30px;">
            Si vous n'avez pas demandé ce code, ignorez cet email.
        </p>
    </body>
    </html>
    """

    return await send_email(email, subject, body, html_body)


async def send_password_reset_email(email: str, reset_code: str) -> bool:
    """
    Envoie un email de réinitialisation de mot de passe

    Args:
        email: Email du destinataire
        reset_code: Code de réinitialisation à 6 chiffres

    Returns:
        True si envoyé avec succès
    """
    subject = "Réinitialisation de votre mot de passe"
    body = f"""
Bonjour,

Vous avez demandé la réinitialisation de votre mot de passe.

Votre code de réinitialisation est : {reset_code}

Ce code expire dans 15 minutes.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email et votre mot de passe restera inchangé.

Cordialement,
L'équipe
    """

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Réinitialisation de votre mot de passe</h2>
        <p>Vous avez demandé la réinitialisation de votre mot de passe.</p>
        <p>Votre code de réinitialisation est :</p>
        <div style="background: #fff3cd; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; border-radius: 8px; border: 2px solid #ffc107;">
            {reset_code}
        </div>
        <p style="color: #666; font-size: 14px; margin-top: 20px;">
            Ce code expire dans 15 minutes.
        </p>
        <p style="color: #dc3545; font-size: 12px; margin-top: 30px;">
            Si vous n'avez pas demandé cette réinitialisation, ignorez cet email et votre mot de passe restera inchangé.
        </p>
    </body>
    </html>
    """

    return await send_email(email, subject, body, html_body)


# Configuration SMTP (à adapter selon vos besoins)
def configure_smtp(host: str, port: int, username: str, password: str, use_tls: bool = True):
    """
    Configure les paramètres SMTP pour l'envoi d'emails

    Example:
        configure_smtp(
            "smtp.gmail.com",
            587,
            "votre@email.com",
            "votre_mot_de_passe",
            use_tls=True
        )
    """
    # TODO: Implémenter la configuration SMTP
    pass
