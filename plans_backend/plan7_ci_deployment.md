# Plan 7: CI Integration & Deployment Readiness

## Goal
Set up continuous integration pipeline and prepare the Django backend for production deployment with proper configuration, documentation, and deployment scripts.

## Scope
This plan covers:
- CI/CD pipeline configuration
- Production settings
- Deployment documentation
- Server configuration (Gunicorn/Uvicorn)
- Environment configuration

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

---

## Deliverables

### Task 7.1: GitHub Actions CI Pipeline

**Acceptance Criteria**:
- [ ] Create `.github/workflows/backend-ci.yml`:
  ```yaml
  name: Backend CI
  
  on:
    push:
      branches: [main, develop]
      paths:
        - 'cv_backend/**'
        - '.github/workflows/backend-ci.yml'
    pull_request:
      branches: [main]
      paths:
        - 'cv_backend/**'
  
  jobs:
    lint:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: '3.11'
        - name: Install dependencies
          run: |
            pip install -r cv_backend/requirements-dev.txt
        - name: Run flake8
          run: flake8 cv_backend/apps
        - name: Run black check
          run: black --check cv_backend/apps
        - name: Run mypy
          run: mypy cv_backend/apps
    
    test:
      runs-on: ubuntu-latest
      needs: lint
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: '3.11'
        - name: Install dependencies
          run: |
            pip install -r cv_backend/requirements.txt
            pip install -r cv_backend/requirements-dev.txt
        - name: Run tests
          run: |
            cd cv_backend
            pytest --cov=apps --cov-report=xml
        - name: Upload coverage
          uses: codecov/codecov-action@v3
          with:
            file: cv_backend/coverage.xml
    
    security:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: '3.11'
        - name: Install dependencies
          run: pip install safety
        - name: Security check
          run: safety check -r cv_backend/requirements.txt
  ```
- [ ] Configure branch protection rules
- [ ] Add status badges to README

**Verification Checks**:
- [ ] CI runs on push/PR
- [ ] Linting step passes
- [ ] Tests pass
- [ ] Security scan completes

### Task 7.2: Production Settings

**Acceptance Criteria**:
- [ ] Create production settings in `settings/production.py`:
  ```python
  from .base import *
  import os
  
  DEBUG = False
  
  ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
  
  # Security settings
  SECURE_SSL_REDIRECT = True
  SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  SECURE_HSTS_SECONDS = 31536000
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  
  # Static files
  STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
  
  # Logging
  LOGGING = {
      'version': 1,
      'disable_existing_loggers': False,
      'formatters': {
          'verbose': {
              'format': '{levelname} {asctime} {module} {message}',
              'style': '{',
          },
      },
      'handlers': {
          'console': {
              'class': 'logging.StreamHandler',
              'formatter': 'verbose',
          },
      },
      'root': {
          'handlers': ['console'],
          'level': 'INFO',
      },
      'loggers': {
          'django': {
              'handlers': ['console'],
              'level': 'INFO',
              'propagate': False,
          },
      },
  }
  ```
- [ ] Verify with `python manage.py check --deploy`

**Verification Checks**:
- [ ] Production settings load without errors
- [ ] Security checks pass
- [ ] No sensitive data in settings

### Task 7.3: Gunicorn Configuration

**Acceptance Criteria**:
- [ ] Create `gunicorn.conf.py`:
  ```python
  import multiprocessing
  
  # Bind to 0.0.0.0:8000
  bind = "0.0.0.0:8000"
  
  # Number of workers
  workers = multiprocessing.cpu_count() * 2 + 1
  
  # Worker class (sync for traditional, uvicorn.workers.UvicornWorker for async)
  worker_class = "sync"
  
  # Max requests per worker before restart
  max_requests = 1000
  max_requests_jitter = 50
  
  # Timeout
  timeout = 30
  graceful_timeout = 30
  
  # Logging
  accesslog = "-"
  errorlog = "-"
  loglevel = "info"
  
  # Process naming
  proc_name = "cv_backend"
  ```
- [ ] Add to requirements: `gunicorn`
- [ ] Document startup command:
  ```bash
  gunicorn cv_backend.wsgi:application -c gunicorn.conf.py
  ```

**Verification Checks**:
- [ ] Gunicorn starts successfully
- [ ] Correct number of workers
- [ ] Logging works

### Task 7.4: Docker Production Configuration

**Acceptance Criteria**:
- [ ] Update Dockerfile for production:
  ```dockerfile
  FROM python:3.11-slim
  
  WORKDIR /app
  
  # Install dependencies
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  
  # Copy application
  COPY . .
  
  # Collect static files
  RUN python manage.py collectstatic --noinput
  
  # Non-root user
  RUN useradd -m appuser
  USER appuser
  
  # Expose port
  EXPOSE 8000
  
  # Start gunicorn
  CMD ["gunicorn", "cv_backend.wsgi:application", "-c", "gunicorn.conf.py"]
  ```
- [ ] Create `docker-compose.prod.yml`:
  ```yaml
  version: '3.8'
  
  services:
    backend:
      build: ./cv_backend
      ports:
        - "8000:8000"
      environment:
        - DJANGO_SETTINGS_MODULE=cv_backend.settings.production
        - SECRET_KEY=${SECRET_KEY}
        - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      volumes:
        - static_volume:/app/staticfiles
        - media_volume:/app/media
  
  volumes:
    static_volume:
    media_volume:
  ```

