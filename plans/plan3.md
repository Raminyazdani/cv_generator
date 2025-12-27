# Plan 3: Section Rendering & JSON Mapping (Phase 2)

## Goal
Render all CV content sections from JSON data, including Hero, Profiles, Education, Languages, Certifications, Skills, Experiences, Projects, Publications, and References sections with proper type_key filtering support.

## Scope
This plan covers:
- Task 2.1: Hero Section (Basics + Pictures)
- Task 2.2: Profiles/Social Links Section
- Task 2.3: Education Section with type_key Filtering
- Task 2.4: Languages Section
- Task 2.5: Certifications Section with type_key Filtering
- Task 2.6: Skills Section (Nested Structure) with type_key Filtering
- Task 2.7: Experiences Section with type_key Filtering
- Task 2.8: Projects Section with type_key Filtering and Deduplication
- Task 2.9: Publications Section with type_key Filtering
- Task 2.10: References Section (Always Visible)

---

## CRITICAL RULES (MUST FOLLOW)

### LOCKED FILES / IMMUTABILITY
- `ramin_de.json`, `ramin_fa.json`, `cv.json` are byte-identical locked inputs (at least through the end of "projects"; treat as fully read-only).
- **Absolutely no edits, no formatting changes, no sorting, no whitespace modifications** to these files.

### SELF-OVERSEER REQUIREMENT (NON-NEGOTIABLE)
- You must continuously self-audit and NOT stop until:
  1. The task's acceptance criteria are fully satisfied,
  2. The project can be run locally after changes with no errors,
  3. The fix is verified (not assumed) with evidence (logs/tests/screens).
- If you think something is "probably fine," you must verify it anyway.
- Do not declare "done" until you can run the project and confirm the expected behavior.

### DEBUG+RUN REQUIREMENT
- For any plan that changes code, the plan must require:
  - Run the project (dev AND build if relevant),
  - Confirm no runtime errors,
  - Confirm the specific success conditions by navigating relevant pages.

---

## Deliverables

### Task 2.1: Hero Section (Basics + Pictures)

