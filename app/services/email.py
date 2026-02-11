import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import Config
import logging

logger = logging.getLogger(__name__)

def send_email(subject: str, body_html: str, recipients: list[str] = None) -> bool:
    """
    Send an HTML email via Gmail SMTP using app password.
    """
    if recipients is None:
        recipients = Config.EMAIL_RECIPIENTS

    if not recipients:
        logger.warning("No email recipients defined.")
        return False
        
    sender_email = Config.SENDER_EMAIL
    password = Config.GMAIL_APP_PASSWORD
    
    if not sender_email or not password:
        logger.error("Email credentials not set.")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = ", ".join(recipients)

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(body_html, "html")

    # Add HTML/plain-text parts to MIMEMessage
    # The email client will try to render the last part first
    message.attach(part1)

    # Create secure connection with server and send email
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(
                sender_email, recipients, message.as_string()
            )
        logger.info(f"Email sent to {recipients}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
