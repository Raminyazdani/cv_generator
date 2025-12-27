# Backend Plans Index

This directory contains the comprehensive plan set for implementing a Django backend for the CV Generator project.

---

## Overview

The backend plans cover building a production-grade Django backend that:
- Serves CV data via REST API
- Integrates with the existing Python CV generator
- Supports multiple languages (EN/DE/FA)
- Provides admin tooling for content management
- Includes proper security, testing, and deployment configuration

---

## Plan Summary

| Plan | Title | Dependencies | Est. Effort |
|------|-------|--------------|-------------|
| [plan0_backend_setup.md](./plan0_backend_setup.md) | Environment Setup & Project Structure | None | 1-2 days |
| [plan1_data_model.md](./plan1_data_model.md) | Data Model Strategy & JSON Handling | Plan 0 | 2-3 days |
| [plan2_api_design.md](./plan2_api_design.md) | API Design & Endpoints | Plans 0, 1 | 2-3 days |
| [plan3_admin_tooling.md](./plan3_admin_tooling.md) | Admin Tooling & Content Management | Plans 0, 1 | 2-3 days |
| [plan4_security.md](./plan4_security.md) | Security Configuration | Plans 0, 2 | 1-2 days |
| [plan5_static_media.md](./plan5_static_media.md) | Static & Media File Handling | Plans 0, 2 | 1-2 days |
| [plan6_testing.md](./plan6_testing.md) | Backend Testing | Plans 0-5 | 2-3 days |
| [plan7_ci_deployment.md](./plan7_ci_deployment.md) | CI Integration & Deployment Readiness | Plans 0-6 | 2-3 days |

**Total Estimated Effort: 13-21 days**

---

## Execution Order

```
Plan 0 (Setup)
    │
    ├──> Plan 1 (Data Model)
    │        │
    │        ├──> Plan 2 (API Design)
    │        │        │
    │        │        ├──> Plan 4 (Security)
    │        │        │
    │        │        └──> Plan 5 (Static/Media)
    │        │
    │        └──> Plan 3 (Admin)
    │
    └──────────────> Plan 6 (Testing)
                         │
                         └──> Plan 7 (CI/Deployment)
```

**Recommended Execution:**
1. Plan 0 → Plan 1 → Plan 2 (core functionality)
2. Plan 3, Plan 4, Plan 5 (can be parallelized)
3. Plan 6 → Plan 7 (finalization)

---

## API Endpoints Summary

After implementing all backend plans, the following endpoints will be available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health/` | GET | Health check |
| `/api/v1/cvs/` | GET | List available CVs |
| `/api/v1/cvs/{person}/` | GET | Get full CV data |
| `/api/v1/cvs/{person}/{section}/` | GET | Get specific section |
| `/api/v1/cvs/{person}/pdf/` | GET | Download PDF |
| `/api/v1/cvs/{person}/picture/` | GET | Get profile picture |

---

## Integration with Frontend

The backend API is designed to be consumed by the React/TypeScript frontend:

1. **Data Loading**: Frontend fetches CV data from `/api/v1/cvs/{person}/?lang={lang}`
2. **Language Support**: `?lang=en|de|fa` parameter for multi-language
3. **Focus Filtering**: `?focus=Programming` parameter for type_key filtering
4. **PDF Generation**: Backend wraps existing `generate_cv.py` for PDF generation

---

## Critical Rules

Every backend plan includes these rules that MUST be followed:

### LOCKED FILES / IMMUTABILITY
- `data/cvs/ramin.json`, `data/cvs/mahsa.json` are byte-identical locked inputs.
- **Absolutely no edits** to these files.

### SELF-OVERSEER REQUIREMENT
- Continuously self-audit until all acceptance criteria are satisfied.
- Verify everything with evidence (logs/tests/screens).
- Do not declare "done" until the project runs without errors.

### DEBUG+RUN REQUIREMENT
- Run the project after changes.
- Confirm no runtime errors.
- Confirm success conditions by testing relevant endpoints.

---

## Technology Stack

- **Framework**: Django 5.0+
- **API**: Django REST Framework
- **Server**: Gunicorn (production), Django dev server (development)
- **Testing**: pytest, pytest-django
- **Linting**: black, flake8, mypy
- **Deployment**: Docker, GitHub Actions CI

---

## Directory Structure (Target)

```
cv_backend/
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── gunicorn.conf.py
├── Dockerfile
├── cv_backend/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── cv/
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   └── tests/
│   └── core/
│       └── views.py
└── scripts/
    └── start.sh
```
