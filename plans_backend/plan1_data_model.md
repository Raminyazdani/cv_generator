# Plan 1: Data Model Strategy & JSON Handling

## Goal
Design and implement the data model strategy for the CV Generator backend, determining how CV data is stored, accessed, and served. Establish the contract between JSON files and the API layer.

## Scope
This plan covers:
- Data storage strategy (JSON files vs DB vs hybrid)
- CV data models and serializers
- Multi-language data handling
- Canonical schema definition
- Data loading and caching mechanisms

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

### Task 1.1: Data Storage Strategy Decision

**Acceptance Criteria**:
- [ ] Document data storage decision in `docs/data_strategy.md`
- [ ] Recommended approach: **JSON files served by backend** (simplest, aligns with current setup)
- [ ] Alternative considered: Database storage for dynamic content
- [ ] Decision factors documented:
  - Read-only vs read-write needs
  - Multi-language requirements
  - Caching strategy
  - Integration with existing `generate_cv.py`

**Strategy Details**:
```
Primary Storage: JSON files in data/cvs/
- Files: ramin.json, mahsa.json (locked, read-only)
- Per-language files: ramin_en.json, ramin_de.json, ramin_fa.json (if separate)
- OR: Single file per person with language as JSON structure

Backend Role:
- Load JSON files at startup or per-request
- Normalize data to canonical schema
- Cache normalized data
- Serve via REST API
```

**Verification Checks**:
- [ ] Strategy document reviewed and approved
- [ ] Aligns with frontend requirements
- [ ] Supports multi-language without code changes

### Task 1.2: Canonical Schema Definition

**Acceptance Criteria**:
- [ ] Create `apps/cv/schemas.py` with Pydantic models (or equivalent)
- [ ] Define canonical schema covering all CV sections:
  - `Basics` - Personal info
  - `Profile` - Social links
  - `Education` - Education entries
  - `Experience` - Work experience
  - `Skill` - Skills with categories
  - `Project` - Projects
  - `Publication` - Publications
  - `Reference` - References
  - `Language` - Language proficiency
  - `Certification` - Certifications
- [ ] Include `type_key` for filtering support
- [ ] All fields have clear types and optionality

**Schema Example**:
```python
from pydantic import BaseModel
from typing import Optional, List

class Basics(BaseModel):
    fname: str
    lname: str
    label: List[str] = []
    email: Optional[str] = None
    phone: Optional[dict] = None
    location: Optional[List[dict]] = None
    summary: Optional[str] = None
    pictures: Optional[List[dict]] = None

class Education(BaseModel):
    institution: str
    studyType: Optional[str] = None
    area: Optional[str] = None
    location: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    gpa: Optional[str] = None
    type_key: List[str] = []
```

**Verification Checks**:
- [ ] Schema validates existing JSON data without errors
- [ ] All sections from JSON have corresponding schema
- [ ] Types are accurate and allow flexibility

### Task 1.3: CV Data App Setup

**Acceptance Criteria**:
- [ ] Create Django app: `apps/cv/`
- [ ] App structure:
  ```
  apps/cv/
  ├── __init__.py
  ├── apps.py
  ├── models.py (minimal, may be empty)
  ├── serializers.py
  ├── views.py
  ├── urls.py
  ├── services.py (business logic)
  └── tests/
      ├── __init__.py
      └── test_services.py
  ```
- [ ] Register app in settings

**Verification Checks**:
- [ ] App imports successfully
- [ ] No circular import issues
- [ ] Tests run successfully

### Task 1.4: JSON Data Loading Service

**Acceptance Criteria**:
- [ ] Create `apps/cv/services.py` with data loading logic
- [ ] Implement `CVDataService` class:
  ```python
  class CVDataService:
      def get_cv_data(self, person: str, language: str = 'en') -> dict:
          """Load CV data for a person, optionally by language."""
          pass
      
      def list_available_cvs(self) -> List[str]:
          """List all available CV files."""
          pass
      
      def get_section(self, person: str, section: str, language: str = 'en') -> dict:
          """Get a specific section of CV data."""
          pass
  ```
- [ ] Handle file not found gracefully
- [ ] Validate data against schema on load (optional, can log warnings)
- [ ] Support language-specific file loading

**Verification Checks**:
- [ ] `get_cv_data('ramin')` returns valid data
- [ ] Invalid person name returns appropriate error
- [ ] Language parameter affects data loading

### Task 1.5: Data Caching Strategy

**Acceptance Criteria**:
- [ ] Implement caching for loaded CV data
- [ ] Options:
  - In-memory cache (simple dict, development)
  - Django cache framework (supports Redis in production)
- [ ] Cache invalidation strategy:
  - File modification time check
  - Manual cache clear endpoint (admin only)
  - TTL-based expiration
- [ ] Cache configuration in settings

**Verification Checks**:
- [ ] Second call to `get_cv_data` uses cache
- [ ] Cache invalidation works correctly
- [ ] Memory usage acceptable

### Task 1.6: Multi-Language Data Handling

**Acceptance Criteria**:
- [ ] Support three languages: EN, DE, FA
- [ ] Strategy options:
  - **Option A**: Separate JSON files per language (ramin_en.json, ramin_de.json, ramin_fa.json)
  - **Option B**: Single file with language keys at section level
  - **Option C**: Single file with default language, translation files for others
- [ ] Document chosen approach
- [ ] Implement language fallback (FA → DE → EN if not found)

**Verification Checks**:
- [ ] API returns correct language content
- [ ] Fallback works when translation missing
- [ ] All three languages accessible

---

## Self-Overseer Checklist

Before marking complete:
- [ ] Data strategy documented and justified
- [ ] Canonical schema covers all CV sections
- [ ] Data loading service works for all existing CVs
- [ ] Caching implemented and verified
- [ ] Multi-language handling works
- [ ] Unit tests pass
- [ ] No modifications to locked JSON files

---

## Success Criteria

- [ ] `CVDataService.get_cv_data('ramin')` returns valid, typed data
- [ ] Schema validates all existing JSON files
- [ ] Caching reduces load times
- [ ] Multi-language support functional
- [ ] Service is unit tested

---

## Dependencies
- **Requires**: Plan 0 (Backend Environment Setup)

## Estimated Effort
- 2-3 days

---

## Integration Notes

The data service will be used by:
- API views to serve CV data
- PDF generation service (wrapping existing `generate_cv.py`)
- Admin interface (if implemented)

The canonical schema becomes the contract between:
- Backend JSON storage
- REST API responses
- Frontend TypeScript interfaces
