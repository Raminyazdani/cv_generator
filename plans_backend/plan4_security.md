# Plan 4: Security Configuration

## Goal
Implement security best practices for the Django backend including CORS configuration, secure headers, rate limiting, and input validation.

## Scope
This plan covers:
- CORS configuration for frontend integration
- Security headers (CSP, X-Frame-Options, etc.)
- Rate limiting for API endpoints
- Input validation and sanitization
- Authentication considerations

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

### Task 4.1: CORS Configuration

**Acceptance Criteria**:
- [ ] Install and configure `django-cors-headers`
- [ ] Configure CORS settings:
  ```python
  # settings/base.py
  INSTALLED_APPS = [
      ...
      'corsheaders',
  ]
  
  MIDDLEWARE = [
      'corsheaders.middleware.CorsMiddleware',
      'django.middleware.common.CommonMiddleware',
      ...
  ]
  
  # Development settings
  CORS_ALLOWED_ORIGINS = [
      'http://localhost:3000',  # React dev server
      'http://127.0.0.1:3000',
  ]
  
  # Or for development: CORS_ALLOW_ALL_ORIGINS = True
  
  CORS_ALLOW_METHODS = [
      'GET',
      'OPTIONS',
  ]
  
  CORS_ALLOW_HEADERS = [
      'accept',
      'accept-encoding',
      'authorization',
      'content-type',
      'origin',
      'user-agent',
      'x-requested-with',
  ]
  ```
- [ ] Production CORS settings from environment variables
- [ ] Restrict allowed methods to GET, OPTIONS (read-only API)

**Verification Checks**:
- [ ] Frontend can fetch from API without CORS errors
- [ ] Unauthorized origins rejected
- [ ] Preflight OPTIONS requests handled correctly

### Task 4.2: Security Headers

**Acceptance Criteria**:
- [ ] Configure Django security middleware
- [ ] Set security headers:
  ```python
  # settings/production.py
  SECURE_BROWSER_XSS_FILTER = True
  SECURE_CONTENT_TYPE_NOSNIFF = True
  X_FRAME_OPTIONS = 'DENY'
  
  # HTTPS settings (when using HTTPS)
  SECURE_SSL_REDIRECT = True
  SECURE_HSTS_SECONDS = 31536000
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  SECURE_HSTS_PRELOAD = True
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  ```
- [ ] Content Security Policy:
  ```python
  # Using django-csp or custom middleware
  CSP_DEFAULT_SRC = ("'self'",)
  CSP_SCRIPT_SRC = ("'self'",)
  CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
  CSP_IMG_SRC = ("'self'", "data:")
  CSP_FONT_SRC = ("'self'",)
  ```

**Verification Checks**:
- [ ] Security headers present in responses
- [ ] X-Frame-Options prevents clickjacking
- [ ] HTTPS enforced in production

### Task 4.3: Rate Limiting

**Acceptance Criteria**:
- [ ] Install rate limiting package (e.g., `django-ratelimit`)
- [ ] Configure rate limits for API endpoints:
  ```python
  # Rate limit configuration
  RATELIMIT_VIEW = 'apps.core.views.rate_limited_view'
  
  # Apply to views
  from django_ratelimit.decorators import ratelimit
  
  @ratelimit(key='ip', rate='100/m', method='GET')
  def cv_detail_view(request, person):
      ...
  ```
- [ ] Limits:
  - CV list: 100 requests/minute
  - CV detail: 100 requests/minute
  - Health check: Unlimited
- [ ] Return 429 Too Many Requests when exceeded
- [ ] Include rate limit headers in response

**Verification Checks**:
- [ ] Normal requests succeed
- [ ] Excessive requests return 429
- [ ] Rate limit headers present
- [ ] Different limits work for different endpoints

### Task 4.4: Input Validation

