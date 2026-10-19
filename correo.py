import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def enviar_correo(destinatario, asunto, cuerpo):
    """Envía un correo de texto por SMTP. Devuelve True si se ha enviado.

    En Docker, MAIL_SERVER apunta al contenedor Mailpit (sin TLS ni login).
    Con un servidor real (Gmail, etc.) se activa MAIL_USE_TLS y se indican
    MAIL_USERNAME / MAIL_PASSWORD.

    Si el servidor SMTP no está configurado o falla, la aplicación no se
    interrumpe: el error se muestra por consola.
    """
    servidor = os.getenv('MAIL_SERVER')
    if not servidor:
        print(f'[correo] MAIL_SERVER no configurado. Correo a {destinatario}: {asunto}')
        return False

    usuario = os.getenv('MAIL_USERNAME', '')
    usar_tls = os.getenv('MAIL_USE_TLS', 'false').lower() == 'true'

    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = os.getenv('MAIL_FROM') or usuario or 'tienda@tienda.local'
    msg['To'] = destinatario
    msg.set_content(cuerpo)

    try:
        with smtplib.SMTP(servidor, int(os.getenv('MAIL_PORT', '587')), timeout=10) as smtp:
            if usar_tls:
                smtp.starttls()
            if usuario:
                smtp.login(usuario, os.getenv('MAIL_PASSWORD', ''))
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f'[correo] Error al enviar a {destinatario}: {e}')
        return False
