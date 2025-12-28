"""
Utility functions
"""

from pathlib import Path

from PIL import Image
from flask_login import current_user
from werkzeug.datastructures import FileStorage

from app import upload_dir

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

