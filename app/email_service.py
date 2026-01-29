import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import os

def send_email(to_email, subject, html_content):
    config = sib_api_v3_sdk.Configuration()
    config.api_key['api-key'] = os.getenv("BREVO_API_KEY")

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(config)
    )

    sender = {
        "email": os.getenv("SENDER_EMAIL"),
        "name": "EEA Association"
    }

    to = [{"email": to_email}]

    email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content
    )

    try:
        api_instance.send_transac_email(email)
        print("Email sent to", to_email)
        return True
    except ApiException as e:
        print("Email sending failed:", e)
        return False