**Acceptance Criteria**:
- [ ] Validate all API query parameters:
  ```python
  # Valid languages
  VALID_LANGUAGES = ['en', 'de', 'fa']
  
  # Valid person names (derived from CV files)
  def validate_person(value):
      available = CVDataService().list_available_cvs()
      if value not in available:
          raise ValidationError(f"Invalid person: {value}")
  
  # Valid section names
  VALID_SECTIONS = ['basics', 'profiles', 'education', ...]
  ```
- [ ] Sanitize path parameters (prevent directory traversal)
- [ ] Validate and sanitize URL parameters
- [ ] Return clear validation error messages

**Implementation**:
```python
# apps/cv/validators.py
import re

def validate_person_name(name: str) -> str:
    """Validate and sanitize person name parameter."""
    # Only allow alphanumeric and underscore
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        raise ValidationError("Invalid person name format")
    
    # Check length
    if len(name) > 50:
        raise ValidationError("Person name too long")
    
    # Check existence
    available = CVDataService().list_available_cvs()
    if name not in available:
        raise Http404(f"CV not found: {name}")
    
    return name
```

**Verification Checks**:
- [ ] Valid inputs accepted
- [ ] Invalid language rejected with 400
- [ ] Invalid person returns 404
- [ ] Path traversal attempts blocked

### Task 4.5: Secret Key Management

**Acceptance Criteria**:
- [ ] Generate strong secret key for production
- [ ] Store secret key in environment variable
- [ ] Different keys for dev/staging/prod
- [ ] Document secret key generation:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```

**Verification Checks**:
- [ ] Secret key not in source code
- [ ] App fails to start without secret key
- [ ] Secret key in .env.example as placeholder

### Task 4.6: Debug Mode Security

**Acceptance Criteria**:
- [ ] DEBUG=False in production
- [ ] Configure ALLOWED_HOSTS properly:
  ```python
  # production.py
  ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')
  ```
- [ ] Custom error pages for 404, 500
- [ ] No sensitive info in error responses

**Verification Checks**:
- [ ] Debug mode off in production settings
- [ ] Error pages don't leak info
- [ ] ALLOWED_HOSTS configured from env

### Task 4.7: Logging Security Events

**Acceptance Criteria**:
- [ ] Log security-relevant events:
  - Failed authentication attempts
  - Rate limit hits
  - Validation failures
  - Suspicious requests
- [ ] Configure logging:
  ```python
  LOGGING = {
      'version': 1,
      'handlers': {
          'security': {
              'class': 'logging.handlers.RotatingFileHandler',
              'filename': 'logs/security.log',
              'maxBytes': 10485760,  # 10MB
              'backupCount': 5,
          },
      },
      'loggers': {
          'security': {
              'handlers': ['security'],
              'level': 'WARNING',
          },
      },
  }
  ```

**Verification Checks**:
- [ ] Security events logged
- [ ] Logs don't contain sensitive data
- [ ] Log rotation configured

---

## Self-Overseer Checklist

Before marking complete:
- [ ] CORS allows frontend access
- [ ] Security headers configured
- [ ] Rate limiting working
- [ ] Input validation on all endpoints
- [ ] Secret key management secure
- [ ] Debug mode off in production
- [ ] Security logging configured
- [ ] No security warnings from Django check

---

## Success Criteria

- [ ] `python manage.py check --deploy` passes (or minimal warnings)
- [ ] CORS works for frontend
- [ ] Rate limiting prevents abuse
- [ ] Invalid inputs rejected properly
- [ ] Security headers in all responses

---

## Dependencies
- **Requires**: Plan 0 (Backend Setup), Plan 2 (API Design)

## Estimated Effort
- 1-2 days

---

## Security Checklist Reference

For production deployment, ensure:
- [ ] SECRET_KEY is unique and secret
- [ ] DEBUG = False
- [ ] ALLOWED_HOSTS configured
- [ ] HTTPS enabled
- [ ] Security headers set
- [ ] CORS restricted to known origins
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Dependencies updated and audited
