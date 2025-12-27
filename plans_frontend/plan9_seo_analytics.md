# Plan 10: Advanced Features - SEO, Analytics, Skills Visualization (Phase 7, Tasks 7.1-7.5)

## Goal
Implement advanced professional features for discoverability and engagement including SEO optimization, analytics tracking, interactive skills visualizations, testimonials section, and project case studies.

## Scope
This plan covers:
- Task 7.1: SEO Optimization & Meta Tags
- Task 7.2: Analytics Integration
- Task 7.3: Skills Visualization Dashboard
- Task 7.4: Testimonials & Recommendations Carousel
- Task 7.5: Project Case Study Expansion

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

### Task 7.1: SEO Optimization & Meta Tags

**Acceptance Criteria**:
- [ ] Create `src/utils/seo.ts` for SEO utilities
- [ ] Implement dynamic meta tags:
  - `<title>` (includes name + current page/section)
  - `<meta name="description">` (from summary)
  - `<meta name="keywords">` (from skills + job titles)
  - `<meta name="author">` (from name)
  - Canonical URL
- [ ] Open Graph tags for social sharing:
  - `og:title`, `og:description`, `og:image`, `og:url`, `og:type`
- [ ] Twitter Card meta tags
- [ ] JSON-LD structured data (Person schema)
- [ ] Sitemap.xml generation
- [ ] Robots.txt configuration
- [ ] Language-specific meta tags (hreflang)

**Verification Checks**:
- Use social media debuggers (Facebook, Twitter) - preview shows correctly
- View page source - all meta tags present
- Google Structured Data Testing Tool - valid JSON-LD
- Lighthouse SEO score: 100
- Sitemap.xml accessible and valid

### Task 7.2: Analytics Integration

**Acceptance Criteria**:
- [ ] Create `src/utils/analytics.ts` for analytics
- [ ] Support Google Analytics 4 (GA4)
- [ ] Alternative: privacy-focused analytics (Plausible, Fathom, Umami)
- [ ] Track events:
  - Page views
  - Section scrolls (which sections viewed)
  - Theme changes
  - Language changes
  - Filter changes
  - PDF downloads
  - External link clicks
  - Contact form submissions
- [ ] User consent before tracking (cookie banner)
- [ ] Respect Do Not Track header
- [ ] Easy opt-out mechanism
- [ ] Development mode: log events to console instead of sending

**Verification Checks**:
- Check network tab - analytics calls made only after consent
- Event tracking: change theme, check analytics console
- Do Not Track enabled - no analytics
- Opt-out works - analytics disabled
- Dev mode - events logged to console

### Task 7.3: Skills Visualization Dashboard

**Acceptance Criteria**:
- [ ] Create interactive skills visualization
- [ ] Radar/spider chart for skill categories
- [ ] Bar charts for individual skill proficiency
- [ ] Bubble chart showing skill relationships
- [ ] Timeline showing skill acquisition over years
- [ ] Interactive: hover for details, click to filter
- [ ] Animate charts on scroll into view
- [ ] Toggle between visualization types
- [ ] Respect `prefers-reduced-motion`

**Verification Checks**:
- Skills dashboard visible and interactive
- Hover over chart element - tooltip with details
- Click skill - filters related content
- Animation smooth on scroll
- All chart types work correctly
- Test `prefers-reduced-motion` - static charts

### Task 7.4: Testimonials & Recommendations Carousel

**Acceptance Criteria**:
- [ ] Add `testimonials` to JSON schema
- [ ] Create `src/components/TestimonialsSection.tsx`
- [ ] Carousel with auto-rotation (pause on hover)
- [ ] Show: quote, author name, title, company, photo, date
- [ ] Star rating display (if applicable)
- [ ] Linked to LinkedIn recommendations
- [ ] Swipe/arrow navigation
- [ ] Keyboard accessible
- [ ] Quote animation effect (fade in with quotation marks)

**Verification Checks**:
- Testimonials display in carousel
- Auto-rotation works (5-7 second intervals)
- Pause on hover
- Arrow navigation works
- Swipe on mobile works
- Quotes display with proper formatting

### Task 7.5: Project Case Study Expansion

**Acceptance Criteria**:
- [ ] Extend projects JSON schema with case study fields:
  - `problem` - Problem statement
  - `solution` - Solution description
  - `process` - Process/methodology
  - `results` - Outcomes and metrics
  - `technologies` - Tech stack details
  - `images` - Gallery of screenshots
  - `links` - GitHub, live demo, etc.
- [ ] Create `src/components/ProjectCaseStudy.tsx`
- [ ] Expandable project cards with full case study view
- [ ] Collapsed state: title, summary, tech tags, thumbnail
- [ ] Expanded state: full case study with all sections
- [ ] Image gallery within expanded view
- [ ] Metrics displayed as stat cards
- [ ] Deep linking: URL can open specific project expanded

**Verification Checks**:
- Click project card - expands smoothly
- Expanded view shows all case study sections
- Image gallery navigable
- Metrics cards display correctly
- GitHub and demo links work
- Deep link URL opens specific project
- ESC or click outside - collapses project

---

## Success Criteria

- [ ] SEO meta tags and structured data complete
- [ ] Lighthouse SEO score: 100
- [ ] Analytics tracking with user consent
- [ ] Interactive skills visualization dashboard
- [ ] Testimonials carousel functioning
- [ ] Project case studies with expandable details
- [ ] All features keyboard accessible

---

## Dependencies
- **Requires**: Plan 1-9 (core MVP and Enhanced UI complete)

## Estimated Effort
- 10-12 days
