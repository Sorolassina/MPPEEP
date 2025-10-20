"""
Fonctions utilitaires pour l'envoi d'emails
"""

import logging

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
    Envoie un email

    Args:
        to_email: Email(s) destinataire(s)
        subject: Sujet de l'email
        body: Contenu texte brut
        html_body: Contenu HTML (optionnel)
        from_email: Email expéditeur
        from_name: Nom expéditeur

    Returns:
        True si envoyé avec succès, False sinon

    Example:
        await send_email(
            "user@example.com",
            "Bienvenue !",
            "Contenu de l'email"
        )
    """
    try:
        # TODO: Implémenter l'envoi réel d'email
        # Options : SMTP, SendGrid, AWS SES, Mailgun, etc.

        # Pour l'instant, juste logger
        logger.info(f"📧 Email envoyé à {to_email}: {subject}")
        print("📧 Email simulé:")
        print(f"   To: {to_email}")
        print(f"   Subject: {subject}")
        print(f"   Body: {body[:100]}...")

        return True

    except Exception as e:
        logger.error(f"❌ Erreur envoi email: {e}")
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
