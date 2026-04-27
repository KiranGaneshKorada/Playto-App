.PHONY: install migrate seed worker beat dev frontend

install:
	pip install -r requirements.txt

migrate:
	python manage.py migrate

seed:
	python manage.py seed_data

worker:
	celery -A playto worker --queues=payouts,scheduled --concurrency=4 -l info

beat:
	celery -A playto beat --scheduler django_celery_beat.schedulers:DatabaseScheduler -l info

dev:
	python manage.py runserver

frontend:
	cd frontend && npm run dev
