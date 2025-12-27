# Master Roadmap Index

This document provides the complete execution plan across all backend, frontend, and shared plans with dependencies, execution order, and integration points.

---

## Overview

The CV Generator project consists of:

1. **Python CV Generator** (existing): `generate_cv.py` - Generates PDF CVs from JSON using Jinja2 + LaTeX
2. **Django Backend** (new): REST API to serve CV data and trigger PDF generation
3. **React Frontend** (new): Interactive web portfolio/CV website

---

## Complete Plan Inventory

### Backend Plans (8 plans)

| ID | Plan | Title | Dependencies |
|----|------|-------|--------------|
| B0 | [plans_backend/plan0_backend_setup.md](./plans_backend/plan0_backend_setup.md) | Environment Setup & Project Structure | None |
| B1 | [plans_backend/plan1_data_model.md](./plans_backend/plan1_data_model.md) | Data Model Strategy & JSON Handling | B0 |
| B2 | [plans_backend/plan2_api_design.md](./plans_backend/plan2_api_design.md) | API Design & Endpoints | B0, B1 |
| B3 | [plans_backend/plan3_admin_tooling.md](./plans_backend/plan3_admin_tooling.md) | Admin Tooling & Content Management | B0, B1 |
| B4 | [plans_backend/plan4_security.md](./plans_backend/plan4_security.md) | Security Configuration | B0, B2 |
| B5 | [plans_backend/plan5_static_media.md](./plans_backend/plan5_static_media.md) | Static & Media File Handling | B0, B2 |
| B6 | [plans_backend/plan6_testing.md](./plans_backend/plan6_testing.md) | Backend Testing | B0-B5 |
| B7 | [plans_backend/plan7_ci_deployment.md](./plans_backend/plan7_ci_deployment.md) | CI Integration & Deployment | B0-B6 |

### Frontend Plans (12 plans)

| ID | Plan | Title | Dependencies |
|----|------|-------|--------------|
| F0 | [plans_frontend/plan0_frontend_readiness.md](./plans_frontend/plan0_frontend_readiness.md) | Frontend Readiness & Tooling | None |
| F1 | [plans_frontend/plan1_project_setup.md](./plans_frontend/plan1_project_setup.md) | Project Setup & Foundation | F0 |
| F2 | [plans_frontend/plan2_layout_theme.md](./plans_frontend/plan2_layout_theme.md) | Core Layout & Theme System | F1 |
| F3 | [plans_frontend/plan3_section_rendering.md](./plans_frontend/plan3_section_rendering.md) | Section Rendering & JSON Mapping | F1, F2 |
| F4 | [plans_frontend/plan4_advanced_features.md](./plans_frontend/plan4_advanced_features.md) | Advanced Features | F1-F3 |
| F5 | [plans_frontend/plan5_robustness_polish.md](./plans_frontend/plan5_robustness_polish.md) | Robustness & Polish | F1-F4 |
| F6 | [plans_frontend/plan6_enhanced_ui_a.md](./plans_frontend/plan6_enhanced_ui_a.md) | Enhanced UI - Part A | F1-F5 |
| F7 | [plans_frontend/plan7_enhanced_ui_b.md](./plans_frontend/plan7_enhanced_ui_b.md) | Enhanced UI - Part B | F1-F6 |
| F8 | [plans_frontend/plan8_enhanced_ui_c.md](./plans_frontend/plan8_enhanced_ui_c.md) | Enhanced UI - Part C | F1-F7 |
| F9 | [plans_frontend/plan9_seo_analytics.md](./plans_frontend/plan9_seo_analytics.md) | SEO, Analytics, Skills Viz | F1-F8 |
| F10 | [plans_frontend/plan10_download_blog_pwa.md](./plans_frontend/plan10_download_blog_pwa.md) | Download, Blog, PWA | F1-F9 |
| F11 | [plans_frontend/plan11_comments_i18n.md](./plans_frontend/plan11_comments_i18n.md) | Comments, i18n, Monitoring | F1-F10 |

### Shared Plans (3 plans)

| ID | Plan | Title | Dependencies |
|----|------|-------|--------------|
| S1 | [plans_shared/plan1_qa_documentation.md](./plans_shared/plan1_qa_documentation.md) | QA & Documentation | F1-F5 |
| S2 | [plans_shared/plan2_infrastructure_a.md](./plans_shared/plan2_infrastructure_a.md) | Infrastructure Part A | B7, F5 |
| S3 | [plans_shared/plan3_infrastructure_b.md](./plans_shared/plan3_infrastructure_b.md) | Infrastructure Part B | S2 |

### Archived Plans

| Plan | Description |
|------|-------------|
| [plans_archive/original_master_plan.md](./plans_archive/original_master_plan.md) | Original comprehensive plan (for reference) |
| [plans_archive/original_plans_index.md](./plans_archive/original_plans_index.md) | Original plans index (for reference) |

---

## Recommended Execution Order

### Phase 1: Foundation (Week 1-2)
**Goal:** Set up both projects and establish communication

| Order | Plan | Track | Duration |
|-------|------|-------|----------|
| 1 | B0 | Backend | 1-2 days |
| 2 | F0 | Frontend | 1 day |
| 3 | F1 | Frontend | 1-2 days |
| 4 | B1 | Backend | 2-3 days |
| 5 | F2 | Frontend | 2-3 days |

### Phase 2: Core Functionality (Week 3-5)
**Goal:** Implement main features for both systems

