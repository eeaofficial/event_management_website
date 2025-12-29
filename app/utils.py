"""
Utility functions
"""

from pathlib import Path
import random
import string

from PIL import Image
from flask_login import current_user
from werkzeug.datastructures import FileStorage
from flask import current_app

def get_upload_dir() -> Path:
    return Path(current_app.config['UPLOAD_FOLDER']).resolve()

def get_static_dir() -> Path:
    return Path(current_app.static_folder).resolve()

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
        if '201950' in reg_no or '202050' in reg_no or '202150' in reg_no or '202250' in reg_no:
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
        category:str='',
        size:tuple[int]=(500,500)
    ) -> tuple[bool, str, str]:
    """
        image is a FileStorage object
        category is used to store images separately
        category will be the subdirectory in static/images/<>

        File extension will be preserved as that of the image object

        Return 
        (bool, str, str): success status, message, relative path to store to fetch the file
    """

    if not image:
        return (False, 'No image provided', '')

    valid_size = len(size)==2 and isinstance(size[0], float) and isinstance(size[1], float)
    if not valid_size:
        size = (500, 500)

    res_dir = get_upload_dir() / category
    res_dir.mkdir(parents=True, exist_ok=True)

    filename = make_valid_file_name(filename)
    if not filename:
        return (False, 'Invalid file name', '')

    img_ext = Path(image.filename).suffix
    filename = f'{filename}{img_ext}'
    file_path = res_dir / filename

    img = Image.open(image)
    img = img.resize(size)
    img.save(file_path)
    img.close()

    if file_path.exists():
        return (True, 'success',filename)

    return (False, 'Error saving image', '')

def random_string(length: int=5) -> str:
    """
    Generate a random string of fixed length
    """
    letters = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(letters) for _ in range(length))
    return result_str
