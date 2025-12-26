# UI/UX Master Plan for JSON-Driven, Multi-Language CV/Portfolio Website

**Vision**: Build a premium, production-ready single-page CV/portfolio website that renders entirely from JSON data, supports multiple languages (EN/DE/FA with RTL), offers multiple visual themes, includes comprehensive filtering, rich media handling, and future-ready backend integration points.

**Target Platform**: React + TypeScript (Spark-like constraints: minimal libraries, maximum polish)

**Data Source**: JSON files following the schema established in `data/cvs/ramin.json`

---

## IMPLEMENTATION TASKS (Step-by-Step Issues)

### PHASE 0: Project Setup & Foundation

#### Task 0.1: Initialize React + TypeScript Project
**Description**: Set up the base React + TypeScript project with minimal dependencies.

**Acceptance Criteria**:
- [ ] Create React app with TypeScript template
- [ ] Configure `tsconfig.json` with strict mode
- [ ] Set up folder structure: `/src/components`, `/src/types`, `/src/data`, `/src/styles`, `/src/utils`
- [ ] Add only essential dependencies: React 18+, TypeScript 5+
- [ ] Configure build system (Vite or Create React App)
- [ ] Create `.gitignore` excluding `node_modules`, build artifacts

**Oversight Checks**:
- ✓ Verify `tsconfig.json` has `"strict": true`
- ✓ Run `npm run build` succeeds without errors
- ✓ Verify no unnecessary dependencies in `package.json` (max 10 total dependencies)
- ✓ Check folder structure matches specification

**Dependencies**: None

---

#### Task 0.2: Create TypeScript Interfaces for JSON Schema
**Description**: Define complete TypeScript types matching the ramin.json structure.

**Acceptance Criteria**:
- [ ] Create `src/types/cv.types.ts` with all interfaces
- [ ] Define `Basics`, `Profile`, `Education`, `Experience`, `Skill`, `Project`, `Publication`, `Reference`, `Language`, `Certification` interfaces
- [ ] Include `type_key` as `string[]` in all relevant types
- [ ] Define `Pictures` type with `type_of` and `URL`
- [ ] Support nested skills structure (category → subcategory → items)
- [ ] Make all fields optional with `?` for robustness

**Oversight Checks**:
- ✓ Load `ramin.json` and assign to typed variable - no TypeScript errors
- ✓ All top-level JSON keys have corresponding interfaces
- ✓ `type_key` present in Education, Skills, Experience, Projects, Publications, References, Certifications
- ✓ Run `tsc --noEmit` with no type errors

**Dependencies**: Task 0.1

---

#### Task 0.3: Create Multi-Language JSON Files
**Description**: Create three JSON files (EN, DE, FA) with identical structure.

**Acceptance Criteria**:
- [ ] Copy `ramin.json` to `src/data/cv-en.json`
- [ ] Create `src/data/cv-de.json` with German translations (all text fields)
- [ ] Create `src/data/cv-fa.json` with Farsi translations (all text fields)
- [ ] Ensure identical structure across all three files (same keys, same nesting)
- [ ] Verify all URLs remain unchanged across files

**Oversight Checks**:
- ✓ Parse all three JSON files successfully
- ✓ Compare object key sets - must be identical
- ✓ Count array lengths for each section - must match across files
- ✓ Verify `type_key` arrays are identical across language files

**Dependencies**: Task 0.2

---

### PHASE 1: Core Layout & Theme System

#### Task 1.1: Implement Theme System with CSS Custom Properties
**Description**: Create a theme system with 6 presets using CSS variables.

**Acceptance Criteria**:
- [ ] Create `src/styles/themes.css` with CSS custom properties
- [ ] Define 6 theme presets: Normal, Academic, Apple-like, Dark, Bright, Futuristic
- [ ] Each theme defines: `--primary`, `--secondary`, `--background`, `--surface`, `--text-primary`, `--text-secondary`, `--accent`, `--border`, `--shadow`
- [ ] Theme applied via `data-theme` attribute on root element
- [ ] Create `src/utils/themeManager.ts` to switch themes
- [ ] Save theme preference to localStorage
- [ ] Academic theme uses serif fonts, others use sans-serif

**Oversight Checks**:
- ✓ Toggle through all 6 themes - visual changes confirm
- ✓ Check DevTools: root element has `data-theme` attribute changing
- ✓ Refresh page - theme persists from localStorage
- ✓ Verify Academic theme uses `font-family: Georgia, serif`
- ✓ Dark theme has `--background` darker than `--text-primary` (contrast check)

**Dependencies**: Task 0.1

---

#### Task 1.2: Implement RTL Support for Farsi
**Description**: Add RTL layout support activated when FA language is selected.

