# Plan 5: Static & Media File Handling

## Goal
Configure Django to properly serve static assets (CSS, JS, images) and media files (uploaded content, generated PDFs) for both development and production environments.

## Scope
This plan covers:
- Static file configuration
- Media file handling
- PDF output serving
- Profile picture serving
- Production-ready static file setup

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

### Task 5.1: Static Files Configuration

**Acceptance Criteria**:
- [ ] Configure static file settings:
  ```python
  # settings/base.py
  STATIC_URL = '/static/'
  
  STATICFILES_DIRS = [
      BASE_DIR / 'static',
  ]
  
  # Production
  STATIC_ROOT = BASE_DIR / 'staticfiles'
  
  STATICFILES_FINDERS = [
      'django.contrib.staticfiles.finders.FileSystemFinder',
      'django.contrib.staticfiles.finders.AppDirectoriesFinder',
  ]
  ```
- [ ] Create static directory structure:
  ```
  static/
  ├── css/
  ├── js/
  └── images/
  ```
- [ ] Configure WhiteNoise for production:
  ```python
  MIDDLEWARE = [
      'whitenoise.middleware.WhiteNoiseMiddleware',
      ...
  ]
  
  STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
  ```

**Verification Checks**:
- [ ] `collectstatic` runs without errors
- [ ] Static files accessible in development
- [ ] WhiteNoise serves files in production

### Task 5.2: Media Files Configuration

**Acceptance Criteria**:
- [ ] Configure media file settings:
  ```python
  # settings/base.py
  MEDIA_URL = '/media/'
  MEDIA_ROOT = BASE_DIR / 'media'
  ```
- [ ] Create media directory structure:
  ```
  media/
  ├── uploads/     # User uploads (if any)
  └── generated/   # Generated PDFs
  ```
- [ ] Configure URL patterns for media serving (development):
  ```python
  # urls.py
  from django.conf import settings
  from django.conf.urls.static import static
  
  if settings.DEBUG:
      urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
  ```

**Verification Checks**:
- [ ] Media files accessible in development
- [ ] Upload directory writable
- [ ] Generated files stored correctly

### Task 5.3: PDF Output Serving

**Acceptance Criteria**:
- [ ] Configure PDF output handling:
  ```python
  # settings/base.py
  PDF_OUTPUT_DIR = BASE_DIR.parent / 'output'
  ```
- [ ] Create API endpoint to serve PDFs:
  ```python
  # apps/cv/views.py
  from django.http import FileResponse
  
  class CVPDFView(APIView):
      def get(self, request, person):
          pdf_path = settings.PDF_OUTPUT_DIR / f'{person}.pdf'
          
          if not pdf_path.exists():
              raise Http404("PDF not found")
          
          return FileResponse(
              open(pdf_path, 'rb'),
              content_type='application/pdf',
              as_attachment=True,
              filename=f'{person}_cv.pdf'
          )
  ```
- [ ] Add URL: `GET /api/v1/cvs/{person}/pdf/`
- [ ] Handle missing PDFs gracefully
- [ ] Set appropriate headers for download

**Verification Checks**:
- [ ] PDF endpoint returns PDF file
- [ ] Content-Disposition header set for download
- [ ] Missing PDF returns 404
- [ ] Large PDFs stream correctly

### Task 5.4: Profile Picture Serving

**Acceptance Criteria**:
- [ ] Configure profile picture access:
  ```python
  # settings/base.py
  PROFILE_PICS_DIR = BASE_DIR.parent / 'data' / 'pics'
  ```
- [ ] Create endpoint to serve profile pictures:
  ```python
  # apps/cv/views.py
  class ProfilePictureView(APIView):
      def get(self, request, person):
          # Try different extensions
          for ext in ['jpg', 'jpeg', 'png']:
              pic_path = settings.PROFILE_PICS_DIR / f'{person}.{ext}'
              if pic_path.exists():
                  return FileResponse(
                      open(pic_path, 'rb'),
                      content_type=f'image/{ext}'
                  )
          
          raise Http404("Profile picture not found")
  ```
- [ ] Add URL: `GET /api/v1/cvs/{person}/picture/`
- [ ] Support multiple image formats (jpg, png)
- [ ] Add caching headers for images

**Verification Checks**:
- [ ] Profile pictures accessible via API
- [ ] Correct content-type returned
- [ ] Missing pictures return 404
- [ ] Cache headers present

### Task 5.5: File Security

**Acceptance Criteria**:
- [ ] Prevent directory traversal attacks:
  ```python
  import os
  
  def safe_file_access(base_dir: Path, filename: str) -> Path:
      """Safely resolve file path, preventing directory traversal."""
      # Normalize and resolve the path
      requested_path = (base_dir / filename).resolve()
      
      # Ensure it's still under base_dir
      if not str(requested_path).startswith(str(base_dir.resolve())):
          raise PermissionError("Invalid file path")
      
      return requested_path
  ```
- [ ] Validate file extensions
- [ ] Set X-Content-Type-Options: nosniff
- [ ] Limit file sizes for responses

**Verification Checks**:
- [ ] Directory traversal attempts blocked
- [ ] Only allowed file types served
- [ ] Security headers present

### Task 5.6: Production Static File Strategy

**Acceptance Criteria**:
- [ ] Document production options:
  - WhiteNoise (simple, included in app)
  - Nginx (recommended for high traffic)
  - CDN (for global distribution)
- [ ] Configure WhiteNoise compression
- [ ] Set up cache headers:
  ```python
  WHITENOISE_MAX_AGE = 31536000  # 1 year for hashed files
  ```
- [ ] Document Nginx configuration example:
  ```nginx
  location /static/ {
      alias /path/to/staticfiles/;
      expires 1y;
      add_header Cache-Control "public, immutable";
  }
  
  location /media/ {
      alias /path/to/media/;
      expires 30d;
  }
  ```

**Verification Checks**:
- [ ] WhiteNoise configured correctly
- [ ] Cache headers appropriate
- [ ] Nginx config documented

### Task 5.7: Data Directory Access

**Acceptance Criteria**:
- [ ] Configure read-only access to data directory:
  ```python
  # settings/base.py
  DATA_DIR = BASE_DIR.parent / 'data'
  CVS_DIR = DATA_DIR / 'cvs'
  PICS_DIR = DATA_DIR / 'pics'
  ```
- [ ] Ensure data files not directly web-accessible
- [ ] Access only through API endpoints
- [ ] Document data directory structure

**Verification Checks**:
- [ ] Data files not at public URLs
- [ ] API endpoints provide controlled access
- [ ] Directory structure documented

---

## Self-Overseer Checklist

Before marking complete:
- [ ] Static files serving correctly
- [ ] Media files configured properly
- [ ] PDF endpoint working
- [ ] Profile pictures accessible
- [ ] File security implemented
- [ ] Production strategy documented
- [ ] Data directory access controlled

---

## Success Criteria

- [ ] `collectstatic` runs without errors
- [ ] Static files load in browser
- [ ] PDFs downloadable via API
- [ ] Profile pictures load correctly
- [ ] No security vulnerabilities in file serving

---

## Dependencies
- **Requires**: Plan 0 (Backend Setup), Plan 2 (API Design)

## Estimated Effort
- 1-2 days

---

## Integration Notes

File serving integrates with:
- Frontend for loading profile pictures
- Admin for PDF downloads
- Existing `generate_cv.py` for PDF output

Production considerations:
- Use CDN for global distribution
- Configure proper caching headers
- Consider S3/CloudStorage for scalability
