"""
Route modules for the tournament application
"""

from .public_routes import public_bp
from .admin_routes import admin_bp

__all__ = ['public_bp', 'admin_bp']
