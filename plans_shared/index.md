# Shared Plans Index

This directory contains plans that apply to both backend and frontend, including documentation, infrastructure, and DevOps concerns.

---

## Overview

The shared plans cover cross-cutting concerns:
- Quality Assurance and Documentation
- Production Infrastructure (environment, security, CI/CD)
- Testing infrastructure
- Monitoring and compliance

---

## Plan Summary

| Plan | Title | Original Plan | Dependencies | Est. Effort |
|------|-------|---------------|--------------|-------------|
| [plan1_qa_documentation.md](./plan1_qa_documentation.md) | Quality Assurance & Documentation | Plan 6 | Frontend Plans 1-5 | 2-3 days |
| [plan2_infrastructure_a.md](./plan2_infrastructure_a.md) | Production Infrastructure Part A | Plan 13 | All prior plans | 12-15 days |
| [plan3_infrastructure_b.md](./plan3_infrastructure_b.md) | Production Infrastructure Part B | Plan 14 | All prior plans | 12-15 days |

**Total Estimated Effort: 26-33 days**

---

## Plan Details

### Plan 1: Quality Assurance & Documentation

**Scope:**
- Create comprehensive README
- JSON Schema documentation
- End-to-End Testing Checklist (QA_CHECKLIST.md)
- Code review and refactoring
- Deployment preparation

**Applies To:** Frontend primarily, but documentation applies to whole project

### Plan 2: Production Infrastructure - Part A

**Scope:**
- Error pages (404, 500, offline)
- Loading states and lazy loading strategy
- Environment configuration and build profiles
- Security headers and Content Security Policy
- Logging and debugging infrastructure
- Cache management and service worker strategy
- URL management and deep linking
- Data validation and schema enforcement

**Applies To:** Both frontend and backend

### Plan 3: Production Infrastructure - Part B

**Scope:**
- Browser compatibility and polyfills
- Automated testing infrastructure
- CI/CD pipeline configuration
- Monitoring dashboard and alerting
- Legal pages and compliance (Privacy Policy, ToS)
- Performance budgets and monitoring
- Graceful degradation and fallback strategies

**Applies To:** Both frontend and backend

---

## Execution Order

```
Frontend Plans 1-5 (MVP)
        │
        └──> Shared Plan 1 (QA & Documentation)
                    │
                    └──> Shared Plan 2 (Infrastructure A)
                                │
                                └──> Shared Plan 3 (Infrastructure B)
```

**Note:** Infrastructure plans can be executed in parallel with Premium UI (Phase 6) and Advanced Features (Phase 7) frontend plans.

---

## Key Deliverables

### Documentation
- README.md (comprehensive)
- SCHEMA.md (JSON schema documentation)
- QA_CHECKLIST.md (testing checklist)
- docs/deployment.md
- docs/integration_contract.md

### Infrastructure
- CI/CD pipeline (GitHub Actions)
- Docker configuration
- Environment configuration
- Security headers
- Monitoring setup

### Compliance
- Privacy Policy
- Terms of Service
- Cookie Policy
- Accessibility Statement

---

## Critical Rules

### LOCKED FILES / IMMUTABILITY
- `data/cvs/ramin.json`, `data/cvs/mahsa.json` are byte-identical locked inputs.
- **Absolutely no edits** to these files.

### SELF-OVERSEER REQUIREMENT
- Continuously self-audit until all acceptance criteria are satisfied.
- Verify everything with evidence.
- Do not declare "done" until both frontend and backend work without errors.

### DEBUG+RUN REQUIREMENT
- Run both frontend and backend after changes.
- Confirm no runtime errors.
- Confirm full integration works.

---

## Cross-Project Testing

Before marking shared plans complete:

- [ ] Frontend runs without errors
- [ ] Backend runs without errors
- [ ] Frontend successfully calls backend API
- [ ] PDF generation works end-to-end
- [ ] All languages (EN/DE/FA) work
- [ ] CI pipeline passes
- [ ] Production deployment successful

---

## Dependency Graph

```
┌─────────────────┐    ┌─────────────────┐
│  Frontend       │    │  Backend        │
│  Plans 1-11     │    │  Plans 0-7      │
└────────┬────────┘    └────────┬────────┘
         │                      │
         └──────────┬───────────┘
                    │
         ┌──────────▼──────────┐
         │  Shared Plans 1-3   │
         │  (QA, Infrastructure)│
         └─────────────────────┘
```
