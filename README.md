# Resume Analyzer ATS

Resume Analyzer ATS is a production-ready Django platform that helps HR teams manage job positions, collect candidate applications, and leverage Cohere-powered AI analysis to assess resume fit. The system supports asynchronous resume processing with Celery, Redis, and MySQL, and ships with a modern Tailwind-based dashboard optimized for both light and dark themes.

## Features
- **Modular Django architecture** with dedicated apps for users, jobs, applications, AI analysis, and the dashboard UI.
- **Custom user model** with HR/Admin roles and per-user AI configuration (model, temperature, extraction toggles).
- **Job management**: create, edit, delete, and import job postings by scraping external URLs and enriching them via Cohere structured outputs.
- **Application workflow**: upload resumes, edit candidate details, track status transitions (submitted → interviews → accepted/rejected), and download originals.
- **AI resume insights**: asynchronous Celery tasks extract resume text, call Cohere for match score, summary, and improvement suggestions, and store results for review.
- **Dashboard experience**: Tailwind CSS with gold accent theme, responsive layout, dark/light mode, KPI snapshots, filters, and search.
- **API-ready core**: DRF serializers and services cleanly separate business logic, enabling future REST or GraphQL endpoints.
- **Dockerized deployment**: Docker Compose stack with Django, Celery worker, Celery beat, Redis, and MySQL.

## Project Structure
```
resume_analyzer/
├── core/                # Shared base models, celery config, utilities
├── users/               # Custom User model, AI settings, auth views/forms
├── jobs/                # JobPosition model, forms, services, import logic
├── applications/        # Application model, forms, resume extraction utils
├── analyzer/            # Cohere integration services and Celery tasks
├── dashboard/           # Tailwind-powered templates and views
├── resume_analyzer/     # Django settings, URLs, WSGI/ASGI, celery app
├── requirements.txt
├── Dockerfile
├── docker-compose.yml   # (ensure present in repo)
└── README.md
```

## Prerequisites
- Python 3.11+
- Node-less Tailwind usage (CDN) for templates
- Redis (for Celery broker/result backend)
- MySQL (default database in Docker stack)

For local-only experiments you can run SQLite, but async processing still requires Redis.

## Quick Start (Local Development)
1. **Clone and enter the project directory**
   ```bash
   git clone <repo-url>
   cd ATS-project
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # macOS/Linux
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure environment variables** (copy `.env.example` to `.env` if provided, otherwise set manually):
   ```bash
   set DJANGO_SECRET_KEY=your-secret-key
   set DEBUG=1
   set DB_ENGINE=django.db.backends.mysql
   set DB_NAME=resume_analyzer
   set DB_USER=root
   set DB_PASSWORD=your-password
   set DB_HOST=localhost
   set DB_PORT=3306
   set CELERY_BROKER_URL=redis://localhost:6379/0
   set CELERY_RESULT_BACKEND=redis://localhost:6379/0
   set COHERE_API_KEY=your-cohere-api-key
   set COHERE_DEFAULT_MODEL=command-a-03-2025
   set COHERE_DEFAULT_TEMPERATURE=0.15
   ```
   Adjust the syntax for your shell/OS.

4. **Apply migrations and create a superuser**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Run supporting services**
   - Start Redis (e.g., `redis-server` locally or via Docker `docker run -p 6379:6379 redis:7`)
   - Start Celery worker in a second terminal:
     ```bash
     .venv\Scripts\activate
     celery -A resume_analyzer worker -l info
     ```
   - Optionally run Celery beat for scheduled tasks:
     ```bash
     celery -A resume_analyzer beat -l info
     ```

6. **Start the Django development server**
   ```bash
   python manage.py runserver
   ```

Visit `http://127.0.0.1:8000/` for the dashboard and `http://127.0.0.1:8000/admin/` for the Django admin.

## Docker Compose Workflow
1. Ensure Docker Desktop (or equivalent) is running.
2. Build and start all services:
   ```bash
   docker compose up --build
   ```
3. The stack launches:
   - `web`: Django application
   - `worker`: Celery worker
   - `beat`: Celery beat scheduler
   - `db`: MySQL 8
   - `redis`: Redis broker/result backend

Environment variables in `docker-compose.yml` point to `.env`. Run migrations inside the `web` container if not automated:
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

## Celery & Async Flow
- When HR uploads a resume, `Application` is created, resume text is extracted (`applications.utils.extract_resume_text`), and the async task `analyze_application_task` is triggered.
- Celery worker calls Cohere (`analyzer.services.analyze_resume_with_cohere`) and stores the results in `ResumeAnalysis`.
- Application status automatically transitions (e.g., to `processing` while analysis runs, `analyzed` on success, or `needs_review` on failure).

## Cohere Integration
- API key is read from `settings.COHERE_API_KEY` or per-user overrides via `UserAISettings`.
- Default model is `command-a-03-2025`; users may customize models/temperatures in the dashboard under **AI Settings**.
- Structured JSON output is enforced with `response_format={"type": "json_object"}` and validated before persisting.

## Dashboard Highlights
- Overview page with KPI cards, recent jobs, and recent applications.
- Job list/detail pages enabling creation, import (web scrape + Cohere enrichment), editing, deletion.
- Application list/detail pages with search/filtering, editable candidate info, status workflow, AI insights display.
- AI Settings page with tabbed interface for job import vs resume analysis preferences.
- Tailwind styling with gold accent (`brand`) and consistent button treatment across light/dark themes.

## Running Tests
Add unit tests as the project evolves. Example command:
```bash
python manage.py test
```

## Contributing
1. Fork the repository and create a feature branch.
2. Follow the existing code style and ensure linters/tests pass.
3. Submit a pull request with a clear description of changes and testing steps.

## License
Specify your project license here (e.g., MIT, Apache 2.0). Replace this section with the correct license information before release.
