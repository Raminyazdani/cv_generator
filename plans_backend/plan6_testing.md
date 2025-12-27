# Plan 6: Backend Testing

## Goal
Implement comprehensive testing for the Django backend including unit tests, API tests, integration tests, and test coverage reporting.

## Scope
This plan covers:
- Test infrastructure setup
- Unit tests for services and utilities
- API endpoint tests
- Integration tests
- Test coverage configuration

---

## CRITICAL RULES (MUST FOLLOW)

### LOCKED FILES / IMMUTABILITY
- `data/cvs/ramin.json`, `data/cvs/mahsa.json` are byte-identical locked inputs.
- **Absolutely no edits, no formatting changes, no sorting, no whitespace modifications** to these files.
- Tests should use these files as fixtures, reading them directly without modification.

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

### Task 6.1: Test Infrastructure Setup

**Acceptance Criteria**:
- [ ] Configure pytest-django:
  ```python
  # pytest.ini or pyproject.toml
  [tool.pytest.ini_options]
  DJANGO_SETTINGS_MODULE = "cv_backend.settings.testing"
  python_files = ["test_*.py", "*_test.py"]
  addopts = "-v --tb=short"
  ```
- [ ] Create testing settings:
  ```python
  # settings/testing.py
  from .base import *
  
  DEBUG = False
  
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.sqlite3',
          'NAME': ':memory:',
      }
  }
  
  # Faster password hashing for tests
  PASSWORD_HASHERS = [
      'django.contrib.auth.hashers.MD5PasswordHasher',
  ]
  
  # Disable caching
  CACHES = {
      'default': {
          'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
      }
  }
  ```
- [ ] Create test directory structure:
  ```
  apps/cv/tests/
  ├── __init__.py
  ├── conftest.py
  ├── test_services.py
  ├── test_views.py
  ├── test_serializers.py
  └── fixtures/
  ```

**Verification Checks**:
- [ ] `pytest` runs without configuration errors
- [ ] Testing settings used during tests
- [ ] Test discovery works correctly

### Task 6.2: Test Fixtures

**Acceptance Criteria**:
- [ ] Create pytest fixtures in `conftest.py`:
  ```python
  import pytest
  from django.test import Client
  from rest_framework.test import APIClient
  
  @pytest.fixture
  def api_client():
      return APIClient()
  
  @pytest.fixture
  def authenticated_client(admin_user):
      client = APIClient()
      client.force_authenticate(user=admin_user)
      return client
  
  @pytest.fixture
  def sample_cv_data():
      """Load sample CV data from locked JSON files."""
      from apps.cv.services import CVDataService
      return CVDataService().get_cv_data('ramin')
  
  @pytest.fixture
  def cv_service():
      from apps.cv.services import CVDataService
      return CVDataService()
  ```
- [ ] Use locked JSON files as test fixtures (read-only)
- [ ] Create mock data for edge cases

**Verification Checks**:
- [ ] Fixtures load correctly
- [ ] Locked files used without modification
- [ ] Fixtures reusable across tests

### Task 6.3: Service Layer Unit Tests

**Acceptance Criteria**:
- [ ] Create tests in `test_services.py`:
  ```python
  import pytest
  from apps.cv.services import CVDataService
  
  class TestCVDataService:
      def test_list_available_cvs(self, cv_service):
          """Test listing available CV files."""
          cvs = cv_service.list_available_cvs()
          assert 'ramin' in cvs
          assert 'mahsa' in cvs
      
      def test_get_cv_data_valid_person(self, cv_service):
          """Test loading CV data for valid person."""
          data = cv_service.get_cv_data('ramin')
          assert 'basics' in data
          assert 'education' in data
      
      def test_get_cv_data_invalid_person(self, cv_service):
          """Test loading CV data for invalid person."""
          with pytest.raises(FileNotFoundError):
              cv_service.get_cv_data('nonexistent')
      
      def test_get_section(self, cv_service):
          """Test getting specific section."""
          education = cv_service.get_section('ramin', 'education')
          assert isinstance(education, list)
      
      def test_get_section_invalid(self, cv_service):
          """Test getting invalid section."""
          with pytest.raises(KeyError):
              cv_service.get_section('ramin', 'nonexistent_section')
      
      def test_data_caching(self, cv_service):
          """Test that data is cached on repeated access."""
          # First call loads from file
          data1 = cv_service.get_cv_data('ramin')
          # Second call should use cache
          data2 = cv_service.get_cv_data('ramin')
          assert data1 == data2
  ```
