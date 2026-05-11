"""
QuickLender Settings Entrypoint
Loads dev or production settings based on DJANGO_ENV env var.
"""
import os

env = os.environ.get('DJANGO_ENV', 'development').lower()

if env == 'production':
    from quicklender_project.settings_modules.production import *
else:
    from quicklender_project.settings_modules.development import *
