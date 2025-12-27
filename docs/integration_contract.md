# Integration Contract

This document defines the API contract between the Django backend and React frontend for the CV Generator project.

---

## Overview

The backend serves CV data via REST API, and the frontend consumes this data to render an interactive CV/portfolio website.

---

## Base Configuration

### Development
```
Backend: http://localhost:8000
Frontend: http://localhost:3000
API Base: http://localhost:8000/api/v1/
```

### Production
```
Backend: https://api.example.com
Frontend: https://www.example.com
API Base: https://api.example.com/api/v1/
```

---

## Endpoints

### 1. Health Check

**Endpoint:** `GET /api/v1/health/`

**Purpose:** Verify backend is running and healthy

**Request:**
```http
GET /api/v1/health/ HTTP/1.1
Host: localhost:8000
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "database": {"status": "error", "message": "Connection failed"}
  }
}
```

---

### 2. List Available CVs

**Endpoint:** `GET /api/v1/cvs/`

**Purpose:** Get list of all available CV persons

**Request:**
```http
GET /api/v1/cvs/ HTTP/1.1
Host: localhost:8000
```

**Response (200 OK):**
```json
{
  "cvs": ["ramin", "mahsa"]
}
```

---

### 3. Get Full CV Data

**Endpoint:** `GET /api/v1/cvs/{person}/`

**Purpose:** Get complete CV data for a person

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `person` | string | Person identifier (e.g., "ramin", "mahsa") |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang` | string | "en" | Language code (en, de, fa) |
| `focus` | string | null | Filter by type_key value |

**Request Examples:**

```http
# English (default)
GET /api/v1/cvs/ramin/ HTTP/1.1

# German
GET /api/v1/cvs/ramin/?lang=de HTTP/1.1

# Persian (Farsi)
GET /api/v1/cvs/ramin/?lang=fa HTTP/1.1

# Filtered by Programming focus
GET /api/v1/cvs/ramin/?lang=en&focus=Programming HTTP/1.1
```

**Response (200 OK):**
```json
{
  "basics": [
    {
      "fname": "Ramin",
      "lname": "Yazdani",
      "label": ["Data Scientist", "Machine Learning Engineer"],
      "email": "user@example.com",
      "phone": {
        "formatted": "+49 (0) 123 456789"
      },
      "location": [
        {
          "city": "Saarbrücken",
          "region": "Saarland",
          "postalCode": "66123",
          "country": "Germany"
        }
      ],
      "summary": "Experienced data scientist...",
      "Pictures": [
        {
          "type_of": "profile",
          "URL": "/api/v1/cvs/ramin/picture/"
        }
      ]
    }
  ],
  "profiles": [
    {
      "network": "Github",
      "username": "ramin-yazdani",
      "url": "https://github.com/ramin-yazdani"
    },
    {
      "network": "LinkedIn",
      "username": "ramin-yazdani",
      "url": "https://linkedin.com/in/ramin-yazdani"
    }
  ],
  "education": [
    {
      "institution": "University Name",
      "studyType": "M.Sc.",
      "area": "Computer Science",
      "location": "City, Country",
      "startDate": "2019",
      "endDate": "2021",
      "gpa": "1.5",
      "type_key": ["Academic", "Programming"]
    }
  ],
  "experiences": [
    {
      "institution": "Company Name",
      "role": "Data Scientist",
      "location": "City, Country",
      "duration": "2020 - Present",
      "primaryFocus": "Machine learning development",
      "description": "Building ML pipelines...",
      "type_key": ["Programming", "Data Science"]
    }
  ],
  "skills": {
    "Technical Skills": {
      "Programming Languages": [
        {
          "short_name": "Python",
          "long_name": "Python Programming",
          "type_key": ["Programming"]
        }
      ],
      "Data Science": [
        {
          "short_name": "Pandas",
          "type_key": ["Programming", "Data Science"]
        }
      ]
    },
    "Soft Skills": {
      "Communication": [
        {
          "short_name": "Public Speaking",
          "type_key": ["Full CV"]
        }
      ]
    }
  },
  "projects": [
    {
      "title": "Project Name",
      "description": "Project description...",
      "url": "https://github.com/project",
      "technologies": ["Python", "React"],
      "type_key": ["Programming"]
    }
  ],
  "publications": [
    {
      "title": "Publication Title",
      "type": "Journal Article",
      "status": "Published",
      "date": "2023-05-15",
      "authors": ["Author 1", "Author 2"],
      "journal": "Journal Name",
      "doi": "10.1000/example",
      "url": "https://doi.org/10.1000/example",
      "type_key": ["Academic", "Research"]
    }
  ],
  "languages": [
    {
      "language": "English",
      "proficiency": "Professional"
    },
    {
      "language": "German",
      "proficiency": "Intermediate"
    },
    {
      "language": "Persian",
      "proficiency": "Native"
    }
  ],
  "workshop_and_certifications": [
    {
      "title": "Certification Name",
      "issuer": "Issuing Organization",
      "date": "2023-01-15",
      "type_key": ["Programming"]
    }
  ],
  "references": [
    {
      "name": "Reference Name",
      "position": "Professor",
      "institution": "University",
      "email": ["reference@example.com"],
      "phone": ["+1 234 567 890"],
      "type_key": ["Academic"]
    }
  ]
}
```

**Response (404 Not Found):**
```json
{
  "error": {
    "code": 404,
    "message": "CV not found",
    "detail": {
      "person": "nonexistent"
    }
  }
}
```

**Response (400 Bad Request - Invalid Language):**
```json
{
  "error": {
    "code": 400,
    "message": "Invalid language",
    "detail": {
      "lang": "xx",
      "valid_languages": ["en", "de", "fa"]
    }
  }
}
```

---

### 4. Get Specific Section

**Endpoint:** `GET /api/v1/cvs/{person}/{section}/`

**Purpose:** Get a specific section of CV data (for lazy loading)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `person` | string | Person identifier |
| `section` | string | Section name |

**Valid Sections:**
- `basics`
- `profiles`
- `education`
- `experiences`
- `skills`
- `projects`
- `publications`
- `languages`
- `certifications` (maps to workshop_and_certifications)
- `references`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang` | string | "en" | Language code |

