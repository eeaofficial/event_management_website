"""
Sending Mail via SMTP 
"""

import smtplib
import os
import hashlib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate

import mimetypes

from app.utils import get_static_dir

smtp_server = 'smtp.dreamhost.com'
smtp_port = 587
smtp_username = 'user@domain.com'
smtp_password = 'password'

from_email = 'user@domain.com'

def send_mail(to, subject, body, format='plain', attachments=None, signature=''):
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)

        file_attachments = attachments or []

        #create email
        mimeMessage = MIMEMultipart()
        mimeMessage['From'] = 'user@domain.com'
        mimeMessage['To'] = to
        mimeMessage['Subject'] = subject
        mimeMessage['Date'] = formatdate(localtime=True)
        #mimeMessage.attach(MIMEText(html,'html'))
        if not signature:
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

        # raw_string = base64.urlsafe_b64encode(mimeMessage.as_bytes()).decode()
        # print(from_email)
        # print(to)
        # print(mimeMessage.as_string())
        server.sendmail(from_email, to, mimeMessage.as_string())
        server.quit()
        return 'success'
    except Exception as e:
        print('Mail Sending Error:', e)

        unsent_mail = {}
        unsent_mail['to'] = to
        unsent_mail['subject'] = subject
        unsent_mail['body'] = body
        unsent_mail['attchments'] = attachments
        save_unsent_mail_directory = get_static_dir() / 'unsent_mails'
        save_unsent_mail_directory.mkdir(parents=True, exist_ok=True)
        filename = f'{hashlib.sha256(body.encode()).hexdigest()[10:40]}.json'
        save_file_path = save_unsent_mail_directory / filename
        with open(save_file_path, 'w') as file:
            json.dump(unsent_mail, file)

        return 'error'
