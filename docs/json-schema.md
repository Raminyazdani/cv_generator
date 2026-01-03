# JSON Schema

CV data is stored as JSON files loosely based on the [JSON Resume](https://jsonresume.org/) format with customizations for Awesome-CV templates.

## File Location

CV files are stored in `data/cvs/`:

```
data/cvs/
├── ramin.json         # Single-language CV
├── ramin_de.json      # German version
├── ramin_fa.json      # Persian version
└── mahsa.json         # Another person's CV
```

## Top-Level Sections

| Section | Description | Required |
|---------|-------------|----------|
| `basics` | Personal information | Yes |
| `profiles` | Social links | No |
| `education` | Education history | No |
| `experiences` | Work experience | No |
| `skills` | Technical and soft skills | No |
| `languages` | Language proficiencies | No |
| `projects` | Projects and contributions | No |
| `publications` | Academic publications | No |
| `workshop_and_certifications` | Certifications | No |
| `references` | Professional references | No |

## Section Details

### basics

Personal information displayed in the CV header.

```json
{
  "basics": [{
    "fname": "Jane",
    "lname": "Doe",
    "label": ["Software Engineer", "ML Researcher"],
    "email": "jane@example.com",
    "phone": {
      "formatted": "+1 555-0100",
      "number": "5550100",
      "countryCode": "+1"
    },
    "birthDate": "1990-01-15",
    "summary": "Brief professional summary",
    "location": [{
      "address": "123 Main St",
      "city": "San Francisco",
      "region": "CA",
      "postalCode": "94102",
      "country": "USA"
    }]
  }]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `fname` | string | First name |
| `lname` | string | Last name |
| `label` | array | Job titles/roles |
| `email` | string | Email address |
| `phone.formatted` | string | Display phone number |
| `location` | array | Address information |
| `summary` | string | Brief bio (optional) |

### profiles

Social media and professional links.

```json
{
  "profiles": [
    {
      "network": "Github",
      "username": "janedoe"
    },
    {
      "network": "LinkedIn",
      "username": "janedoe"
    },
    {
      "network": "Google Scholar",
      "username": "Jane Doe",
      "uuid": "wpZDx1cAAAAJ"
    }
  ]
}
```

**Supported Networks:**

| Network | Template Macro |
|---------|----------------|
| `Github` | `\github{username}` |
| `LinkedIn` | `\linkedin{username}` |
| `Google Scholar` | `\googlescholar{uuid}{username}` |

### education

Academic history.

```json
{
  "education": [
    {
      "studyType": "M.Sc.",
      "area": "Computer Science",
      "institution": "Stanford University",
      "location": "Stanford, CA",
      "startDate": "2019",
      "endDate": "2021",
      "gpa": "3.9/4.0"
    },
    {
      "studyType": "B.Sc.",
      "area": "Software Engineering",
      "institution": "UC Berkeley",
      "location": "Berkeley, CA",
      "startDate": "2015",
      "endDate": "2019"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `studyType` | string | Degree type (B.Sc., M.Sc., Ph.D.) |
| `area` | string | Field of study |
| `institution` | string | University/school name |
| `location` | string | City, Country |
| `startDate` | string | Start year |
| `endDate` | string | End year (or "Present") |
| `gpa` | string | GPA (optional) |

### experiences

Work experience and professional roles.

```json
{
  "experiences": [
    {
      "institution": "Tech Corp",
      "role": "Senior Software Engineer",
      "location": "San Francisco, CA",
      "duration": "2021 – Present",
      "primaryFocus": "Leading backend development",
      "description": "Architecting microservices infrastructure"
    },
    {
      "institution": "Startup Inc",
      "role": "Software Engineer",
      "location": "Remote",
      "duration": "2019 – 2021",
      "description": "Full-stack web development"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `institution` | string | Company name |
| `role` | string | Job title |
| `location` | string | Work location |
| `duration` | string | Time period |
| `primaryFocus` | string | Main responsibility (optional) |
| `description` | string | Additional details (optional) |

### skills

Technical and soft skills organized by category.

```json
{
  "skills": {
    "Technical Skills": {
      "Programming": [
        {"short_name": "Python", "long_name": "Python 3.x"},
        {"short_name": "JavaScript"},
        {"short_name": "Go"}
      ],
      "Frameworks": [
        {"short_name": "React"},
        {"short_name": "Django"},
        {"short_name": "FastAPI"}
      ],
      "Tools": [
        {"short_name": "Git"},
        {"short_name": "Docker"},
        {"short_name": "Kubernetes"}
      ]
    },
    "Soft Skills": {
      "Leadership": [
        {"short_name": "Team Management"},
        {"short_name": "Mentoring"}
      ]
    }
  }
}
```

**Structure:**

1. **Section** (e.g., "Technical Skills") — Top-level grouping
2. **Category** (e.g., "Programming") — Skill category
3. **Items** — Individual skills with `short_name` and optional `long_name`

### languages

Language proficiencies.

```json
{
  "languages": [
    {
      "language": "English",
      "proficiency": "Native",
      "level": "C2",
      "CEFR": "C2"
    },
    {
      "language": "German",
      "proficiency": "Professional",
      "level": "B2",
      "certifications": [
        {
          "test": "TestDaF",
          "overall": "TDN 4",
          "examDate": "2020-06"
        }
      ]
    }
  ]
}
```

### publications

Academic and professional publications.

```json
{
  "publications": [
    {
      "type": "journal",
      "title": "Machine Learning for NLP",
      "authors": ["Jane Doe", "John Smith"],
      "journal": "Journal of AI Research",
      "year": "2023",
      "doi": "10.1234/jair.2023.001"
    },
    {
      "type": "conference",
      "title": "Deep Learning Approaches",
      "conference": "NeurIPS 2022",
      "year": "2022"
    }
  ]
}
```

### projects

Personal or professional projects.

```json
{
  "projects": [
    {
      "title": "Open Source Library",
      "url": "https://github.com/user/project",
      "description": "A library for data processing",
      "role": "Creator and Maintainer"
    }
  ]
}
```

### workshop_and_certifications

Certifications, courses, and workshops.

```json
{
  "workshop_and_certifications": [
    {
      "name": "AWS Solutions Architect",
      "issuer": "Amazon Web Services",
      "date": "2023-01",
      "certificate": "https://verify.example.com/123"
    }
  ]
}
```

### references

Professional references.

```json
{
  "references": [
    {
      "name": "Dr. John Smith",
      "position": "Professor",
      "department": "Computer Science",
      "institution": "Stanford University",
      "email": ["john.smith@stanford.edu"],
      "phone": "+1 555-0200"
    }
  ]
}
```

## Complete Example

See `data/cvs/ramin.json` for a complete, production-ready example.

## Validation

Use `cvgen ensure` to validate consistency across language versions:

```bash
cvgen ensure --name ramin
```