**Acceptance Criteria**:
- [ ] Detect language and set `dir="rtl"` on HTML root for FA
- [ ] Create `src/styles/rtl.css` with RTL-specific rules
- [ ] Flip margins, paddings, text-align for RTL
- [ ] Mirror icons/arrows that indicate direction
- [ ] Test all sections render correctly in RTL
- [ ] Logical properties: use `inline-start`, `inline-end` instead of left/right where possible

**Oversight Checks**:
- ✓ Switch to FA language - inspect HTML root has `dir="rtl"` and `lang="fa"`
- ✓ Header navigation aligns right
- ✓ Profile photo appears on right side in RTL
- ✓ Text alignment is right for paragraphs
- ✓ Check skills section: categories flow right-to-left
- ✓ Verify no layout breakage (overlaps, cutoffs)

**Dependencies**: Task 0.3, Task 1.1

---

#### Task 1.3: Build Sticky Header with Navigation
**Description**: Create responsive sticky header with language switcher, theme switcher, focus filter, and navigation.

**Acceptance Criteria**:
- [ ] Create `src/components/Header.tsx`
- [ ] Logo/Name on left (clickable, scrolls to top)
- [ ] Navigation links to sections (smooth scroll on click)
- [ ] Language dropdown (EN/DE/FA) - switches JSON data source
- [ ] Theme dropdown (6 themes) - switches theme
- [ ] Focus filter dropdown (initially: Full CV, Programming, Biotechnology, Academic, etc.)
- [ ] Header sticks to top on scroll, adds shadow
- [ ] Hamburger menu on mobile (< 640px)
- [ ] All controls keyboard accessible (Tab, Enter, Esc)

**Oversight Checks**:
- ✓ Scroll page - header stays visible at top
- ✓ Click nav link - smooth scroll to section occurs
- ✓ Change language - verify content changes (check section headings)
- ✓ Change theme - verify colors change immediately
- ✓ Resize to mobile - hamburger menu appears
- ✓ Tab through header - all interactive elements receive focus indicators
- ✓ Press Esc on open dropdown - dropdown closes

**Dependencies**: Task 1.1, Task 1.2, Task 0.3

---

#### Task 1.4: Build Footer Component
**Description**: Create real footer with copyright, PDF export, and social links.

**Acceptance Criteria**:
- [ ] Create `src/components/Footer.tsx`
- [ ] Display copyright with current year
- [ ] PDF Export button (onClick triggers print dialog for now)
- [ ] Render social links from `profiles` JSON data
- [ ] Responsive layout (stack on mobile)
- [ ] Consistent theme styling

**Oversight Checks**:
- ✓ Footer appears at bottom of page
- ✓ Click PDF Export - browser print dialog opens
- ✓ Social links are clickable and open in new tab
- ✓ Verify links match `profiles` array URLs from JSON
- ✓ Resize to mobile - footer content stacks vertically

**Dependencies**: Task 1.1

---

### PHASE 2: Section Rendering & JSON Mapping

#### Task 2.1: Hero Section (Basics + Pictures)
**Description**: Render hero section with profile photo, cover image, name, labels, summary, contact info.

