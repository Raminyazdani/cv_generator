# Plan 2: API Design & Endpoints

## Goal
Design and implement a RESTful API for serving CV data, enabling the frontend to fetch CV content by person and language, and providing health and metadata endpoints.

## Scope
This plan covers:
- REST API design and documentation
- CV data endpoints
- Health check endpoint
- Response schema standardization
- Error handling conventions

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

### Task 2.1: API Design Documentation

**Acceptance Criteria**:
- [ ] Create `docs/api_design.md` with API specification
- [ ] Document all endpoints with:
  - HTTP method
  - URL pattern
  - Request parameters
  - Response schema
  - Error responses
  - Example requests/responses

**API Overview**:
```
Base URL: /api/v1/

Endpoints:
GET /api/v1/health/              - Health check
GET /api/v1/cvs/                 - List available CVs
GET /api/v1/cvs/{person}/        - Get full CV data
GET /api/v1/cvs/{person}/basics/ - Get basics section
GET /api/v1/cvs/{person}/{section}/ - Get specific section

Query Parameters:
- lang: en|de|fa (default: en)
- focus: string (filter by type_key)
```

**Verification Checks**:
- [ ] API design document complete
- [ ] All endpoints documented with examples
- [ ] Aligns with frontend requirements

### Task 2.2: Django REST Framework Setup

**Acceptance Criteria**:
- [ ] Configure DRF in settings:
  ```python
  REST_FRAMEWORK = {
      'DEFAULT_RENDERER_CLASSES': [
          'rest_framework.renderers.JSONRenderer',
      ],
      'DEFAULT_PARSER_CLASSES': [
          'rest_framework.parsers.JSONParser',
      ],
      'EXCEPTION_HANDLER': 'apps.cv.exceptions.custom_exception_handler',
      'DEFAULT_PAGINATION_CLASS': None,
  }
  ```
- [ ] Set up URL routing for API versioning
- [ ] Configure API root URL

**Verification Checks**:
- [ ] DRF browsable API works (development only)
- [ ] JSON responses properly formatted
- [ ] API versioning in URLs

### Task 2.3: CV Serializers

**Acceptance Criteria**:
- [ ] Create serializers in `apps/cv/serializers.py`:
  ```python
  class BasicsSerializer(serializers.Serializer):
      fname = serializers.CharField()
      lname = serializers.CharField()
      label = serializers.ListField(child=serializers.CharField())
      email = serializers.EmailField(allow_null=True, required=False)
      phone = serializers.DictField(allow_null=True, required=False)
      location = serializers.ListField(required=False)
      summary = serializers.CharField(allow_null=True, required=False)
      pictures = serializers.ListField(required=False)

  class EducationSerializer(serializers.Serializer):
      institution = serializers.CharField()
      studyType = serializers.CharField(allow_null=True, required=False)
      area = serializers.CharField(allow_null=True, required=False)
      location = serializers.CharField(allow_null=True, required=False)
      startDate = serializers.CharField(allow_null=True, required=False)
      endDate = serializers.CharField(allow_null=True, required=False)
      gpa = serializers.CharField(allow_null=True, required=False)
      type_key = serializers.ListField(child=serializers.CharField(), required=False)

  # ... similar for all sections

  class CVSerializer(serializers.Serializer):
      basics = BasicsSerializer(many=True)
      profiles = ProfileSerializer(many=True, required=False)
      education = EducationSerializer(many=True, required=False)
      experiences = ExperienceSerializer(many=True, required=False)
      skills = serializers.DictField(required=False)
      projects = ProjectSerializer(many=True, required=False)
      publications = PublicationSerializer(many=True, required=False)
      references = ReferenceSerializer(many=True, required=False)
      languages = LanguageSerializer(many=True, required=False)
      workshop_and_certifications = CertificationSerializer(many=True, required=False)
  ```

**Verification Checks**:
- [ ] Serializers validate existing JSON data
- [ ] Serialization produces clean JSON output
- [ ] All sections have corresponding serializers

### Task 2.4: CV API Views

**Acceptance Criteria**:
- [ ] Create views in `apps/cv/views.py`:
  ```python
  class CVListView(APIView):
      """List all available CVs."""
      def get(self, request):
          cvs = CVDataService().list_available_cvs()
          return Response({'cvs': cvs})

  class CVDetailView(APIView):
      """Get full CV data for a person."""
      def get(self, request, person):
          lang = request.query_params.get('lang', 'en')
          focus = request.query_params.get('focus', None)
          
          service = CVDataService()
          data = service.get_cv_data(person, language=lang)
          
          if focus:
              data = service.filter_by_type_key(data, focus)
          
          serializer = CVSerializer(data)
          return Response(serializer.data)

  class CVSectionView(APIView):
      """Get a specific section of CV data."""
      def get(self, request, person, section):
          lang = request.query_params.get('lang', 'en')
          
          service = CVDataService()
          data = service.get_section(person, section, language=lang)
          
          # Use appropriate serializer based on section
          return Response(data)
  ```
