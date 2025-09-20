from basics import process_basics
from profiles import process_profiles
from education import process_education
from languages import process_languages
from certifications import process_certifications
from skills import process_skills
from experiences import process_experiences
from projects import process_projects
from publications import process_publications
from references import process_references

HANDLERS = {
    # TODO: ensure keys match your JSON exactly
    "basics": process_basics,
    "profiles": process_profiles,
    "education": process_education,
    "languages": process_languages,
    "certifications": process_certifications,  # or "certificationAndCourses"
    "skills": process_skills,
    "experiences": process_experiences,        # or "experience"
    "projects": process_projects,
    "publications": process_publications,
    "references": process_references,
}