**Acceptance Criteria**:
- [ ] Create `src/components/HeroSection.tsx`
- [ ] Render cover image from `Pictures` array (type_of: "cover") as full-width background
- [ ] Render profile photo from `Pictures` array (type_of: "profile") as circular overlay
- [ ] Display `fname` + `lname` as large heading
- [ ] Display `label` array as comma-separated subtitle
- [ ] Display `summary` paragraph
- [ ] Display email, phone, location (city, country)
- [ ] Handle missing fields gracefully (don't crash, skip or show placeholder)

**Oversight Checks**:
- ✓ Visual inspection: cover image fills width, profile photo overlays
- ✓ Verify name renders from JSON `basics[0].fname` and `lname`
- ✓ Check labels: count matches `basics[0].label.length`
- ✓ Remove `Pictures` from JSON - section still renders without crash
- ✓ Remove `summary` - no error, summary area empty
- ✓ Verify email is a clickable `mailto:` link

**Dependencies**: Task 0.2, Task 0.3, Task 1.1

---

#### Task 2.2: Profiles/Social Links Section
**Description**: Render social media profiles as icon buttons.

**Acceptance Criteria**:
- [ ] Create `src/components/ProfilesSection.tsx`
- [ ] Map over `profiles` array from JSON
- [ ] Display each profile as icon + username (clickable link)
- [ ] Support: GitHub, LinkedIn, Google Scholar, ORCID (note: normalize "ORCHID" → "ORCID")
- [ ] Icons: use CSS-only icons or minimal SVG (no icon library)
- [ ] Links open in new tab (`target="_blank" rel="noopener noreferrer"`)

**Oversight Checks**:
- ✓ Count rendered profile buttons matches `profiles.length` in JSON
- ✓ Click each link - opens correct URL in new tab
- ✓ Verify ORCID link (even if JSON says "ORCHID")
- ✓ Remove `profiles` from JSON - section not rendered or shows "No profiles"
- ✓ Check keyboard navigation: Tab to each link, Enter opens

**Dependencies**: Task 0.2, Task 0.3, Task 1.1

---

#### Task 2.3: Education Section with type_key Filtering
**Description**: Render education entries as timeline cards, support filtering by type_key.

**Acceptance Criteria**:
- [ ] Create `src/components/EducationSection.tsx`
- [ ] Map over `education` array
- [ ] Display: institution, studyType, area, location, startDate-endDate, GPA
- [ ] Handle "present" or null endDate (show as "Present")
- [ ] Filter entries by selected focus: only show if focus value in `type_key` array
- [ ] Show all entries if focus is "Full CV"
- [ ] Animate entries on scroll (fade-in with stagger)

**Oversight Checks**:
- ✓ Select focus "Full CV" - count rendered entries equals `education.length`
- ✓ Select focus "Programming" - only entries with "Programming" in `type_key` appear
- ✓ Verify startDate/endDate formatted correctly (handle ISO dates)
- ✓ Set endDate to "present" - displays as "Present", not raw string
- ✓ Scroll section into view - animation triggers
- ✓ Check `prefers-reduced-motion: reduce` - no animation

**Dependencies**: Task 2.1, Task 1.3 (focus filter)

---

#### Task 2.4: Languages Section
**Description**: Render language proficiency list.

**Acceptance Criteria**:
- [ ] Create `src/components/LanguagesSection.tsx`
- [ ] Map over `languages` array
- [ ] Display language name and proficiency level (e.g., bars or text)
- [ ] Responsive grid layout

**Oversight Checks**:
- ✓ Count entries matches `languages.length`
- ✓ Each language shows proficiency clearly
- ✓ Resize to mobile - grid adjusts

**Dependencies**: Task 0.2, Task 1.1

---

#### Task 2.5: Certifications Section with type_key Filtering
**Description**: Render workshop_and_certifications as cards with date robustness.

**Acceptance Criteria**:
- [ ] Create `src/components/CertificationsSection.tsx`
- [ ] Map over `workshop_and_certifications` array
- [ ] Display title, issuer, date
- [ ] Handle invalid dates gracefully (e.g., "2020-9-31" should not crash - show raw or "Invalid Date")
- [ ] Filter by `type_key`
- [ ] Optional: render PDF URL as thumbnail if present

**Oversight Checks**:
- ✓ Verify invalid date ("2020-9-31") does not crash app
- ✓ Check date displayed as fallback (raw string or "Invalid Date" message)
- ✓ Select focus filter - entries filter correctly
- ✓ If certification has PDF URL, thumbnail appears and is clickable

**Dependencies**: Task 2.3 (filtering pattern), Task 0.2

---

#### Task 2.6: Skills Section (Nested Structure) with type_key Filtering
**Description**: Render nested skills structure (sections → categories → items).

**Acceptance Criteria**:
- [ ] Create `src/components/SkillsSection.tsx`
- [ ] Iterate over top-level keys (e.g., "Programming & Scripting", "Soft Skills")
- [ ] For each section, iterate over categories (e.g., "Programming Languages", "Data Science")
- [ ] For each category, render items as badges/chips (use `short_name`)
- [ ] Filter items: only show if focus value in item's `type_key` array
- [ ] Visual grouping: section title, category subtitle, item list

**Oversight Checks**:
- ✓ All sections and categories from JSON are rendered
- ✓ Count items in first category - matches JSON
- ✓ Select focus "Programming" - only items with "Programming" in `type_key` show
- ✓ Verify items display `short_name`, not `long_name`
- ✓ Visual check: clear hierarchy (section > category > items)

**Dependencies**: Task 2.3 (filtering), Task 0.2

---

#### Task 2.7: Experiences Section with type_key Filtering
**Description**: Render work experiences as timeline entries.

**Acceptance Criteria**:
- [ ] Create `src/components/ExperiencesSection.tsx`
- [ ] Map over `experiences` array
- [ ] Display: role, institution, location, duration, primaryFocus, description
- [ ] `duration` is a string - display as-is (e.g., "2018-02-11 - Recent")
- [ ] Filter by `type_key`
- [ ] Bullet points for primaryFocus and description

**Oversight Checks**:
- ✓ Verify `duration` displayed exactly as in JSON (string format)
- ✓ Filter by focus - only matching entries appear
- ✓ Check primaryFocus and description render as separate bullets

**Dependencies**: Task 2.3 (filtering), Task 0.2

---

#### Task 2.8: Projects Section with type_key Filtering and Deduplication
**Description**: Render projects with duplicate handling.

**Acceptance Criteria**:
- [ ] Create `src/components/ProjectsSection.tsx`
- [ ] Map over `projects` array
- [ ] Deduplicate by `title + url` combination (if duplicate found, show only once)
- [ ] Display: title, description, URL (link), technologies
- [ ] Filter by `type_key`
- [ ] Optional: detect image URLs in project data and render as thumbnails

**Oversight Checks**:
- ✓ Check JSON for duplicate project (e.g., "Cosmetic Shop Marketplace") - verify only one rendered
- ✓ Deduplication logic: hash or set of `${title}|${url}` keys
- ✓ Click project URL - opens in new tab
- ✓ Filter by focus - correct projects appear

**Dependencies**: Task 2.3 (filtering), Task 0.2

---

#### Task 2.9: Publications Section with type_key Filtering
**Description**: Render publications as bibliography entries.

**Acceptance Criteria**:
- [ ] Create `src/components/PublicationsSection.tsx`
- [ ] Map over `publications` array
- [ ] Display: title, type, status, date, authors, journal/conference, ISBN, DOI, URL
- [ ] Format as citation (e.g., "Author (Year). Title. Journal.")
- [ ] Filter by `type_key`
- [ ] URL links open in new tab

**Oversight Checks**:
- ✓ Verify all fields from JSON rendered
- ✓ Check status "Published" vs "In Review" displays
- ✓ URL clickable and opens correct link
- ✓ Filter by "Academic" focus - only academic publications show

**Dependencies**: Task 2.3 (filtering), Task 0.2

---

#### Task 2.10: References Section (Always Visible)
**Description**: Render references with optional phone and PDF URL.

**Acceptance Criteria**:
- [ ] Create `src/components/ReferencesSection.tsx`
- [ ] Map over `references` array
- [ ] Display: name, email(s), phone(s), position/affiliation
- [ ] `email` and `phone` are arrays - display all
- [ ] Optional `URL` field: if PDF URL, show as "View Reference Letter" link/thumbnail
- [ ] Always visible (no privacy gating)
- [ ] Filter by `type_key` (only if focus filter active)

**Oversight Checks**:
- ✓ Verify references always displayed (not hidden)
- ✓ Check multiple emails displayed correctly
- ✓ If reference has PDF URL, link appears and opens PDF
- ✓ Filter by focus - only matching references show

**Dependencies**: Task 2.3 (filtering), Task 0.2

---

### PHASE 3: Advanced Features

#### Task 3.1: Unified Media Thumbnail + Modal System
**Description**: Detect media URLs (images, PDFs) across all sections, render thumbnails, open full-view modal on click.

**Acceptance Criteria**:
- [ ] Create `src/utils/mediaDetector.ts` to identify image/PDF URLs by extension
- [ ] Create `src/components/MediaThumbnail.tsx` component
- [ ] Thumbnail: small preview (image: actual thumbnail, PDF: icon + filename)
- [ ] Create `src/components/MediaModal.tsx` for full-view
- [ ] Modal: overlay, close button, ESC key closes, focus trap, click outside closes
- [ ] Display images directly, PDFs in iframe or link to open
- [ ] Keyboard navigation: Tab through close button, arrow keys for gallery (if multiple)

**Oversight Checks**:
- ✓ Identify all media URLs in JSON (Pictures, publication URLs, reference URLs, project images)
- ✓ Click thumbnail - modal opens with full content
- ✓ Press ESC - modal closes
- ✓ Click outside modal content - modal closes
- ✓ Tab in modal - focus stays within modal (focus trap)
- ✓ Check PDF URL opens in iframe or new tab

**Dependencies**: Task 2.1-2.10 (all sections)

---

#### Task 3.2: Global Focus Filter Implementation
**Description**: Wire focus filter dropdown to all sections with type_key.

**Acceptance Criteria**:
- [ ] Create `src/context/FilterContext.tsx` (React Context)
- [ ] Store selected focus value (string)
- [ ] Provide function to change focus
- [ ] All sections (Education, Skills, Projects, etc.) subscribe to context
- [ ] Filter logic: if focus === "Full CV", show all; else show only entries where `type_key.includes(focus)`
- [ ] Derive filter options dynamically from JSON data (union of all type_key values)
- [ ] Persist selected focus to localStorage

**Oversight Checks**:
- ✓ Change focus in header dropdown - verify all sections update simultaneously
- ✓ Count visible entries in each section - matches filter logic
- ✓ Select "Full CV" - all entries across all sections appear
- ✓ Select "Programming" - only relevant entries appear
- ✓ Refresh page - focus filter persists from localStorage
- ✓ Check DevTools React context value changes on filter switch

**Dependencies**: Task 1.3 (header filter dropdown), Task 2.3-2.10 (filtered sections)

---

#### Task 3.3: Smooth Scroll & Scroll Animations
**Description**: Implement smooth scrolling to sections and scroll-triggered animations.

**Acceptance Criteria**:
- [ ] Navigation links trigger smooth scroll via `scrollIntoView({ behavior: 'smooth' })`
- [ ] Detect when sections enter viewport using Intersection Observer
- [ ] Fade-in animation on sections as they enter viewport
- [ ] Stagger animation for lists (education, projects, etc.)
- [ ] Disable animations if `prefers-reduced-motion: reduce`

**Oversight Checks**:
- ✓ Click nav link - page scrolls smoothly to section
- ✓ Scroll manually - sections fade in as they enter viewport
- ✓ Check DevTools: `prefers-reduced-motion: reduce` - animations disabled
- ✓ Verify no layout shift during animation

**Dependencies**: Task 1.3, Task 2.1-2.10

---

#### Task 3.4: PDF Generation (Print-Based)
**Description**: Implement browser print/save-as-PDF functionality with print stylesheet.

**Acceptance Criteria**:
- [ ] Create `src/styles/print.css` media query stylesheet
- [ ] Hide header, footer, theme switcher, language switcher in print mode
- [ ] Optimize layout for A4 page
- [ ] Ensure all sections visible (no pagination breaks in awkward places)
- [ ] PDF Export button in footer triggers `window.print()`
- [ ] Add comment in code for future backend API seam (e.g., LaTeX generator)

**Oversight Checks**:
- ✓ Click PDF Export - print preview opens
- ✓ In print preview, header/footer not visible
- ✓ In print preview, content is well-formatted, readable
- ✓ Save as PDF from print dialog - PDF is usable
- ✓ Verify comment in code: `// TODO: Replace with backend API call for LaTeX PDF generation`

**Dependencies**: Task 1.4 (footer), Task 2.1-2.10

---

#### Task 3.5: Contact Form Placeholder
**Description**: Create UI for contact form (no backend yet).

**Acceptance Criteria**:
- [ ] Create `src/components/ContactForm.tsx`
- [ ] Fields: Name, Email, Subject, Message
- [ ] Submit button (onClick shows alert: "Backend not implemented yet")
- [ ] Form validation (client-side: required fields, email format)
- [ ] Accessible form labels and error messages
- [ ] Add comment for future backend integration point

**Oversight Checks**:
- ✓ Fill form and submit - alert appears with message about backend
- ✓ Submit with empty required field - validation error shows
- ✓ Enter invalid email - validation error shows
- ✓ Tab through form - all fields keyboard accessible
- ✓ Verify comment: `// TODO: POST to /api/contact endpoint`

**Dependencies**: Task 1.1

---

#### Task 3.6: Book a Call Placeholder
**Description**: Create UI for booking a call (no backend yet).

**Acceptance Criteria**:
- [ ] Create `src/components/BookingWidget.tsx`
- [ ] Display placeholder calendar/scheduling UI
- [ ] Button: "Book a Call" (onClick shows alert: "Booking system not implemented yet")
- [ ] Add comment for future integration (e.g., Calendly API)

**Oversight Checks**:
- ✓ Click "Book a Call" - alert appears
- ✓ Verify comment: `// TODO: Integrate Calendly or custom booking backend`

**Dependencies**: Task 1.1

---

### PHASE 4: Robustness & Polish

#### Task 4.1: Handle Missing/Null/Invalid Data
**Description**: Ensure app doesn't crash with incomplete or malformed JSON.

**Acceptance Criteria**:
- [ ] All components check for null/undefined before rendering
- [ ] Use optional chaining (`data?.field`) and nullish coalescing (`?? 'default'`)
- [ ] Invalid dates display as raw string or "Invalid Date" message
- [ ] Missing images fallback to placeholder or skip rendering
- [ ] Empty arrays don't render section headings (or show "No data available")

**Oversight Checks**:
- ✓ Remove `education` key from JSON - section doesn't crash, shows nothing or "No education data"
- ✓ Set a date to invalid value (e.g., "2020-99-99") - no crash, fallback displayed
- ✓ Remove `Pictures` from basics - hero section renders without photos
- ✓ Set `type_key` to `null` on one entry - entry still renders, just not filtered

**Dependencies**: Task 2.1-2.10

---

#### Task 4.2: Responsive Design Verification
**Description**: Test and refine responsive behavior across all breakpoints.

**Acceptance Criteria**:
- [ ] Test on mobile (< 640px), tablet (640-1024px), desktop (> 1024px)
- [ ] Header: hamburger menu on mobile, full nav on desktop
- [ ] Hero: stack content vertically on mobile
- [ ] Skills: grid adjusts from 3 columns to 1 column
- [ ] All sections readable and usable on small screens
- [ ] Touch targets minimum 44x44px for mobile

**Oversight Checks**:
- ✓ Use DevTools device emulation: iPhone SE, iPad, Desktop
- ✓ Hamburger menu appears on mobile, works correctly
- ✓ No horizontal scroll on any screen size
- ✓ Text remains readable (min 14px on mobile)
- ✓ Verify touch targets with DevTools touch simulator

**Dependencies**: Task 1.3, Task 2.1-2.10

---

#### Task 4.3: Accessibility Audit (WCAG 2.1 AA)
**Description**: Ensure site meets accessibility standards.

**Acceptance Criteria**:
- [ ] All interactive elements keyboard accessible
- [ ] Focus indicators visible on all focusable elements
- [ ] Semantic HTML (nav, main, section, article, footer)
- [ ] Images have alt text (from JSON or fallback)
- [ ] Color contrast ratio ≥ 4.5:1 for normal text, ≥ 3:1 for large text
- [ ] ARIA labels where needed (dropdowns, modals)
- [ ] Screen reader testing (basic): page structure navigable

**Oversight Checks**:
- ✓ Tab through entire page - no keyboard traps, all elements reachable
- ✓ Run axe DevTools or Lighthouse accessibility audit - no critical issues
- ✓ Check contrast ratios with browser DevTools or Contrast Checker tool
- ✓ Verify modal has `role="dialog"` and `aria-modal="true"`
- ✓ Test with VoiceOver (Mac) or NVDA (Windows) - page makes sense

**Dependencies**: All previous tasks

---

#### Task 4.4: Performance Optimization
**Description**: Optimize load time and runtime performance.

**Acceptance Criteria**:
- [ ] Lazy load images (use `loading="lazy"` or Intersection Observer)
- [ ] Code splitting for components (React.lazy)
- [ ] Minimize bundle size: check with `npm run build` and analyze
- [ ] Optimize images: suggest compression or responsive images
- [ ] Measure Lighthouse performance score > 90

**Oversight Checks**:
- ✓ Run `npm run build` - check bundle size (< 500KB initial load target)
- ✓ Run Lighthouse in DevTools - Performance score > 90
- ✓ Check Network tab: images load progressively
- ✓ Verify code-splitting: lazy-loaded components show separate chunks

**Dependencies**: All previous tasks

---

#### Task 4.5: Browser Compatibility Testing
**Description**: Test on major browsers and ensure polyfills if needed.

**Acceptance Criteria**:
- [ ] Test on Chrome, Firefox, Safari, Edge (latest versions)
- [ ] Check for CSS compatibility (Grid, Flexbox, Custom Properties)
- [ ] Add autoprefixer if needed
- [ ] Fallbacks for unsupported features

**Oversight Checks**:
- ✓ Open site in Chrome, Firefox, Safari, Edge - all features work
- ✓ Check for console errors in each browser
- ✓ Verify CSS custom properties work (themes change)
- ✓ Test RTL in all browsers

**Dependencies**: All previous tasks

---

### PHASE 5: Quality Assurance & Documentation

#### Task 5.1: Create Comprehensive README
**Description**: Document the project setup, architecture, and usage.

**Acceptance Criteria**:
- [ ] Create `README.md` in project root
- [ ] Sections: Overview, Features, Tech Stack, Getting Started, Project Structure, JSON Schema, Customization Guide, Deployment
- [ ] Include screenshots or GIFs of key features
- [ ] Explain how to add new languages, themes, sections
- [ ] List future enhancements (backend API, analytics, etc.)

**Oversight Checks**:
- ✓ Follow README instructions as new user - can set up project successfully
- ✓ All features listed in README are implemented
- ✓ JSON schema documentation matches actual interfaces

**Dependencies**: All previous tasks

---

#### Task 5.2: Create JSON Schema Documentation
**Description**: Document the expected JSON structure for CVs.

**Acceptance Criteria**:
- [ ] Create `SCHEMA.md` or section in README
- [ ] Document all top-level keys: `basics`, `profiles`, `education`, etc.
- [ ] Explain `type_key` usage and filtering
- [ ] Provide example snippets for each section
- [ ] Explain Pictures structure and media URL handling

**Oversight Checks**:
- ✓ Schema documentation matches TypeScript interfaces
- ✓ Examples valid JSON that passes TypeScript type check
- ✓ Explanation of `type_key` clear and accurate

**Dependencies**: Task 0.2, Task 5.1

---

#### Task 5.3: End-to-End Testing Checklist
**Description**: Manual QA checklist covering all features.

**Acceptance Criteria**:
- [ ] Create `QA_CHECKLIST.md`
- [ ] Test cases for each feature: language switching, theme switching, filtering, modal interactions, form submissions, PDF export
- [ ] Test scenarios: mobile, desktop, keyboard-only, screen reader
- [ ] Edge cases: empty data, invalid dates, missing images, duplicate entries

**Oversight Checks**:
- ✓ Run through entire QA checklist - all items pass
- ✓ Document any issues found and fix before completion

**Dependencies**: All previous tasks

---

#### Task 5.4: Code Review & Refactoring
**Description**: Review codebase for quality, consistency, and maintainability.

**Acceptance Criteria**:
- [ ] Consistent naming conventions (camelCase for variables, PascalCase for components)
- [ ] Remove console.logs and debug code
- [ ] Add comments for complex logic
- [ ] Extract magic numbers to constants
- [ ] No TypeScript `any` types
- [ ] Consistent component structure (props, hooks, render)

**Oversight Checks**:
- ✓ Run ESLint - no errors or warnings
- ✓ Run `tsc --noEmit` - no type errors
- ✓ Search codebase for `console.log` - none found (or only intentional)
- ✓ Search for `any` type - none found (or justified with comment)

**Dependencies**: All previous tasks

---

#### Task 5.5: Deployment Preparation
**Description**: Prepare for production deployment.

**Acceptance Criteria**:
- [ ] Create production build (`npm run build`)
- [ ] Test production build locally (serve from `build/` or `dist/`)
- [ ] Configure environment variables if needed
- [ ] Add deployment instructions to README (Vercel, Netlify, GitHub Pages, etc.)
- [ ] Set up robots.txt and sitemap.xml if SEO desired

**Oversight Checks**:
- ✓ Production build succeeds without errors
- ✓ Serve production build - all features work identically to dev
- ✓ Check bundle sizes - within acceptable range
- ✓ Verify deployment instructions by deploying to staging environment

**Dependencies**: Task 5.1, Task 4.4

---

## CROSS-CUTTING OVERSIGHT CRITERIA

### For Every Component Created:
- ✓ TypeScript: No `any` types, all props typed
- ✓ Accessibility: Keyboard navigable, semantic HTML, ARIA where needed
- ✓ Responsive: Works on mobile, tablet, desktop
- ✓ Theme-aware: Uses CSS custom properties, adapts to theme changes
- ✓ RTL-compatible: Works correctly when `dir="rtl"`
- ✓ Null-safe: Handles missing/undefined data gracefully
- ✓ Performance: No unnecessary re-renders, memoization where appropriate

### For Every Section with type_key:
- ✓ Filtering logic: Correctly filters by selected focus
- ✓ "Full CV" behavior: Shows all entries when focus is "Full CV"
- ✓ Filter consistency: Same logic across all filtered sections
- ✓ Empty state: Handles no matching entries gracefully

### For Every Media Element:
- ✓ Thumbnail rendering: Small, performant preview
- ✓ Modal integration: Clicks open full-view modal
- ✓ Keyboard support: ESC closes, Tab navigates within modal
- ✓ Focus trap: Focus stays in modal when open
- ✓ Accessibility: Screen reader announces modal open/close

### For Every User Interaction:
- ✓ Visual feedback: Hover states, active states, loading states
- ✓ Keyboard support: Enter/Space activate, Tab navigates, ESC cancels
- ✓ Screen reader: Announces state changes
- ✓ Error handling: User-friendly error messages

---

## SUCCESS METRICS

### Technical Quality:
- [ ] TypeScript strict mode: 0 type errors
- [ ] ESLint: 0 errors, 0 warnings (or all justified)
- [ ] Lighthouse scores: Performance > 90, Accessibility 100, Best Practices 100
- [ ] Bundle size: Initial load < 500KB, total < 2MB
- [ ] Browser support: Chrome, Firefox, Safari, Edge (latest 2 versions)

### Feature Completeness:
- [ ] All JSON sections rendered correctly
- [ ] All 3 languages (EN/DE/FA) working with RTL
- [ ] All 6 themes working
- [ ] Focus filtering working across all sections
- [ ] Media thumbnails + modal working
- [ ] PDF export (print) working
- [ ] Contact form + booking placeholders present

### User Experience:
- [ ] Smooth, professional animations (respecting reduced motion)
- [ ] Fast load time (< 3s on 3G)
- [ ] Intuitive navigation
- [ ] Clear visual hierarchy
- [ ] No layout shifts or jank
- [ ] Works without JavaScript (graceful degradation for critical content)

### Data Integrity:
- [ ] No crashes with malformed JSON
- [ ] Duplicate entries handled
- [ ] Invalid dates handled
- [ ] Missing fields handled
- [ ] All type_key filtering correct

---

## FUTURE ENHANCEMENTS (Out of Scope for Initial Build)

1. **Backend API Integration**
   - LaTeX-based PDF generation endpoint (calling existing Python generator)
   - Contact form submission endpoint
   - Booking system integration (Calendly or custom)

2. **Advanced Features**
   - Analytics integration (Google Analytics, Plausible)
   - SEO optimization (meta tags, Open Graph, JSON-LD)
   - Blog section (if desired)
   - Admin panel for JSON editing (CRUD UI)

3. **Content Enhancements**
   - Timeline visualization for education/experience
   - Skills radar chart
   - Project galleries with lightbox
   - Endorsements/testimonials section

4. **Technical Improvements**
   - Server-side rendering (Next.js migration)
   - Progressive Web App (PWA) features
   - Offline support
   - A/B testing framework

---

## BUILD ORDER RECOMMENDATION

1. **Foundation First** (Phase 0): Setup, types, data
2. **Core Layout** (Phase 1): Header, footer, themes, RTL
3. **Content Rendering** (Phase 2): Sections, one by one
4. **Advanced Features** (Phase 3): Filtering, media, animations
5. **Polish** (Phase 4): Robustness, responsive, accessibility
6. **Ship** (Phase 5): Documentation, QA, deployment

**Estimated Timeline** (for a single developer):
- Phase 0: 1-2 days
- Phase 1: 2-3 days
- Phase 2: 5-7 days (most time-consuming)
- Phase 3: 3-4 days
- Phase 4: 2-3 days
- Phase 5: 2-3 days
- **Total: 15-22 days** (3-4 weeks)

---

## FINAL VALIDATION CHECKLIST

Before considering the project complete, verify:

### Functional:
- [ ] Load each JSON (EN/DE/FA) - all content renders correctly
- [ ] Switch between all 6 themes - visual changes confirm
- [ ] Toggle through all focus filter options - sections update correctly
- [ ] Click all media thumbnails - modals open correctly
- [ ] Export PDF - print preview works, PDF is usable
- [ ] Test on mobile device - all features work
- [ ] Test keyboard-only navigation - entire site usable

### Technical:
- [ ] `npm run build` succeeds
- [ ] No TypeScript errors (`tsc --noEmit`)
- [ ] No ESLint errors
- [ ] Lighthouse: Performance > 90, Accessibility 100
- [ ] No console errors in browser

### Content:
- [ ] All JSON sections mapped to UI sections
- [ ] All fields from JSON displayed somewhere
- [ ] Duplicate projects deduplicated
- [ ] Invalid dates handled gracefully
- [ ] Missing fields don't crash

### Accessibility:
- [ ] All interactions keyboard accessible
- [ ] Focus indicators visible
- [ ] Screen reader test: page structure makes sense
- [ ] Color contrast meets WCAG AA

### Experience:
- [ ] Animations smooth (and respect reduced motion)
- [ ] Page feels professional and polished
- [ ] Navigation intuitive
- [ ] Load time acceptable (< 3s)

---

## OVERSIGHT SELF-CHECK (For AI/Developer Building This)

After completing each task, ask yourself:

1. **Did I actually implement the feature, or just create a placeholder?**
   - ✓ Component actually renders data from JSON
   - ✓ Not just hardcoded example data

2. **Does it work with real data?**
   - ✓ Tested with ramin.json
   - ✓ Tested with modified/incomplete JSON

3. **Is it accessible?**
   - ✓ Keyboard navigable
   - ✓ Screen reader friendly

4. **Is it responsive?**
   - ✓ Tested at mobile, tablet, desktop sizes

5. **Does filtering actually work?**
   - ✓ Changing focus filter updates visible entries
   - ✓ Verified by counting before/after

6. **Is RTL working?**
   - ✓ Switched to FA language and inspected layout

7. **Are themes applying?**
   - ✓ Changed theme and verified CSS custom properties changed

8. **Did I handle edge cases?**
   - ✓ Null/undefined, empty arrays, invalid dates, missing images

9. **Is the code maintainable?**
   - ✓ Clear naming, commented where complex, no magic numbers

10. **Would this pass a code review?**
    - ✓ Follows TypeScript best practices
    - ✓ Follows React best practices
    - ✓ No obvious performance issues

**If you answer "no" to any of these, the task is not complete.**

---

## CONTACT & CONTRIBUTION

For questions or contributions to this plan, refer to the repository maintainer.

This plan is a living document and should be updated as requirements evolve or technical constraints change.

---

**End of Plan**