- [ ] Test all public methods of CVDataService
- [ ] Test error handling
- [ ] Test caching behavior

**Verification Checks**:
- [ ] All service tests pass
- [ ] Edge cases covered
- [ ] No modifications to locked files

### Task 6.4: API Endpoint Tests

**Acceptance Criteria**:
- [ ] Create tests in `test_views.py`:
  ```python
  import pytest
  from django.urls import reverse
  from rest_framework import status
  
  class TestCVListView:
      def test_list_cvs(self, api_client):
          """Test CV list endpoint."""
          response = api_client.get('/api/v1/cvs/')
          assert response.status_code == status.HTTP_200_OK
          assert 'cvs' in response.json()
      
      def test_list_cvs_returns_available_cvs(self, api_client):
          """Test that list includes known CVs."""
          response = api_client.get('/api/v1/cvs/')
          cvs = response.json()['cvs']
          assert 'ramin' in cvs
  
  class TestCVDetailView:
      def test_get_cv_valid_person(self, api_client):
          """Test getting CV for valid person."""
          response = api_client.get('/api/v1/cvs/ramin/')
          assert response.status_code == status.HTTP_200_OK
          assert 'basics' in response.json()
      
      def test_get_cv_invalid_person(self, api_client):
          """Test 404 for invalid person."""
          response = api_client.get('/api/v1/cvs/nonexistent/')
          assert response.status_code == status.HTTP_404_NOT_FOUND
      
      def test_language_parameter(self, api_client):
          """Test language query parameter."""
          response = api_client.get('/api/v1/cvs/ramin/?lang=en')
          assert response.status_code == status.HTTP_200_OK
      
      def test_invalid_language_parameter(self, api_client):
          """Test invalid language returns error."""
          response = api_client.get('/api/v1/cvs/ramin/?lang=invalid')
          assert response.status_code == status.HTTP_400_BAD_REQUEST
  
  class TestHealthCheckView:
      def test_health_check(self, api_client):
          """Test health check endpoint."""
          response = api_client.get('/api/v1/health/')
          assert response.status_code == status.HTTP_200_OK
          assert response.json()['status'] == 'healthy'
  ```
- [ ] Test all endpoints
- [ ] Test query parameters
- [ ] Test error responses
- [ ] Test response structure

**Verification Checks**:
- [ ] All API tests pass
- [ ] Response formats correct
- [ ] Error codes appropriate

### Task 6.5: Serializer Tests

**Acceptance Criteria**:
- [ ] Create tests in `test_serializers.py`:
  ```python
  import pytest
  from apps.cv.serializers import (
      BasicsSerializer,
      EducationSerializer,
      CVSerializer,
  )
  
  class TestBasicsSerializer:
      def test_valid_basics(self):
          """Test serializing valid basics data."""
          data = {
              'fname': 'Ramin',
              'lname': 'Yazdani',
              'label': ['Developer'],
          }
          serializer = BasicsSerializer(data=data)
          assert serializer.is_valid()
      
      def test_missing_required_field(self):
          """Test that required fields are enforced."""
          data = {'fname': 'Ramin'}  # Missing lname
          serializer = BasicsSerializer(data=data)
          assert not serializer.is_valid()
          assert 'lname' in serializer.errors
  
  class TestCVSerializer:
      def test_serialize_full_cv(self, sample_cv_data):
          """Test serializing complete CV data."""
          serializer = CVSerializer(data=sample_cv_data)
          assert serializer.is_valid(), serializer.errors
  ```
