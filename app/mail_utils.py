"""
Send Mail Utility

For easy of using ensure both send_mail* has same signature
"""

from pathlib import Path
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate
import hashlib
import json
from smtplib import SMTP
import base64
from datetime import datetime
from typing import Optional

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


from app.utils import get_unsent_mail_dir

def create_email(
        to: str,
        subject: str,
        body: str,
        from_email: str,
        body_format: str='plain',
        attachments: Optional[list[str]]=None,
        signature: str=''
    ) -> MIMEMultipart:

    file_attachments = attachments or []

    # creating mail
    mime_message = MIMEMultipart()
    mime_message['From'] = from_email
    mime_message['To'] = to
    mime_message['Subject'] = subject
    mime_message['Date'] = formatdate(localtime=True)

    if not signature:
        signature = '\n\n--\nThanks'

    # attaching body, subsequent attach will be attachments
    mime_message.attach(MIMEText(body + signature, body_format))

    for attachment_path in file_attachments:
        attachment_path = Path(attachment_path)
        if not attachment_path.exists():
            print(f"Warning: Attachement not found: {attachment_path}")
            continue

        # guess file type (like image/jpeg, application/pdf)
        # solely depends on file extension
        # good to have, one soln - predict filetype using python-magic (a wrapper around linux libmagic)
        content_type, _ = mimetypes.guess_type(attachment_path)

        # if not known, label as generic binary data
        if content_type is None:
            content_type = 'application/octet-stream'

        main_type, sub_type = content_type.split('/', 1)
        file_name = attachment_path.name

        with open(attachment_path, 'rb') as f:
            file_bag = MIMEBase(main_type, sub_type)
            file_bag.set_payload(f.read())
            # label it as an attachement
            file_bag.add_header('Content-Disposition', str(attachment_path), filename=file_name)
            # encode data to text(base64)
            encoders.encode_base64(file_bag)

        mime_message.attach(file_bag)

    return mime_message

def save_mail_as_json(
        to: str,
        subject: str,
        body: str,
        body_format: str,
        attachments: Optional[list[str]]=None,
        exception: Optional[Exception]=None
    ) -> None:

    unsent_mail = {}
    unsent_mail['to'] = to
    unsent_mail['subject'] = subject
    unsent_mail['body'] = body
    unsent_mail['body_format'] = body_format
    unsent_mail['attchments'] = attachments
    unsent_mail['exception'] = exception

    unsent_mail_dir = get_unsent_mail_dir()
    unsent_mail_dir.mkdir(parents=True, exist_ok=True)
    timestamp = f'{datetime.now():%Y_%m_%d__%H_%M_%S}'
    body_hash = hashlib.sha256(body.encode()).hexdigest()[10:30]
    filename = f'{timestamp}__{body_hash}.json'
    save_file_path = unsent_mail_dir / filename
    with open(save_file_path, 'w') as file:
        json.dump(unsent_mail, file)

smtp_server = 'smtp.dreamhost.com'
smtp_port = 587
smtp_username = 'user@domain.com'
smtp_password = 'password'
smtp_from_email = 'user@domain.com'
DEFAULT_SIGNATURE = '\n\nThanks & Regards,\nOrganizing Team'

# raw_string
# SMTP requires MIMEMultiPart.as_string() - human readable
# GMAIL requires safer string encoded - not human readbale

def send_mail_smtp(to, subject, body, body_format='plain', attachments=None):
    try:
        mime_message = create_email(to, subject, body,
            smtp_from_email, body_format, attachments)
        raw_string = mime_message.as_string()

        server = SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_from_email, to, raw_string)
        server.quit()

    except Exception as e:
        print(f"Error while sending mail: {e}")
        save_mail_as_json(to, subject, body, body_format, attachments)

        return {'status': 'error', 'details': str(e)}

    return {'status': 'success', 'details': 'ok'}

# using gmail API
def send_mail_http(to, subject, body, body_format='plain', attachments=None):
    try:
        raise Exception("Development & Testing")
        # `me` - special alias for from email in gmail
        mime_message = create_email(to, subject, body,
            'me', body_format, attachments, DEFAULT_SIGNATURE)
        raw_string = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
        creds = None
        scopes = ['https://mail.google.com/']
        creds = Credentials.from_authorized_user_file('token.json', scopes)
        service = build('gmail', 'v1', credentials=creds)
        _ = service.users().messages().send(
            userId='me',
            body={'raw': raw_string}
        ).execute()
    except Exception as e:
        print(f"Error while sending mail: {e}")
        save_mail_as_json(to, subject, body, body_format, attachments, str(e))

        return {'status': 'error', 'details': str(e)}

    return {'status': 'success', 'details': 'ok'}