**Acceptance Criteria**:
- [ ] Create `src/components/HeroSection.tsx`
- [ ] Render cover image from `Pictures` array (type_of: "cover") as full-width background
- [ ] Render profile photo from `Pictures` array (type_of: "profile") as circular overlay
- [ ] Display `fname` + `lname` as large heading
- [ ] Display `label` array as comma-separated subtitle
- [ ] Display `summary` paragraph
- [ ] Display email, phone, location (city, country)
- [ ] Handle missing fields gracefully (don't crash, skip or show placeholder)

**Verification Checks**:
- Visual inspection: cover image fills width, profile photo overlays
- Verify name renders from JSON `basics[0].fname` and `lname`
- Check labels: count matches `basics[0].label.length`
- Remove `Pictures` from JSON - section still renders without crash
- Remove `summary` - no error, summary area empty
- Verify email is a clickable `mailto:` link

### Task 2.2: Profiles/Social Links Section

**Acceptance Criteria**:
- [ ] Create `src/components/ProfilesSection.tsx`
- [ ] Map over `profiles` array from JSON
- [ ] Display each profile as icon + username (clickable link)
- [ ] Support: GitHub, LinkedIn, Google Scholar, ORCID (note: normalize "ORCHID" → "ORCID")
- [ ] Icons: use CSS-only icons or minimal SVG (no icon library)
- [ ] Links open in new tab (`target="_blank" rel="noopener noreferrer"`)

**Verification Checks**:
- Count rendered profile buttons matches `profiles.length` in JSON
- Click each link - opens correct URL in new tab
- Verify ORCID link (even if JSON says "ORCHID")
- Remove `profiles` from JSON - section not rendered or shows "No profiles"
- Check keyboard navigation: Tab to each link, Enter opens

### Task 2.3: Education Section with type_key Filtering

**Acceptance Criteria**:
- [ ] Create `src/components/EducationSection.tsx`
- [ ] Map over `education` array
- [ ] Display: institution, studyType, area, location, startDate-endDate, GPA
- [ ] Handle "present" or null endDate (show as "Present")
- [ ] Filter entries by selected focus: only show if focus value in `type_key` array
- [ ] Show all entries if focus is "Full CV"
- [ ] Animate entries on scroll (fade-in with stagger)

**Verification Checks**:
- Select focus "Full CV" - count rendered entries equals `education.length`
- Select focus "Programming" - only entries with "Programming" in `type_key` appear
- Verify startDate/endDate formatted correctly (handle ISO dates)
- Set endDate to "present" - displays as "Present", not raw string
- Scroll section into view - animation triggers
- Check `prefers-reduced-motion: reduce` - no animation

### Task 2.4: Languages Section

**Acceptance Criteria**:
- [ ] Create `src/components/LanguagesSection.tsx`
- [ ] Map over `languages` array
- [ ] Display language name and proficiency level (e.g., bars or text)
- [ ] Responsive grid layout

**Verification Checks**:
- Count entries matches `languages.length`
- Each language shows proficiency clearly
- Resize to mobile - grid adjusts

### Task 2.5: Certifications Section with type_key Filtering

**Acceptance Criteria**:
- [ ] Create `src/components/CertificationsSection.tsx`
- [ ] Map over `workshop_and_certifications` array
- [ ] Display title, issuer, date
- [ ] Handle invalid dates gracefully (e.g., "2020-9-31" should not crash - show raw or "Invalid Date")
- [ ] Filter by `type_key`
- [ ] Optional: render PDF URL as thumbnail if present

**Verification Checks**:
- Verify invalid date ("2020-9-31") does not crash app
- Check date displayed as fallback (raw string or "Invalid Date" message)
- Select focus filter - entries filter correctly
- If certification has PDF URL, thumbnail appears and is clickable

### Task 2.6: Skills Section (Nested Structure) with type_key Filtering

**Acceptance Criteria**:
- [ ] Create `src/components/SkillsSection.tsx`
- [ ] Iterate over top-level keys (e.g., "Programming & Scripting", "Soft Skills")
- [ ] For each section, iterate over categories (e.g., "Programming Languages", "Data Science")
- [ ] For each category, render items as badges/chips (use `short_name`)
- [ ] Filter items: only show if focus value in item's `type_key` array
- [ ] Visual grouping: section title, category subtitle, item list

**Verification Checks**:
- All sections and categories from JSON are rendered
- Count items in first category - matches JSON
- Select focus "Programming" - only items with "Programming" in `type_key` show
- Verify items display `short_name`, not `long_name`
- Visual check: clear hierarchy (section > category > items)

### Task 2.7: Experiences Section with type_key Filtering

**Acceptance Criteria**:
- [ ] Create `src/components/ExperiencesSection.tsx`
- [ ] Map over `experiences` array
- [ ] Display: role, institution, location, duration, primaryFocus, description
- [ ] `duration` is a string - display as-is (e.g., "2018-02-11 - Recent")
- [ ] Filter by `type_key`
- [ ] Bullet points for primaryFocus and description

**Verification Checks**:
- Verify `duration` displayed exactly as in JSON (string format)
- Filter by focus - only matching entries appear
- Check primaryFocus and description render as separate bullets

### Task 2.8: Projects Section with type_key Filtering and Deduplication

**Acceptance Criteria**:
- [ ] Create `src/components/ProjectsSection.tsx`
- [ ] Map over `projects` array
- [ ] Deduplicate by `title + url` combination (if duplicate found, show only once)
- [ ] Display: title, description, URL (link), technologies
- [ ] Filter by `type_key`
- [ ] Optional: detect image URLs in project data and render as thumbnails

**Verification Checks**:
- Check JSON for duplicate project (e.g., "Cosmetic Shop Marketplace") - verify only one rendered
- Deduplication logic: hash or set of `${title}|${url}` keys
- Click project URL - opens in new tab
- Filter by focus - correct projects appear

### Task 2.9: Publications Section with type_key Filtering

**Acceptance Criteria**:
- [ ] Create `src/components/PublicationsSection.tsx`
- [ ] Map over `publications` array
- [ ] Display: title, type, status, date, authors, journal/conference, ISBN, DOI, URL
- [ ] Format as citation (e.g., "Author (Year). Title. Journal.")
- [ ] Filter by `type_key`
- [ ] URL links open in new tab

**Verification Checks**:
- Verify all fields from JSON rendered
- Check status "Published" vs "In Review" displays
- URL clickable and opens correct link
- Filter by "Academic" focus - only academic publications show

### Task 2.10: References Section (Always Visible)

**Acceptance Criteria**:
- [ ] Create `src/components/ReferencesSection.tsx`
- [ ] Map over `references` array
- [ ] Display: name, email(s), phone(s), position/affiliation
- [ ] `email` and `phone` are arrays - display all
- [ ] Optional `URL` field: if PDF URL, show as "View Reference Letter" link/thumbnail
- [ ] Always visible (no privacy gating)
- [ ] Filter by `type_key` (only if focus filter active)

**Verification Checks**:
- Verify references always displayed (not hidden)
- Check multiple emails displayed correctly
- If reference has PDF URL, link appears and opens PDF
- Filter by focus - only matching references show

---

## Success Criteria

- [ ] All 10 sections render correctly from JSON data
- [ ] All sections with type_key support filtering correctly
- [ ] "Full CV" focus shows all entries
- [ ] Deduplication working for projects
- [ ] Invalid/missing data handled gracefully (no crashes)
- [ ] All links open in new tabs
- [ ] Keyboard navigation working
- [ ] Scroll animations respecting reduced-motion preference

---

## Dependencies
- **Requires**: Plan 1 (Project Setup & Foundation), Plan 2 (Core Layout & Theme System)

## Estimated Effort
- 5-7 days
