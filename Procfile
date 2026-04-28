web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn playto.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60
worker: celery -A playto worker -Q payouts,scheduled --concurrency=2 --without-mingle --without-gossip -l info
beat: celery -A playto beat -l info