| Order | Plan | Track | Duration |
|-------|------|-------|----------|
| 6 | B2 | Backend | 2-3 days |
| 7 | F3 | Frontend | 5-7 days |
| 8 | B3, B4, B5 | Backend (parallel) | 3-5 days |
| 9 | F4 | Frontend | 3-4 days |

### Phase 3: Integration & Polish (Week 6-7)
**Goal:** Connect frontend to backend, polish both

| Order | Plan | Track | Duration |
|-------|------|-------|----------|
| 10 | F5 | Frontend | 2-3 days |
| 11 | B6 | Backend | 2-3 days |
| 12 | S1 | Shared | 2-3 days |
| 13 | B7 | Backend | 2-3 days |

### Phase 4: Premium Features (Week 8-12)
**Goal:** Enhanced UI and advanced features

| Order | Plan | Track | Duration |
|-------|------|-------|----------|
| 14 | F6 | Frontend | 8-10 days |
| 15 | F7 | Frontend | 6-8 days |
| 16 | F8 | Frontend | 8-10 days |

### Phase 5: Enterprise Features (Week 13-18)
**Goal:** SEO, PWA, advanced features, infrastructure

| Order | Plan | Track | Duration |
|-------|------|-------|----------|
| 17 | F9 | Frontend | 10-12 days |
| 18 | F10 | Frontend | 12-15 days |
| 19 | F11 | Frontend | 12-15 days |
| 20 | S2 | Shared | 12-15 days |
| 21 | S3 | Shared | 12-15 days |

---

## Parallel Execution Opportunities

These plans can be executed in parallel if multiple developers are available:

### Track 1: Backend
```
B0 → B1 → B2 → B3/B4/B5 → B6 → B7
```

### Track 2: Frontend
```
F0 → F1 → F2 → F3 → F4 → F5 → F6 → F7 → F8 → F9 → F10 → F11
```

### Track 3: Shared (after MVP)
```
S1 → S2 → S3
```

**Integration Points:**
- After B2 + F3: Frontend can start calling backend API
- After B7 + F5: Full integration testing
- After S3: Production deployment

---

## Total Effort Estimates

| Track | Plans | Effort (days) |
|-------|-------|---------------|
| Backend | 8 plans | 13-21 days |
| Frontend | 12 plans | 71-90 days |
| Shared | 3 plans | 26-33 days |
| **Total** | 23 plans | **110-144 days** |

**With Parallel Execution:**
- 2 developers: ~70-90 days
- 3 developers: ~50-70 days

---

## Integration Contract

See [docs/integration_contract.md](./docs/integration_contract.md) for the complete API contract between frontend and backend.

**Quick Reference:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/cvs/` | GET | List available CVs |
| `/api/v1/cvs/{person}/` | GET | Get full CV data |
| `/api/v1/cvs/{person}/?lang=de` | GET | Get CV in German |
| `/api/v1/cvs/{person}/?focus=Programming` | GET | Filter by type_key |
| `/api/v1/cvs/{person}/pdf/` | GET | Download PDF |
| `/api/v1/health/` | GET | Health check |

---

## Critical Rules (All Plans)

### LOCKED FILES
```
data/cvs/ramin.json  ← DO NOT MODIFY
data/cvs/mahsa.json  ← DO NOT MODIFY
```

### SELF-OVERSEER
- Do not stop until acceptance criteria met
- Verify with evidence (logs, tests, screenshots)
- Run dev AND build, confirm no errors

### NO FEATURE CREEP
- Only implement what the plan specifies
- No unrelated refactors

---

## Deployment Milestones

| Milestone | When | What |
|-----------|------|------|
| **M1: Backend API** | Week 3 | Backend serving CV data |
| **M2: Frontend MVP** | Week 5 | Basic frontend with all sections |
| **M3: Full Integration** | Week 7 | Frontend + Backend working together |
| **M4: Premium UI** | Week 12 | Enhanced animations and effects |
| **M5: Production** | Week 18 | Full production deployment |

---

## Getting Started

1. **Read this document** to understand the overall structure
2. **Pick a track** (Backend or Frontend)
3. **Start with Plan 0 (Backend) or Plan 1 (Frontend)**
4. **Follow the dependency chain**
5. **Use the integration contract** for API communication
6. **Refer to archived plans** for additional context if needed

---

## File Structure Summary

```
cv_generator/
├── plans_backend/           # Django backend plans (8 plans)
│   ├── index.md
│   ├── plan0_backend_setup.md
│   ├── plan1_data_model.md
│   ├── plan2_api_design.md
│   ├── plan3_admin_tooling.md
│   ├── plan4_security.md
│   ├── plan5_static_media.md
│   ├── plan6_testing.md
│   └── plan7_ci_deployment.md
│
├── plans_frontend/          # React frontend plans (11 plans)
│   ├── index.md
│   ├── plan1_project_setup.md
│   ├── plan2_layout_theme.md
│   ├── ... (through plan11)
│
├── plans_shared/            # Cross-cutting plans (3 plans)
│   ├── index.md
│   ├── plan1_qa_documentation.md
│   ├── plan2_infrastructure_a.md
│   └── plan3_infrastructure_b.md
│
├── plans_archive/           # Archived original plans
│   ├── original_master_plan.md
│   └── original_plans_index.md
│
├── docs/
│   └── integration_contract.md
│
└── plans_master_index.md    # This file
```
