# Playto Payout Engine

A robust, production-ready fintech payout engine built with Django, PostgreSQL, Celery, Redis, and React. 

## Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd playto-payout
   ```

2. **Environment Variables**:
   ```bash
   cp .env.example .env
   ```

3. **Start Infrastructure**:
   Spin up PostgreSQL and Redis:
   ```bash
   docker-compose up -d
   ```

4. **Install Backend Dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Run Migrations & Seed Data**:
   ```bash
   python manage.py migrate
   python manage.py seed_data
   ```

6. **Install Frontend Dependencies**:
   ```bash
   cd frontend
   npm install
   ```

## Running the full stack

You need to run 4 processes simultaneously:

1. **Django API Server**:
   ```bash
   python manage.py runserver
   ```
2. **Celery Worker** (Processes payouts):
   ```bash
   celery -A playto worker -l INFO -Q payouts,scheduled
   ```
3. **Celery Beat** (Runs the reaper for stuck payouts):
   ```bash
   celery -A playto beat -l INFO
   ```
4. **React Dev Server**:
   ```bash
   cd frontend
   npm run dev
   ```

