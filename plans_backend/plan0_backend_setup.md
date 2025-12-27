# Plan 0: Backend Environment Setup & Project Structure

## Goal
Set up a production-ready Django backend environment with proper project structure, dependencies, environment configuration, and local development workflow that integrates with the CV Generator frontend.

## Scope
This plan covers:
- Django project initialization
- Environment configuration (settings, env vars)
- Docker setup (optional but recommended)
- Local development workflow
- Project structure and conventions

---

## CRITICAL RULES (MUST FOLLOW)

### LOCKED FILES / IMMUTABILITY
- `data/cvs/ramin.json`, `data/cvs/mahsa.json` are byte-identical locked inputs.
- **Absolutely no edits, no formatting changes, no sorting, no whitespace modifications** to these files.

### SELF-OVERSEER / DO-NOT-STOP
- You must continuously self-audit and do not stop until:
  (a) The plan's acceptance criteria are fully satisfied,
  (b) You can run the relevant project locally after changes with zero errors,
  (c) You verified behavior with evidence (logs/tests/screens), not assumptions.
- Do not claim "done" unless you can run dev + build/test (as applicable) and confirm expected behavior.

### NO FEATURE CREEP
- Only implement what is required for this plan's scope.
- No unrelated refactors or redesigns.

### DEBUG+RUN REQUIREMENT
- Run the project (dev AND build if relevant) after changes.
- Confirm no runtime errors.
- Confirm specific success conditions.

---

## Deliverables

### Task 0.1: Initialize Django Project

**Acceptance Criteria**:
- [ ] Create Django project with appropriate name (e.g., `cv_backend`)
- [ ] Use Django 5.0+ with Python 3.11+
- [ ] Set up virtual environment with `requirements.txt`
- [ ] Configure project structure:
  ```
  cv_backend/
  ├── manage.py
  ├── requirements.txt
  ├── requirements-dev.txt
  ├── cv_backend/
  │   ├── __init__.py
  │   ├── settings/
  │   │   ├── __init__.py
  │   │   ├── base.py
  │   │   ├── development.py
  │   │   ├── production.py
  │   │   └── testing.py
  │   ├── urls.py
  │   ├── wsgi.py
  │   └── asgi.py
  ├── apps/
  │   └── __init__.py
  └── static/
  ```

**Verification Checks**:
- [ ] `python manage.py check` runs without errors
- [ ] `python manage.py runserver` starts successfully
- [ ] Project uses split settings pattern

### Task 0.2: Environment Configuration

**Acceptance Criteria**:
- [ ] Create `.env.example` with all required variables
- [ ] Environment variables:
  - `DJANGO_SETTINGS_MODULE`
  - `SECRET_KEY`
  - `DEBUG`
  - `ALLOWED_HOSTS`
  - `DATABASE_URL` (optional, SQLite default)
  - `CORS_ALLOWED_ORIGINS`
  - `STATIC_URL`, `MEDIA_URL`
- [ ] Install and configure `python-dotenv` or `django-environ`
- [ ] Create `.env` file in `.gitignore`
- [ ] Validate required env vars on startup

**Verification Checks**:
- [ ] App starts with valid `.env` file
- [ ] App fails gracefully with missing required env vars
- [ ] Settings differ between development/production

### Task 0.3: Dependencies Setup

**Acceptance Criteria**:
- [ ] Create `requirements.txt` with production dependencies:
  - `Django>=5.0`
  - `django-cors-headers`
  - `djangorestframework`
  - `gunicorn`
  - `python-dotenv` or `django-environ`
- [ ] Create `requirements-dev.txt` with development dependencies:
  - `pytest`
  - `pytest-django`
  - `black`
  - `flake8`
  - `mypy`
  - `django-stubs`

**Verification Checks**:
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `pip install -r requirements-dev.txt` succeeds
- [ ] All imports resolve without errors

### Task 0.4: Docker Setup (Optional but Recommended)

**Acceptance Criteria**:
- [ ] Create `Dockerfile` for backend
- [ ] Create `docker-compose.yml` for local development
- [ ] Configure services:
  - Django app
  - (Optional) PostgreSQL
  - (Optional) Redis for caching
- [ ] Health check endpoints configured

**Verification Checks**:
- [ ] `docker-compose up` starts all services
- [ ] App accessible at configured port
- [ ] Hot reload works in development mode

### Task 0.5: Local Development Workflow

**Acceptance Criteria**:
- [ ] Document setup steps in `cv_backend/README.md`
- [ ] Create `Makefile` or scripts for common tasks:
  - `make install` - set up environment
  - `make run` - start development server
  - `make test` - run tests
  - `make lint` - run linting
  - `make migrate` - run migrations
- [ ] Configure pre-commit hooks (optional)

**Verification Checks**:
- [ ] Fresh clone + documented steps = working dev environment
- [ ] All make commands work as expected
- [ ] README is accurate and complete

---

## Self-Overseer Checklist

Before marking complete:
- [ ] Django project starts without errors
- [ ] Settings properly split for dev/prod
- [ ] Environment variables properly configured
- [ ] All dependencies installed and working
- [ ] Docker setup working (if implemented)
- [ ] Documentation accurate and complete
- [ ] No hardcoded secrets in codebase
- [ ] `.gitignore` properly configured

---

## Success Criteria

- [ ] `python manage.py runserver` works
- [ ] `python manage.py check` returns no errors
- [ ] Settings differ based on environment
- [ ] Project structure follows Django best practices
- [ ] Documentation allows new developer to set up in &lt; 15 minutes

---

## Dependencies
- None (this is the first backend plan)

## Estimated Effort
- 1-2 days

---

## Integration Notes

This backend will integrate with:
- The existing Python CV generator (`generate_cv.py`)
- The planned React/TypeScript frontend
- The locked JSON CV data files

The backend should be able to:
1. Serve CV data via REST API
2. Trigger PDF generation using existing `generate_cv.py`
3. Support multiple languages (EN/DE/FA)
