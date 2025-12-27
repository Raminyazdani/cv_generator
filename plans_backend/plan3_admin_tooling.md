# Plan 3: Admin Tooling & Content Management

## Goal
Set up Django admin interface for content management, including CV data viewing, user management, and optional content editing workflows.

## Scope
This plan covers:
- Django admin configuration
- Admin views for CV data (read-only initially)
- User authentication and permissions
- Content preview functionality
- PDF generation from admin

---

## CRITICAL RULES (MUST FOLLOW)

### LOCKED FILES / IMMUTABILITY
- `data/cvs/ramin.json`, `data/cvs/mahsa.json` are byte-identical locked inputs.
- **Absolutely no edits, no formatting changes, no sorting, no whitespace modifications** to these files.
- Admin interface should provide READ-ONLY views of locked files.

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

### Task 3.1: Django Admin Configuration

**Acceptance Criteria**:
- [ ] Configure Django admin in settings
- [ ] Customize admin site branding:
  ```python
  admin.site.site_header = "CV Generator Admin"
  admin.site.site_title = "CV Generator"
  admin.site.index_title = "Administration"
  ```
- [ ] Set up admin URLs with security
- [ ] Enable admin documentation (optional)

**Verification Checks**:
- [ ] Admin accessible at `/admin/`
- [ ] Custom branding displayed
- [ ] Login required for access

### Task 3.2: User Authentication Setup

**Acceptance Criteria**:
- [ ] Create superuser creation command/script
- [ ] Configure authentication settings:
  ```python
  AUTHENTICATION_BACKENDS = [
      'django.contrib.auth.backends.ModelBackend',
  ]
  
  LOGIN_URL = '/admin/login/'
  LOGIN_REDIRECT_URL = '/admin/'
  ```
- [ ] Set password validators for production
- [ ] Document user creation process

**Verification Checks**:
- [ ] Superuser can log into admin
- [ ] Regular users denied admin access (unless staff)
- [ ] Password requirements enforced

### Task 3.3: CV Data Admin Views (Read-Only)

**Acceptance Criteria**:
- [ ] Create custom admin views for CV data browsing
- [ ] Display list of available CVs
- [ ] Show CV data in structured format:
  - Basics (personal info)
  - Education (table view)
  - Experience (table view)
  - Skills (categorized view)
  - Projects, Publications, References
- [ ] All views READ-ONLY (no edit capability for locked files)

**Implementation**:
```python
# apps/cv/admin.py
from django.contrib import admin
from django.urls import path
from django.template.response import TemplateResponse

class CVAdminSite(admin.AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('cv-browser/', self.admin_view(self.cv_browser_view), name='cv-browser'),
            path('cv-browser/<str:person>/', self.admin_view(self.cv_detail_view), name='cv-detail'),
        ]
        return custom_urls + urls
    
    def cv_browser_view(self, request):
        context = {
            **self.each_context(request),
            'cvs': CVDataService().list_available_cvs(),
        }
        return TemplateResponse(request, 'admin/cv_browser.html', context)
    
    def cv_detail_view(self, request, person):
        context = {
            **self.each_context(request),
            'person': person,
            'cv_data': CVDataService().get_cv_data(person),
        }
        return TemplateResponse(request, 'admin/cv_detail.html', context)
```

**Verification Checks**:
- [ ] CV browser shows all available CVs
- [ ] CV detail shows all sections
- [ ] No edit buttons/forms present
- [ ] Data displays correctly

### Task 3.4: Admin Templates for CV Display

**Acceptance Criteria**:
- [ ] Create admin templates:
  - `templates/admin/cv_browser.html`
  - `templates/admin/cv_detail.html`
  - `templates/admin/cv_section.html` (partial)
- [ ] Style consistent with Django admin
- [ ] Responsive layout for different screen sizes
- [ ] Clear section organization

**Verification Checks**:
- [ ] Templates render without errors
- [ ] Styling consistent with admin theme
- [ ] Data displays in readable format
- [ ] Navigation between CVs works

### Task 3.5: PDF Generation from Admin

**Acceptance Criteria**:
- [ ] Add "Generate PDF" button to CV detail view
- [ ] Integrate with existing `generate_cv.py` script
- [ ] Create wrapper service:
  ```python
  # apps/cv/services.py
  class PDFGenerationService:
      def generate_pdf(self, person: str) -> Path:
          """Generate PDF for a person, return path to file."""
          # Call existing generate_cv.py logic
          pass
      
      def get_pdf_path(self, person: str) -> Optional[Path]:
          """Get path to existing PDF if available."""
          pass
  ```
- [ ] Serve generated PDF for download
- [ ] Handle generation errors gracefully

**Verification Checks**:
- [ ] "Generate PDF" button visible in admin
- [ ] Clicking button triggers PDF generation
- [ ] PDF downloads successfully
- [ ] Error messages displayed on failure

### Task 3.6: Content Preview

**Acceptance Criteria**:
- [ ] Add preview button for CV data
- [ ] Preview shows how data will appear:
  - In PDF format (generated preview)
  - In frontend format (link to frontend preview)
- [ ] Language selection for preview
- [ ] Focus filter option in preview

**Verification Checks**:
- [ ] Preview button works
- [ ] Preview reflects current data
- [ ] Language switching works in preview

### Task 3.7: Admin Action Logging

**Acceptance Criteria**:
- [ ] Log admin actions (views, PDF generations)
- [ ] Use Django's built-in logging
- [ ] Log format includes:
  - Timestamp
  - User
  - Action
  - Target (CV person)
  - Result (success/failure)

**Verification Checks**:
- [ ] Actions logged to file/console
- [ ] Logs include required information
- [ ] No sensitive data logged

---

## Self-Overseer Checklist

Before marking complete:
- [ ] Admin interface accessible and styled
- [ ] User authentication working
- [ ] CV data viewable in admin
- [ ] No edit capabilities for locked files
- [ ] PDF generation working from admin
- [ ] Preview functionality implemented
- [ ] Action logging configured

---

## Success Criteria

- [ ] Admin login works with superuser
- [ ] CV browser displays all CVs
- [ ] CV detail shows all sections correctly
- [ ] PDF generation works from admin
- [ ] No ability to modify locked JSON files

---

## Dependencies
- **Requires**: Plan 0 (Backend Setup), Plan 1 (Data Model)

## Estimated Effort
- 2-3 days

---

## Integration Notes

The admin interface provides:
- Read-only access to CV data
- PDF generation capability
- Content preview functionality

Future enhancements (out of scope):
- Database-backed CV editing
- Content approval workflows
- Version history