- [ ] Handle 404 for non-existent person/section
- [ ] Validate language parameter

**Verification Checks**:
- [ ] `/api/v1/cvs/` returns list of CVs
- [ ] `/api/v1/cvs/ramin/` returns full CV data
- [ ] `/api/v1/cvs/ramin/?lang=de` returns German content
- [ ] Invalid person returns 404

### Task 2.5: Health Check Endpoint

**Acceptance Criteria**:
- [ ] Create health endpoint in `apps/core/views.py`:
  ```python
  class HealthCheckView(APIView):
      permission_classes = []
      
      def get(self, request):
          return Response({
              'status': 'healthy',
              'version': settings.VERSION,
              'timestamp': timezone.now().isoformat()
          })
  ```
- [ ] No authentication required
- [ ] Returns 200 for healthy status
- [ ] Optionally check dependencies (DB, cache)

**Verification Checks**:
- [ ] `/api/v1/health/` returns 200
- [ ] Response includes status and version
- [ ] Works without authentication

### Task 2.6: URL Configuration

**Acceptance Criteria**:
- [ ] Configure URLs in `apps/cv/urls.py`:
  ```python
  urlpatterns = [
      path('cvs/', CVListView.as_view(), name='cv-list'),
      path('cvs/<str:person>/', CVDetailView.as_view(), name='cv-detail'),
      path('cvs/<str:person>/<str:section>/', CVSectionView.as_view(), name='cv-section'),
  ]
  ```
- [ ] Include in main `urls.py` with version prefix
- [ ] Add health endpoint to core URLs

**Verification Checks**:
- [ ] All URLs resolve correctly
- [ ] URL names work for reverse lookups
- [ ] API versioning in place

### Task 2.7: Error Handling

**Acceptance Criteria**:
- [ ] Create custom exception handler in `apps/cv/exceptions.py`:
  ```python
  def custom_exception_handler(exc, context):
      response = exception_handler(exc, context)
      
      if response is not None:
          response.data = {
              'error': {
                  'code': response.status_code,
                  'message': str(exc),
                  'detail': response.data
              }
          }
      
      return response
  ```
- [ ] Define custom exceptions:
  - `CVNotFoundError`
  - `SectionNotFoundError`
  - `InvalidLanguageError`
- [ ] Consistent error response format

**Verification Checks**:
- [ ] 404 errors return structured JSON
- [ ] 400 errors include validation details
- [ ] 500 errors don't leak sensitive info

### Task 2.8: API Response Examples

**Create example responses for documentation**:

```json
// GET /api/v1/cvs/
{
  "cvs": ["ramin", "mahsa"]
}

// GET /api/v1/cvs/ramin/?lang=en
{
  "basics": [{
    "fname": "Ramin",
    "lname": "Yazdani",
    "label": ["Data Scientist", "Machine Learning Engineer"],
    "email": "user@example.com"
  }],
  "profiles": [...],
  "education": [...],
  "skills": {...},
  ...
}

// GET /api/v1/cvs/ramin/education/?lang=en
{
  "education": [
    {
      "institution": "University Name",
      "studyType": "M.Sc.",
      "area": "Computer Science",
      "startDate": "2019",
      "endDate": "2021"
    }
  ]
}

// Error Response
{
  "error": {
    "code": 404,
    "message": "CV not found",
    "detail": {"person": "unknown"}
  }
}
```

---

## Self-Overseer Checklist

Before marking complete:
- [ ] All endpoints implemented and working
- [ ] Serializers validate data correctly
- [ ] Error handling consistent
- [ ] Health check accessible
- [ ] API documentation complete
- [ ] All endpoints tested manually
- [ ] Response times acceptable (&lt; 100ms)

---

## Success Criteria

- [ ] `curl /api/v1/cvs/` returns CV list
- [ ] `curl /api/v1/cvs/ramin/` returns full CV
- [ ] Language parameter works correctly
- [ ] 404 errors formatted correctly
- [ ] API documentation matches implementation

---

## Dependencies
- **Requires**: Plan 0 (Backend Setup), Plan 1 (Data Model)

## Estimated Effort
- 2-3 days

---

## Integration Notes

These endpoints will be consumed by:
- React frontend for data fetching
- Potential mobile apps
- Third-party integrations

Frontend will call:
- `/api/v1/cvs/{person}/?lang={lang}` for full CV data
- Section-specific endpoints for lazy loading (optional)
