"""
Utility functions
"""

from pathlib import Path
import random
import string
import cloudinary.uploader
from io import BytesIO
from PIL import Image
from flask_login import current_user
from werkzeug.datastructures import FileStorage
from flask import current_app

def get_upload_dir() -> Path:
    return Path(current_app.config['UPLOAD_FOLDER']).resolve()

def get_static_dir() -> Path:
    return Path(current_app.static_folder).resolve()

def get_unsent_mail_dir() -> Path:
    return get_static_dir() / 'unsent_mails'

# access codes for certain institution; can be extended following the idea used
def is_code_applicable() -> bool:
    """
    Check if special code is applicable for the user based on college and registration number
    """
    if not current_user.is_authenticated:
        return False

    reg_no = current_user.reg_no
    code_applicable = False

    if current_user.college == 'MIT':
        if '20225' in reg_no or '20235' in reg_no or '20245' in reg_no or '20255' in reg_no:
            code_applicable = True

    return code_applicable

def make_valid_file_name(filename: str) -> str:
    """
        Get Valid File Name
        TODO: add limit_size: int=100
    """

    illegal_chars = ['-', ' ', '/','\\', ':', '*', '?', '"', '<', '>', '|', '&']

    for i in illegal_chars:
        filename = filename.replace(i, '_')

    return filename

def save_image(
        image: FileStorage,
        filename: str,
        category: str = '',
        size: tuple[int] = (500, 500)
    ) -> tuple[bool, str, str]:

    """
    Upload image to Cloudinary instead of local storage.
    Returns (success, message, secure_url)
    """

    if not image:
        return (False, 'No image provided', '')

    # Validate size
    if not (len(size) == 2 and isinstance(size[0], int) and isinstance(size[1], int)):
        size = (500, 500)

    filename = make_valid_file_name(filename)
    if not filename:
        return (False, 'Invalid file name', '')

    try:
        # Open and resize image
        img = Image.open(image)
        img = img.resize(size)

        # Save resized image to memory instead of disk
        buffer = BytesIO()
        img_format = img.format if img.format else "PNG"
        img.save(buffer, format=img_format)
        buffer.seek(0)
        img.close()

        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            buffer,
            folder=f"electrofocus/{category}",
            public_id=filename,
            overwrite=True
        )

        return (True, 'success', upload_result["secure_url"])

    except Exception as e:
        return (False, f'Error uploading image: {str(e)}', '')

def random_string(length: int=5) -> str:
    """
    Generate a random string of fixed length
    """
    letters = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(letters) for _ in range(length))
    return result_str