**Verification Checks**:
- [ ] Docker build succeeds
- [ ] Container starts and serves requests
- [ ] Static files collected

### Task 7.5: Environment Documentation

**Acceptance Criteria**:
- [ ] Update `.env.example`:
  ```bash
  # Django Settings
  DJANGO_SETTINGS_MODULE=cv_backend.settings.production
  SECRET_KEY=your-secret-key-here
  DEBUG=False
  ALLOWED_HOSTS=example.com,www.example.com
  
  # CORS
  CORS_ALLOWED_ORIGINS=https://frontend.example.com
  
  # Database (optional, SQLite default)
  DATABASE_URL=
  
  # Cache (optional, memory default)
  REDIS_URL=
  
  # Monitoring (optional)
  SENTRY_DSN=
  ```
- [ ] Document all environment variables
- [ ] Include validation requirements

**Verification Checks**:
- [ ] All variables documented
- [ ] Example values provided
- [ ] Clear descriptions

### Task 7.6: Deployment Documentation

**Acceptance Criteria**:
- [ ] Create `docs/deployment.md`:
  ```markdown
  # Deployment Guide
  
  ## Prerequisites
  - Python 3.11+
  - pip
  - (Optional) Docker
  
  ## Quick Deploy
  
  ### Using Docker
  ```bash
  docker-compose -f docker-compose.prod.yml up -d
  ```
  
  ### Manual Deployment
  1. Clone repository
  2. Create virtual environment
  3. Install dependencies
  4. Set environment variables
  5. Run migrations
  6. Collect static files
  7. Start Gunicorn
  
  ## Platform-Specific Guides
  
  ### Railway.app
  ...
  
  ### Heroku
  ...
  
  ### DigitalOcean
  ...
  ```
- [ ] Include troubleshooting section
- [ ] Document rollback procedure

**Verification Checks**:
- [ ] Documentation complete
- [ ] Steps are accurate
- [ ] Commands work

### Task 7.7: Health Monitoring Setup

**Acceptance Criteria**:
- [ ] Enhance health check endpoint:
  ```python
  class HealthCheckView(APIView):
      def get(self, request):
          health = {
              'status': 'healthy',
              'version': settings.VERSION,
              'timestamp': timezone.now().isoformat(),
              'checks': {
                  'database': self._check_database(),
                  'cache': self._check_cache(),
                  'cv_data': self._check_cv_data(),
              }
          }
          
          overall_healthy = all(
              c['status'] == 'ok' 
              for c in health['checks'].values()
          )
          
          status_code = 200 if overall_healthy else 503
          return Response(health, status=status_code)
  ```
- [ ] Add liveness and readiness probes for Kubernetes
- [ ] Document monitoring endpoints

**Verification Checks**:
- [ ] Health check returns component status
- [ ] 503 returned when unhealthy
- [ ] Easy to integrate with monitoring

### Task 7.8: Startup Scripts

**Acceptance Criteria**:
- [ ] Create `scripts/start.sh`:
  ```bash
  #!/bin/bash
  set -e
  
  # Wait for database (if using)
  # python manage.py wait_for_db
  
  # Run migrations
  python manage.py migrate --noinput
  
  # Collect static files
  python manage.py collectstatic --noinput
  
  # Start server
  exec gunicorn cv_backend.wsgi:application -c gunicorn.conf.py
  ```
- [ ] Create `scripts/healthcheck.sh`:
  ```bash
  #!/bin/bash
  curl -f http://localhost:8000/api/v1/health/ || exit 1
  ```
- [ ] Make scripts executable

**Verification Checks**:
- [ ] Start script runs successfully
- [ ] Health check script works
- [ ] Scripts are idempotent

---

## Self-Overseer Checklist

Before marking complete:
- [ ] CI pipeline working
- [ ] Production settings configured
- [ ] Gunicorn ready
- [ ] Docker production ready
- [ ] Environment documented
- [ ] Deployment documented
- [ ] Health monitoring configured
- [ ] Startup scripts working

---

## Success Criteria

- [ ] CI passes on all branches
- [ ] `python manage.py check --deploy` passes
- [ ] Docker container starts and serves requests
- [ ] Deployment documentation accurate
- [ ] Health endpoint returns component status

---

## Dependencies
- **Requires**: Plans 0-6 (complete backend implementation and testing)

## Estimated Effort
- 2-3 days

---

## CI/CD Pipeline Summary

| Stage | Purpose | Tools |
|-------|---------|-------|
| Lint | Code quality | flake8, black, mypy |
| Test | Functionality | pytest, coverage |
| Security | Vulnerability scan | safety |
| Build | Docker image | docker build |
| Deploy | Production release | docker-compose |

---

## Production Checklist

Before going live:
- [ ] SECRET_KEY is unique and secret
- [ ] DEBUG = False
- [ ] ALLOWED_HOSTS configured
- [ ] HTTPS enabled
- [ ] Static files collected and served
- [ ] Logging configured
- [ ] Health checks working
- [ ] Monitoring configured
- [ ] Backup strategy in place
