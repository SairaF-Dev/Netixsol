"""
ShopKaro Configuration Module
=============================
Handles environment variables, application settings, database URIs, model artifact
paths, and service credentials for development, staging, and production environments.
"""

from shopkaro.config.settings import PROJECT_ROOT, Settings, settings

__all__ = [
    "PROJECT_ROOT",
    "Settings",
    "settings",
]