**Request:**
```http
GET /api/v1/cvs/ramin/education/?lang=en HTTP/1.1
```

**Response (200 OK):**
```json
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
```

---

### 5. Download PDF

**Endpoint:** `GET /api/v1/cvs/{person}/pdf/`

**Purpose:** Download generated PDF CV

**Request:**
```http
GET /api/v1/cvs/ramin/pdf/ HTTP/1.1
```

**Response (200 OK):**
```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="ramin_cv.pdf"
Content-Length: 123456

[PDF binary content]
```

**Response (404 Not Found):**
```json
{
  "error": {
    "code": 404,
    "message": "PDF not found. Generate it first."
  }
}
```

---

### 6. Get Profile Picture

**Endpoint:** `GET /api/v1/cvs/{person}/picture/`

**Purpose:** Get profile picture for a person

**Request:**
```http
GET /api/v1/cvs/ramin/picture/ HTTP/1.1
```

**Response (200 OK):**
```http
HTTP/1.1 200 OK
Content-Type: image/jpeg
Cache-Control: max-age=86400

[Image binary content]
```

**Response (404 Not Found):**
```json
{
  "error": {
    "code": 404,
    "message": "Profile picture not found"
  }
}
```

---

## Language Parameter Rules

| Value | Description | Direction |
|-------|-------------|-----------|
| `en` | English (default) | LTR |
| `de` | German (Deutsch) | LTR |
| `fa` | Persian (Farsi) | RTL |

**Frontend Behavior:**
- Set `<html lang="{lang}" dir="{dir}">`
- Load corresponding translations for UI strings
- Apply RTL styles for Persian

**Fallback Chain:**
1. Requested language
2. English
3. Error if English not available

---

## Focus Filtering Rules

When `focus` parameter is provided:

1. Filter all arrays (education, experiences, projects, etc.)
2. Keep only items where `type_key` array contains the focus value
3. `focus=Full CV` or no focus: return all items
4. Skills: filter individual skill items, not categories

**Example:**
```
?focus=Programming
```

Returns only items where `"Programming"` is in their `type_key` array.

---

## Caching Rules

| Endpoint | Cache Duration | Notes |
|----------|----------------|-------|
| `/health/` | No cache | Always fresh |
| `/cvs/` | 5 minutes | List rarely changes |
| `/cvs/{person}/` | 5 minutes | CV data rarely changes |
| `/cvs/{person}/pdf/` | 1 hour | PDFs are static |
| `/cvs/{person}/picture/` | 1 day | Images rarely change |

**Cache Headers:**
```http
Cache-Control: public, max-age=300
ETag: "abc123"
```

**Conditional Requests:**
```http
If-None-Match: "abc123"
```

---

## Error Response Format

All errors follow this format:

```json
{
  "error": {
    "code": <HTTP status code>,
    "message": "<Human-readable message>",
    "detail": {
      "<field>": "<specific error info>"
    }
  }
}
```

**Common Error Codes:**
| Code | Meaning |
|------|---------|
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found (CV, section, or file doesn't exist) |
| 429 | Too Many Requests (rate limit exceeded) |
| 500 | Internal Server Error |

---

## CORS Configuration

**Allowed Origins:**
- Development: `http://localhost:3000`
- Production: `https://www.example.com`

**Allowed Methods:**
- `GET`
- `OPTIONS`

**Allowed Headers:**
- `Accept`
- `Content-Type`
- `Origin`

---

## Local Development

### Running Frontend with Backend

1. **Start Backend:**
   ```bash
   cd cv_backend
   python manage.py runserver 8000
   ```

2. **Start Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Configure Frontend Proxy (Vite):**
   ```typescript
   // vite.config.ts
   export default {
     server: {
       proxy: {
         '/api': 'http://localhost:8000'
       }
     }
   }
   ```

### Testing Integration

```bash
# Test backend directly
curl http://localhost:8000/api/v1/cvs/

# Test from frontend (should work via proxy)
# In browser console:
fetch('/api/v1/cvs/').then(r => r.json()).then(console.log)
```

---

## TypeScript Types (Frontend)

```typescript
interface CVResponse {
  basics: Basics[];
  profiles: Profile[];
  education: Education[];
  experiences: Experience[];
  skills: SkillsSection;
  projects: Project[];
  publications: Publication[];
  languages: Language[];
  workshop_and_certifications: Certification[];
  references: Reference[];
}

interface Basics {
  fname: string;
  lname: string;
  label: string[];
  email?: string;
  phone?: { formatted?: string };
  location?: Location[];
  summary?: string;
  Pictures?: Picture[];
}

interface Education {
  institution: string;
  studyType?: string;
  area?: string;
  location?: string;
  startDate?: string;
  endDate?: string;
  gpa?: string;
  type_key?: string[];
}

// ... (see plans_frontend/plan1_project_setup.md for complete types)
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-01-15 | Initial contract |