- [ ] Test serialization/deserialization
- [ ] Test validation rules
- [ ] Test with real CV data

**Verification Checks**:
- [ ] Serializers validate correctly
- [ ] Error messages clear
- [ ] Real data passes validation

### Task 6.6: Integration Tests

**Acceptance Criteria**:
- [ ] Create integration tests:
  ```python
  import pytest
  
  @pytest.mark.django_db
  class TestCVWorkflow:
      def test_full_cv_retrieval_workflow(self, api_client):
          """Test complete workflow of retrieving CV data."""
          # List available CVs
          list_response = api_client.get('/api/v1/cvs/')
          assert list_response.status_code == 200
          
          # Get first CV
          cvs = list_response.json()['cvs']
          person = cvs[0]
          
          # Get full CV data
          detail_response = api_client.get(f'/api/v1/cvs/{person}/')
          assert detail_response.status_code == 200
          
          # Verify structure
          data = detail_response.json()
          assert 'basics' in data
          assert len(data['basics']) > 0
      
      def test_cv_data_matches_locked_file(self, api_client, sample_cv_data):
          """Test that API returns same data as locked JSON file."""
          response = api_client.get('/api/v1/cvs/ramin/')
          api_data = response.json()
          
          # Verify key sections match
          assert api_data['basics'] == sample_cv_data['basics']
  ```
- [ ] Test complete workflows
- [ ] Verify data integrity
- [ ] Test multi-step processes

**Verification Checks**:
- [ ] Integration tests pass
- [ ] Data integrity maintained
- [ ] Workflows complete successfully

### Task 6.7: Test Coverage

**Acceptance Criteria**:
- [ ] Configure coverage.py:
  ```ini
  # .coveragerc
  [run]
  source = apps
  omit = 
      */migrations/*
      */tests/*
      */__init__.py
  
  [report]
  exclude_lines =
      pragma: no cover
      def __repr__
      raise NotImplementedError
  
  fail_under = 80
  ```
- [ ] Add coverage to CI pipeline
- [ ] Generate HTML reports:
  ```bash
  pytest --cov=apps --cov-report=html --cov-report=term
  ```

**Verification Checks**:
- [ ] Coverage report generated
- [ ] Coverage >= 80%
- [ ] HTML report viewable

### Task 6.8: Test Documentation

**Acceptance Criteria**:
- [ ] Document testing approach in `docs/testing.md`
- [ ] Include:
  - How to run tests
  - Test structure
  - Writing new tests
  - Coverage requirements
- [ ] Add test commands to Makefile:
  ```makefile
  test:
      pytest
  
  test-cov:
      pytest --cov=apps --cov-report=html
  
  test-fast:
      pytest -x --ff
  ```

**Verification Checks**:
- [ ] Documentation complete
- [ ] Commands work as documented
- [ ] New developer can run tests

---

## Self-Overseer Checklist

Before marking complete:
- [ ] Test infrastructure working
- [ ] All fixtures created
- [ ] Service tests passing
- [ ] API tests passing
- [ ] Serializer tests passing
- [ ] Integration tests passing
- [ ] Coverage >= 80%
- [ ] Documentation complete

---

## Success Criteria

- [ ] `pytest` runs all tests successfully
- [ ] Test coverage >= 80%
- [ ] No modifications to locked JSON files
- [ ] Tests documented and reproducible

---

## Dependencies
- **Requires**: Plans 0-5 (all backend implementation)

## Estimated Effort
- 2-3 days

---

## Test Categories Summary

| Category | Location | Purpose |
|----------|----------|---------|
| Unit | test_services.py | Test service layer logic |
| API | test_views.py | Test REST endpoints |
| Serializer | test_serializers.py | Test data validation |
| Integration | test_integration.py | Test full workflows |
