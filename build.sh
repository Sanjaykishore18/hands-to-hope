#!/usr/bin/env bash
# build.sh — Render build script for HandsToHope Django app
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate

# Automatically create a superuser if it doesn't exist
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model

User = get_user_model()
admin_email = os.environ.get('DJANGO_ADMIN_EMAIL', 'admin@handstohope.com')
admin_password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'Admin@123')

if not User.objects.filter(email=admin_email).exists():
    User.objects.create_superuser(email=admin_email, password=admin_password)
    print(f'Superuser {admin_email} created successfully.')
else:
    print(f'Superuser {admin_email} already exists.')
"
