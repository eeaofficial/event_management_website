"""
Global error handlers
"""

from flask import render_template

def register_error_handlers(app):
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('page_not_found.html')

    @app.errorhandler(405)
    def method_not_allowed(e):
        return render_template('method_not_allowed.html')
