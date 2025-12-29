"""
Sending Mail via HTTP
"""
import os
import base64
import hashlib
import json
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

import mimetypes
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app import static_dir

def send_mail_http(to, subject, body, format='plain', attachments=None, signature=''):
    file_attachments = attachments or []

    #create email
    mimeMessage = MIMEMultipart()
    mimeMessage['to'] = to
    mimeMessage['subject'] = subject
    #mimeMessage.attach(MIMEText(html,'html'))

    if not signature:
            # SIGNATURE
            signature = '''
Thanks & Regards,
Organizing Team
'''

    # expected signature and body same format
    mimeMessage.attach(MIMEText(body + signature, format))

    for attachment in file_attachments:
        content_type, encoding = mimetypes.guess_type(attachment)
        main_type, sub_type = content_type.split('/', 1)
        file_name = os.path.basename(attachment)

        with open(attachment, 'rb') as f:
            myFile = MIMEBase(main_type, sub_type)
            myFile.set_payload(f.read())
            myFile.add_header('Content-Disposition', attachment, filename=file_name)
            encoders.encode_base64(myFile)

        mimeMessage.attach(myFile)


    raw_string = base64.urlsafe_b64encode(mimeMessage.as_bytes()).decode()


    try:
        creds = None
        scopes = ['https://mail.google.com/']
        creds = Credentials.from_authorized_user_file('token.json', scopes)
        service = build('gmail', 'v1', credentials=creds)
        message = service.users().messages().send(
            userId='me',
            body={'raw': raw_string}
        ).execute()
    except Exception as e:
        message = f'An error occurred: {e}'

        unsent_mail = {}
        unsent_mail['to'] = to
        unsent_mail['subject'] = subject
        unsent_mail['body'] = body
        unsent_mail['attchments'] = attachments
        save_unsent_mail_directory = static_dir / 'unsent_mails'
        save_unsent_mail_directory.mkdir(parents=True, exist_ok=True)
        filename = f'{hashlib.sha256(body.encode()).hexdigest()[10:40]}.json'
        save_file_path = save_unsent_mail_directory / filename
        with open(save_file_path, 'w') as file:
            json.dump(unsent_mail, file)

    return message
