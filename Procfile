release: python manage.py migrate --noinput && python manage.py create_admin
web: gunicorn dropshipping.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
