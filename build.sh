#!/usr/bin/env bash
# build.sh — Render build script for HandsToHope Django app
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate
