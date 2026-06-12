import threading
import smtplib
import ssl
from django.core.mail import send_mail
from django.conf import settings


def _envoyer_email_identifiants(username, email, first_name, mot_de_passe, role_label):
    """Envoi synchrone de l'email — appelé depuis un thread."""
    try:
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            print("Email non envoyé : EMAIL_HOST_USER ou EMAIL_HOST_PASSWORD manquant.")
            return False, "Configuration SMTP manquante."

        # Contexte SSL sans vérification stricte du certificat (contourne CERTIFICATE_VERIFY_FAILED)
        import django.core.mail
        connection = django.core.mail.get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            use_ssl=getattr(settings, 'EMAIL_USE_SSL', False),
            timeout=settings.EMAIL_TIMEOUT,
            ssl_certfile=None,
            ssl_keyfile=None,
        )
        # Patch : désactiver la vérification du certificat SSL
        connection.ssl_context = ssl.create_default_context()
        connection.ssl_context.check_hostname = False
        connection.ssl_context.verify_mode = ssl.CERT_NONE

        send_mail(
            subject="GestImpôts — Vos identifiants de connexion",
            message=f"""Bonjour {first_name or username},

Votre compte a été créé sur le Système de Gestion des Impôts.

════════════════════════════════
  VOS IDENTIFIANTS
════════════════════════════════
  Utilisateur : {username}
  Mot de passe: {mot_de_passe}
  Rôle        : {role_label}
════════════════════════════════

Connectez-vous sur : http://localhost:4200/login

Cordialement,
GestImpôts""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
            connection=connection,
        )
        print(f"✅ Email envoyé à {email}")
        return True, None
    except smtplib.SMTPAuthenticationError:
        msg = "Échec d'authentification SMTP. Vérifiez EMAIL_HOST_USER et EMAIL_HOST_PASSWORD dans le .env."
        print(f"❌ {msg}")
        return False, msg
    except smtplib.SMTPException as e:
        msg = f"Erreur SMTP : {e}"
        print(f"❌ {msg}")
        return False, msg
    except Exception as e:
        msg = f"Erreur inattendue lors de l'envoi de l'email : {e}"
        print(f"❌ {msg}")
        return False, msg


def envoyer_identifiants_async(username, email, first_name, mot_de_passe, role_label):
    """Envoie l'email en arrière-plan pour ne pas bloquer la réponse API.
    
    Note : daemon=False garantit que le thread a le temps de s'exécuter
    même si la requête HTTP s'est terminée.
    """
    thread = threading.Thread(
        target=_envoyer_email_identifiants,
        args=(username, email, first_name, mot_de_passe, role_label),
        daemon=False,  # CORRIGÉ : False pour ne pas être tué avant l'envoi
    )
    thread.start()
    return True