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

### PHASE 6: Enhanced UI Features

#### Task 6.1: Language Selector Carousel with 3D Card Effect
**Description**: Replace the simple language dropdown with an interactive 3D carousel showing all three language options (EN/DE/FA) simultaneously, with the selected language prominently in the foreground and the other two positioned behind it on the left and right.

**Acceptance Criteria**:
- [ ] Create `src/components/LanguageCarousel.tsx` component
- [ ] Display 3 language cards simultaneously (EN, DE, FA)
- [ ] Apply 3D transform effect: focused/selected card is larger and closer (z-axis forward)
- [ ] Non-selected cards are positioned behind on left and right with reduced scale and opacity
- [ ] Smooth transition animations when switching between languages (300-500ms)
- [ ] Cards are clickable to select that language
- [ ] Keyboard navigation: Arrow keys to cycle through languages, Enter to select
- [ ] Touch/swipe support for mobile devices
- [ ] Visual indicators: focused card has higher z-index, larger scale (e.g., 1.1x), full opacity
- [ ] Background cards: smaller scale (e.g., 0.85x), reduced opacity (0.6-0.7), slight blur
- [ ] Carousel wraps around: from FA, right arrow goes to EN; from EN, left arrow goes to FA
- [ ] Respect `prefers-reduced-motion` - disable 3D transforms, use simple fade/position change
- [ ] Replace or integrate with existing language switcher in header

**Visual Layout Example**:
```
     [DE]              [EN]              [FA]
   (smaller,        (focused,         (smaller,
    behind,         forward,          behind,
    left)           center)           right)
```

**Oversight Checks**:
- ✓ Visual inspection: three cards visible simultaneously
- ✓ Click on background card (e.g., DE when EN is focused) - DE moves to center/foreground, EN moves to background
- ✓ Verify CSS transforms: focused card has `transform: scale(1.1) translateZ(50px)` or similar
- ✓ Background cards have `transform: scale(0.85) translateZ(-20px)` or similar
- ✓ Press right arrow key - carousel cycles to next language smoothly
- ✓ Press left arrow key - carousel cycles to previous language
- ✓ On mobile: swipe left/right - carousel responds appropriately
- ✓ Check `prefers-reduced-motion: reduce` - 3D effects disabled, simple transition instead
- ✓ Verify animation duration is 300-500ms
- ✓ Selected language triggers actual language switch (loads corresponding JSON file)
- ✓ Test wrapping: from FA, next goes to EN; from EN, previous goes to FA
- ✓ Check z-index stacking: focused card is on top, others behind
- ✓ Verify touch targets are adequate on mobile (min 44x44px)

**Implementation Notes**:
- Use CSS `transform: perspective()` on container for 3D space
- Use `transform: rotateY()` for slight angle on side cards (optional enhancement)
- Use `transform: translateZ()` for depth effect
- Consider using `transform-style: preserve-3d` for nested 3D transforms
- State management: track current focused language index (0, 1, or 2)
- Animation: use CSS transitions or React Spring for smooth movement
- Accessibility: ensure focus indicators clear, screen reader announces language change

**Fallback Strategy** (Minimal Library Approach):
- Primary: Pure CSS transforms + React state for card positioning
- Fallback: If 3D transforms prove complex, use 2D approach with scale/opacity only
- No external carousel libraries needed - implement with vanilla React + CSS

**Dependencies**: Task 1.3 (Header component), Task 0.3 (Multi-language JSON files)

**Estimated Effort**: 1-2 days

---

#### Task 6.2: Premium Button & Interactive Elements System
**Description**: Create a comprehensive system for button hover effects, mouse interactions, and micro-animations that work consistently across all interactive elements.

**Acceptance Criteria**:
- [ ] Create `src/styles/interactions.css` with reusable interaction patterns
- [ ] Define button hover states: scale (1.05x), shadow elevation, color shift
- [ ] Add magnetic button effect: buttons slightly follow cursor when nearby (subtle, < 10px)
- [ ] Implement ripple effect on click (CSS-only or minimal JS)
- [ ] Create smooth transitions for all interactive states (150ms ease-out)
- [ ] Add focus-visible styles with animated border or glow effect
- [ ] Implement disabled state styling (reduced opacity, no-cursor)
- [ ] Create loading state animation (spinner or pulsing effect)
- [ ] Add "active" press-down effect (scale 0.95x) for tactile feedback
- [ ] Ensure all effects respect `prefers-reduced-motion`

**Visual Effects to Implement**:
- Primary buttons: Gradient background shift on hover, shadow elevation
- Secondary buttons: Border glow, background fade-in
- Icon buttons: Rotate or scale on hover
- Links: Underline slide-in effect from left to right
- Cards: Lift effect (translateY + shadow) on hover
- Input fields: Border color animation, label float effect

**Oversight Checks**:
- ✓ Hover over any button - smooth scale and shadow animation occurs
- ✓ Move cursor near button with magnetic effect - button subtly moves toward cursor
- ✓ Click button - ripple effect emanates from click point
- ✓ Tab to button - focus indicator animates in smoothly
- ✓ Verify disabled buttons have no hover effects
- ✓ Check all transitions are 150ms or appropriate duration
- ✓ Test with `prefers-reduced-motion: reduce` - only essential animations remain
- ✓ Verify consistency across all button types (primary, secondary, icon)

**Dependencies**: Task 1.1 (Theme system)

**Estimated Effort**: 1 day

---

#### Task 6.3: Parallax Scrolling & Depth Effects
**Description**: Add subtle parallax effects to create depth and premium feel during scrolling.

**Acceptance Criteria**:
- [ ] Implement parallax effect on hero cover image (scrolls slower than content)
- [ ] Add parallax to section backgrounds (if any decorative elements)
- [ ] Create depth layers: background (0.3x speed), mid-ground (0.6x speed), foreground (1x speed)
- [ ] Keep effects subtle (max 30% speed difference) to avoid motion sickness
- [ ] Use `transform: translateY()` with `will-change` for performance
- [ ] Implement via Intersection Observer + requestAnimationFrame
- [ ] Disable parallax on mobile (performance concern)
- [ ] Respect `prefers-reduced-motion: reduce` - disable all parallax

**Oversight Checks**:
- ✓ Scroll page - hero cover image moves slower than content (parallax effect visible)
- ✓ Verify performance: scrolling is smooth, no jank (use DevTools Performance tab)
- ✓ Check mobile - parallax disabled, normal scrolling
- ✓ Test `prefers-reduced-motion: reduce` - parallax disabled
- ✓ Verify `will-change: transform` applied to parallax elements

**Dependencies**: Task 2.1 (Hero section)

**Estimated Effort**: 0.5-1 day

---

#### Task 6.4: Skills Section Interactive Carousel/Slider
**Description**: Transform the skills display into an interactive horizontal carousel that showcases skill categories with smooth sliding transitions.

**Acceptance Criteria**:
- [ ] Create carousel for skill categories (Programming, Data Science, Soft Skills, etc.)
- [ ] Display 1-3 categories at a time depending on screen size (1 on mobile, 2 on tablet, 3 on desktop)
- [ ] Add navigation arrows (previous/next) with smooth slide animations
- [ ] Add dot indicators at bottom showing current position
- [ ] Auto-advance option (optional, with pause on hover)
- [ ] Swipe gestures on mobile/tablet
- [ ] Keyboard navigation: Arrow keys to navigate, Tab to enter/exit carousel
- [ ] Each category card shows title and skill items (badges/chips)
- [ ] Smooth easing function for slide transitions (cubic-bezier)
- [ ] Cards have subtle scale effect when entering/exiting viewport

**Visual Layout**:
```
[<] [Programming Languages] [Data Science] [>]
    • • ○ ○ ○  (dot indicators)
```

**Oversight Checks**:
- ✓ Click next arrow - carousel slides to next category smoothly
- ✓ Click previous arrow - carousel slides backward
- ✓ Swipe left on mobile - carousel advances
- ✓ Click dot indicator - carousel jumps to that category
- ✓ Verify 1 card visible on mobile, 2 on tablet, 3 on desktop
- ✓ Press arrow keys - carousel navigates
- ✓ Hover over carousel (if auto-advance enabled) - auto-advance pauses
- ✓ Check transition is smooth (300-500ms cubic-bezier easing)
- ✓ Verify `prefers-reduced-motion` - instant jumps instead of slides

**Dependencies**: Task 2.6 (Skills section)

**Estimated Effort**: 1-2 days

---

#### Task 6.5: Projects Gallery with Lightbox Carousel
**Description**: Transform projects section into an interactive gallery with image preview carousel and lightbox modal.

**Acceptance Criteria**:
- [ ] Display projects as grid of cards with project thumbnails (if available)
- [ ] Add hover effect: card lifts, shows overlay with project title and brief description
- [ ] Click on project card opens lightbox modal with full details
- [ ] Lightbox includes image carousel if project has multiple images
- [ ] Carousel has smooth transitions, thumbnail strip at bottom
- [ ] Arrow keys navigate between projects in lightbox
- [ ] Close button, ESC key, and click outside close lightbox
- [ ] Zoom in/out on images (optional pinch-to-zoom on mobile)
- [ ] Add filter/sort controls above gallery (by type_key or technology)
- [ ] Animate grid layout changes when filtering

**Oversight Checks**:
- ✓ Hover over project card - card lifts and overlay appears
- ✓ Click project card - lightbox opens with full details
- ✓ If multiple images, carousel works with smooth transitions
- ✓ Press arrow keys in lightbox - navigate between projects
- ✓ Press ESC - lightbox closes
- ✓ Click thumbnail - jumps to that image
- ✓ Filter projects by technology - grid animates layout changes
- ✓ Verify focus trap in lightbox
- ✓ Check mobile pinch-to-zoom works (if implemented)

**Dependencies**: Task 2.8 (Projects section), Task 3.1 (Media modal)

**Estimated Effort**: 2-3 days

---

#### Task 6.6: Timeline Visualization with Animated Progress
**Description**: Create an interactive vertical timeline for Education and Experience sections with animated progress indicators.

**Acceptance Criteria**:
- [ ] Create `src/components/Timeline.tsx` component
- [ ] Vertical line connecting all timeline entries
- [ ] Animated dots/nodes at each entry point
- [ ] Progress bar fills as user scrolls down the timeline
- [ ] Timeline animates in from left/right as it enters viewport
- [ ] Entries stagger in with fade + slide animation (200ms delay between items)
- [ ] Hover over timeline entry: highlight with color, slight scale
- [ ] Active entry indicator (based on scroll position)
- [ ] Add subtle connecting lines with animation (draw from top to bottom)
- [ ] Responsive: horizontal timeline on mobile (optional)

**Visual Example**:
```
    ○ ──── 2024: Master's Bioinformatics
    │
    ○ ──── 2021-2024: Master's Biotechnology
    │
    ○ ──── 2018-2021: Bachelor's
```

**Oversight Checks**:
- ✓ Scroll to timeline section - line draws from top to bottom
- ✓ Verify entries fade and slide in with stagger effect
- ✓ Scroll through timeline - progress indicator fills dynamically
- ✓ Hover over entry - highlight animation occurs
- ✓ Check stagger delay is ~200ms between items
- ✓ Verify timeline responsive on mobile
- ✓ Test `prefers-reduced-motion` - no animation, all content immediately visible

**Dependencies**: Task 2.3 (Education section), Task 2.7 (Experience section)

**Estimated Effort**: 2 days

---

#### Task 6.7: Cursor Follower & Custom Cursor Effects
**Description**: Implement a custom cursor with trailing effect and contextual changes based on hover targets.

**Acceptance Criteria**:
- [ ] Create `src/components/CursorFollower.tsx`
- [ ] Custom cursor circle follows mouse position (hidden default cursor)
- [ ] Trailing effect: second larger circle follows with delay (100-150ms)
- [ ] Cursor changes on hover: scale up over links/buttons, change color
- [ ] Blend mode for interesting visual effect (e.g., `mix-blend-mode: difference`)
- [ ] Smooth interpolation using lerp (linear interpolation) for fluid movement
- [ ] Only active on desktop (hide on mobile/touch devices)
- [ ] Disable if user prefers default cursor (check user agent/settings)
- [ ] Respect `prefers-reduced-motion` - reduce trail effect complexity

**Cursor States**:
- Default: small circle (8px diameter)
- Hover link/button: large circle (32px diameter) with reduced opacity
- Hover text: vertical line cursor for text selection
- Click/active: shrink briefly (6px) then return

**Oversight Checks**:
- ✓ Move mouse - custom cursor smoothly follows with trail
- ✓ Hover over button - cursor scales up to 32px
- ✓ Hover over text - cursor changes to text selection style
- ✓ Click - cursor briefly shrinks
- ✓ Verify trail circle follows with ~100ms delay
- ✓ Check on mobile - custom cursor hidden, native cursor visible
- ✓ Test performance - no impact on scroll/interaction smoothness
- ✓ Verify `prefers-reduced-motion` - simplified cursor or disabled

**Dependencies**: None (global feature)

**Estimated Effort**: 1-2 days

---

#### Task 6.8: Smooth Page Transitions & Section Reveal Animations
**Description**: Enhance page load and section transitions with sophisticated reveal animations.

**Acceptance Criteria**:
- [ ] Implement page load animation: fade in from dark with logo/name reveal
- [ ] Stagger section reveals as user scrolls (each section has unique entrance)
- [ ] Section entrance styles:
  - Hero: Fade in + scale from 0.95 to 1.0
  - Education/Experience: Slide in from left with fade
  - Skills: Slide in from right with fade
  - Projects: Grid items pop in with stagger (cascade effect)
  - Publications: Fade in from bottom
- [ ] Use Intersection Observer for scroll-triggered animations
- [ ] Each animation respects timing: 500ms duration, 100ms stagger between items
- [ ] Add subtle background pattern animations (optional: animated gradients, particles)
- [ ] Ensure animations only trigger once (not on every scroll)
- [ ] Respect `prefers-reduced-motion` - instant appearance, no animation

**Oversight Checks**:
- ✓ Refresh page - smooth fade in with logo reveal
- ✓ Scroll to each section - appropriate entrance animation triggers
- ✓ Verify stagger timing between items (100ms)
- ✓ Scroll back up and down - animations don't retrigger
- ✓ Check multiple sections animating simultaneously look smooth
- ✓ Test `prefers-reduced-motion: reduce` - all content immediately visible
- ✓ Verify no layout shift during animations

**Dependencies**: Task 2.1-2.10 (all sections)

**Estimated Effort**: 2 days

---

#### Task 6.9: Floating Action Button (FAB) with Quick Actions
**Description**: Add a floating action button in the bottom-right corner with expandable quick action menu.

**Acceptance Criteria**:
- [ ] Create `src/components/FloatingActionButton.tsx`
- [ ] Circular FAB button fixed in bottom-right corner
- [ ] Primary action: "Back to top" (scrolls smoothly to page top)
- [ ] Click/tap to expand: reveals 3-4 quick action buttons radially
- [ ] Quick actions:
  - Back to top (scroll to hero)
  - Download PDF (triggers print dialog)
  - Contact (scrolls to contact form)
  - Toggle theme (quick theme switcher)
- [ ] Smooth expand/collapse animation (rotate + scale sub-buttons)
- [ ] FAB hides when at top of page, appears when scrolling down
- [ ] Hover effect: FAB pulses subtly
- [ ] Mobile-friendly: adequate touch target size (56x56px minimum)
- [ ] Keyboard accessible: Tab to focus, Enter/Space to activate

**Visual Layout (Expanded)**:
```
        ○ (Back to top)
       ╱
      ● ─ ○ (Download PDF)
       ╲
        ○ (Contact)
```

**Oversight Checks**:
- ✓ Scroll down - FAB appears with fade-in animation
- ✓ Scroll to top - FAB disappears
- ✓ Click FAB - sub-buttons expand radially with smooth animation
- ✓ Click "Back to top" - smoothly scrolls to top
- ✓ Click "Download PDF" - print dialog opens
- ✓ Verify FAB size is adequate for touch (56x56px)
- ✓ Tab to FAB - focus indicator visible, Enter activates
- ✓ Test on mobile - FAB doesn't obscure content
- ✓ Check z-index: FAB appears above all content but below modals

**Dependencies**: Task 1.4 (Footer), Task 3.4 (PDF export)

**Estimated Effort**: 1 day

---

#### Task 6.10: Theme Transition Animations
**Description**: Add smooth visual transitions when switching between themes instead of instant changes.

**Acceptance Criteria**:
- [ ] Implement cross-fade animation when changing themes (500ms duration)
- [ ] Use CSS transitions on all theme-related custom properties
- [ ] Add visual feedback during theme switch: brief color wave or gradient sweep
- [ ] Prevent flash of unstyled content (FOUC) during transition
- [ ] Smooth transition for background colors, text colors, borders, shadows
- [ ] Add theme preview thumbnails in theme switcher (mini cards showing colors)
- [ ] Theme switcher shows current theme with checkmark or highlight
- [ ] Persist theme smoothly: no flash on page reload

**Oversight Checks**:
- ✓ Switch theme - smooth cross-fade occurs (500ms)
- ✓ Verify no jarring color shifts or flashes
- ✓ Check all elements transition smoothly (background, text, borders, shadows)
- ✓ Open theme switcher - preview thumbnails show each theme's colors
- ✓ Current theme is clearly highlighted
- ✓ Refresh page - theme loads without flash (stored in localStorage, applied before render)
- ✓ Test rapid theme switching - transitions queue properly without breaking

**Dependencies**: Task 1.1 (Theme system), Task 1.3 (Header with theme switcher)

**Estimated Effort**: 1 day

---

#### Task 6.11: Scroll Progress Indicator
**Description**: Add a visual indicator showing reading progress through the page.

**Acceptance Criteria**:
- [ ] Create horizontal progress bar at top of page (fixed position)
- [ ] Bar fills from left to right as user scrolls down
- [ ] Calculate progress: `scrollTop / (scrollHeight - clientHeight)`
- [ ] Smooth animation using CSS transition or requestAnimationFrame
- [ ] Color matches current theme's primary color
- [ ] Minimal height (2-3px) to avoid being intrusive
- [ ] Add subtle glow effect on progress bar
- [ ] Option to show section markers on progress bar (dots indicating section boundaries)

**Oversight Checks**:
- ✓ Scroll down - progress bar fills proportionally
- ✓ Scroll to bottom - progress bar reaches 100%
- ✓ Verify smooth animation (no jank)
- ✓ Check color matches theme primary color
- ✓ Switch theme - progress bar color updates
- ✓ Verify height is subtle (2-3px)
- ✓ If section markers enabled, verify they align with actual sections

**Dependencies**: Task 1.1 (Theme system)

**Estimated Effort**: 0.5 days

---

#### Task 6.12: Easter Egg: Konami Code Unlockable Theme
**Description**: Add a fun hidden feature that unlocks a special theme when user enters the Konami code.

**Acceptance Criteria**:
- [ ] Detect Konami code sequence: ↑ ↑ ↓ ↓ ← → ← → B A
- [ ] On successful entry: unlock "Secret" theme (e.g., retro, neon, matrix style)
- [ ] Show brief celebration animation (confetti, particles, or screen flash)
- [ ] Add "Secret" theme to theme switcher after unlock
- [ ] Persist unlock state in localStorage
- [ ] Add subtle hint in footer or about section: "Try the Konami code 🎮"
- [ ] Ensure doesn't interfere with normal keyboard navigation
- [ ] Make it fun but professional (not distracting from CV content)

**Secret Theme Suggestions**:
- Retro/Terminal: Green text on black, monospace font, CRT scanline effect
- Neon/Cyberpunk: Dark background with neon accent colors, glow effects
- Matrix: Falling characters animation in background (subtle)

**Oversight Checks**:
- ✓ Enter Konami code sequence - celebration animation triggers
- ✓ Secret theme appears in theme switcher
- ✓ Apply secret theme - unique styling applied
- ✓ Refresh page - secret theme remains unlocked (localStorage)
- ✓ Verify normal keyboard navigation still works
- ✓ Check hint text is visible but subtle
- ✓ Ensure secret theme is still professional and readable

**Dependencies**: Task 1.1 (Theme system), Task 1.3 (Theme switcher)

**Estimated Effort**: 1 day (for fun and delight!)

---

### PHASE 6 SUMMARY

**Total Tasks in Phase 6**: 12 tasks (6.1 - 6.12)

**Focus Areas**:
- Interactive carousels and sliders (Language, Skills, Projects)
- Premium micro-interactions (buttons, hover effects, cursor)
- Smooth animations and transitions (scroll, page load, theme switching)
- Visual depth and polish (parallax, timeline, progress indicator)
- Delightful details (FAB, easter egg)

**Estimated Total Effort for Phase 6**: 15-20 days

**Key Principles**:
- All animations respect `prefers-reduced-motion: reduce`
- Mobile-first responsive design
- Performance-conscious (60fps target)
- Accessibility maintained (keyboard navigation, focus indicators)
- Consistent with theme system
- Pure CSS/minimal JS approach where possible

**Testing Checklist for Phase 6**:
- [ ] All animations smooth (60fps) on desktop
- [ ] All interactions work on mobile/touch devices
- [ ] Keyboard navigation complete and intuitive
- [ ] No performance degradation with all effects active
- [ ] All effects disabled properly with `prefers-reduced-motion`
- [ ] Visual consistency across all 6 themes + secret theme
- [ ] No accessibility regressions

---

#### Task 6.13: Conditional Section Rendering - Hide Empty Sections
**Description**: Implement logic to automatically hide sections and their headings when they contain no data or empty arrays, ensuring a clean, content-driven layout.

**Acceptance Criteria**:
- [ ] Create utility function `src/utils/sectionVisibility.ts` to check if section has content
- [ ] Check conditions for each section type:
  - Array-based sections (education, experiences, projects, publications, references, certifications, languages): Hide if array is empty or undefined
  - Object-based sections (skills): Hide if object is empty, has no keys, or all nested arrays are empty
  - Nested data (skills categories): Hide category if items array is empty
- [ ] Apply conditional rendering to all section components
- [ ] Hide section wrapper, heading, and any decorative elements when empty
- [ ] Ensure no empty space or visual artifacts left behind
- [ ] Handle edge cases: null values, undefined fields, arrays with only null/undefined items
- [ ] Filtering consideration: If focus filter results in no items, show "No results for this filter" message instead of hiding section
- [ ] Update navigation menu: hide links to empty sections or disable/gray them out

**Section-Specific Rules**:
- **Hero/Basics**: Always visible (core identity section)
- **Profiles**: Hide if `profiles` array is empty
- **Education**: Hide if `education` array is empty or all entries filtered out
- **Languages**: Hide if `languages` array is empty
- **Certifications**: Hide if `workshop_and_certifications` array is empty
- **Skills**: Hide if `skills` object is empty or all categories have empty items
- **Experiences**: Hide if `experiences` array is empty
- **Projects**: Hide if `projects` array is empty (after deduplication)
- **Publications**: Hide if `publications` array is empty
- **References**: Hide if `references` array is empty
- **Contact Form**: Always visible (placeholder for future)
- **Booking Widget**: Always visible (placeholder for future)

**Implementation Pattern**:
```typescript
// Example utility function
export const hasSectionContent = (data: any, sectionType: string): boolean => {
  if (!data) return false;
  
  switch (sectionType) {
    case 'array':
      return Array.isArray(data) && data.length > 0;
    case 'skills':
      return data && Object.keys(data).some(section => 
        Object.keys(data[section]).some(category => 
          Array.isArray(data[section][category]) && 
          data[section][category].length > 0
        )
      );
    default:
      return !!data;
  }
};

// Example component usage
{hasSectionContent(education, 'array') && (
  <EducationSection data={education} />
)}
```

**Oversight Checks**:
- ✓ Remove `education` array from JSON - Education section and heading not visible
- ✓ Set `profiles` to empty array `[]` - Profiles section not visible
- ✓ Remove all items from a skills category - that category heading not visible
- ✓ Remove all skills categories - entire Skills section not visible
- ✓ Verify navigation menu updates: links to empty sections hidden or disabled
- ✓ Apply focus filter that results in no matches - section shows "No results" message, not hidden
- ✓ Hero/Basics section always visible even if some fields are missing
- ✓ Contact and Booking sections always visible (placeholders)
- ✓ Check for any leftover spacing or visual gaps where hidden sections were
- ✓ Verify smooth transitions if sections appear/disappear due to filtering
- ✓ Test with completely empty JSON (only basics) - only Hero and placeholders visible

**User Experience Considerations**:
- When section is hidden due to filtering, show subtle message: "No [section name] match your current filter. Try 'Full CV' to see all."
- Provide visual feedback when many sections are hidden
- Ensure page doesn't look broken when multiple sections are hidden
- Consider adding a "Show empty sections" toggle in settings for debugging/completeness view

**Dependencies**: Task 2.1-2.10 (all section components), Task 3.2 (filtering logic)

**Estimated Effort**: 1 day

---

#### Task 6.14: Universal Section Heading System
**Description**: Create a unified, beautiful, and flexible section heading component system that maintains visual consistency across all sections while supporting different heading styles (with/without buttons, icons, decorations).

**Acceptance Criteria**:
- [ ] Create `src/components/SectionHeading.tsx` as universal heading component
- [ ] Support multiple heading variants:
  - **Standard**: Title with decorative underline/accent
  - **With Action**: Title + action button (e.g., "View All", "Download")
  - **With Icon**: Title + leading icon (contextual to section)
  - **With Counter**: Title + item count badge (e.g., "Projects (12)")
  - **With Filter Info**: Title + current filter indicator
- [ ] Consistent spacing and sizing across all sections
- [ ] Animated entrance: Slide in from side with fade (respects reduced motion)
- [ ] Decorative elements:
  - Gradient underline that animates in from left
  - Optional accent icon/glyph before title
  - Optional subtle background pattern or shape
- [ ] Theme-aware: colors adapt to current theme
- [ ] RTL-compatible: decorations flip direction in RTL mode
- [ ] Typography: Clear hierarchy (title, subtitle, metadata)

**Component API Example**:
```typescript
interface SectionHeadingProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  variant?: 'standard' | 'with-action' | 'with-icon' | 'with-counter';
  actionButton?: {
    label: string;
    onClick: () => void;
    icon?: React.ReactNode;
  };
  count?: number;
  filterActive?: string;
  className?: string;
}
```

**Visual Design Patterns**:
- Title: 32px font-size, bold, theme primary color
- Subtitle: 16px, theme secondary color, optional italic
- Underline: 4px height, gradient from primary to accent, 60% width, animated expand
- Icon: 24x24px, positioned left (right in RTL), theme accent color
- Action button: Outlined style, hover scale effect, positioned right (left in RTL)
- Spacing: 48px margin-bottom, 24px padding-top

**Oversight Checks**:
- ✓ Replace all section headings with `<SectionHeading />` component
- ✓ Verify consistent spacing and sizing across all sections
- ✓ Scroll to each section - heading animates in smoothly
- ✓ Check all 4 variants render correctly (standard, with-action, with-icon, with-counter)
- ✓ Switch themes - heading colors update appropriately
- ✓ Switch to FA (RTL) - decorations and buttons flip correctly
- ✓ Test `prefers-reduced-motion` - animations disabled
- ✓ Hover action button - scale and color transition smooth
- ✓ Verify underline gradient animates from left to right (right to left in RTL)

**Dependencies**: Task 1.1 (Theme system), Task 1.2 (RTL support)

**Estimated Effort**: 1-2 days

---

#### Task 6.15: Section Container Animation System
**Description**: Create a universal container component for sections with entrance animations, background effects, and consistent visual treatments.

**Acceptance Criteria**:
- [ ] Create `src/components/SectionContainer.tsx` component
- [ ] Wrap all content sections (not hero) with this container
- [ ] Intersection Observer-based entrance animations
- [ ] Multiple animation styles assigned by section type:
  - **Education/Experience**: Slide from left with fade
  - **Skills/Languages**: Slide from right with fade
  - **Projects/Publications**: Zoom in with fade (scale 0.95 → 1.0)
  - **References/Contact**: Fade up with subtle bounce
- [ ] Background decoration options:
  - Subtle gradient overlay
  - Geometric pattern (dots, lines, shapes) - theme-aware
  - Optional colored accent bar on left/right edge
- [ ] Consistent padding and max-width (1200px)
- [ ] Alternating background colors (surface vs. background) for visual rhythm
- [ ] Smooth transitions between sections (no jarring breaks)

**Component API Example**:
```typescript
interface SectionContainerProps {
  id: string;
  animationType?: 'slide-left' | 'slide-right' | 'zoom' | 'fade-up';
  background?: 'default' | 'alternate' | 'gradient';
  accentBar?: boolean;
  pattern?: 'none' | 'dots' | 'lines' | 'grid';
  children: React.ReactNode;
}
```

**Visual Treatments**:
- Padding: 80px vertical, 24px horizontal (mobile: 48px vertical, 16px horizontal)
- Max-width: 1200px centered
- Border-radius: 16px on cards within sections (optional)
- Shadow: Subtle elevation on hover (optional for card-style sections)
- Accent bar: 4px width, full height, primary color, left edge (right in RTL)

**Oversight Checks**:
- ✓ All sections wrapped with `<SectionContainer />`
- ✓ Scroll through page - each section animates in with unique entrance
- ✓ Verify alternating backgrounds create visual rhythm
- ✓ Check accent bars appear correctly and flip in RTL
- ✓ Background patterns visible and subtle (not distracting)
- ✓ Animations smooth and performant (60fps)
- ✓ Test `prefers-reduced-motion` - content appears instantly
- ✓ Mobile layout: padding adjusts appropriately

**Dependencies**: Task 2.1-2.10 (all sections), Task 3.3 (scroll animations)

**Estimated Effort**: 2 days

---

#### Task 6.16: Interactive Section Action Buttons
**Description**: Standardize and enhance action buttons within sections (expand/collapse, filter, sort, view more) with consistent styling and micro-interactions.

**Acceptance Criteria**:
- [ ] Create `src/components/SectionActionButton.tsx` component
- [ ] Button types:
  - **Expand/Collapse**: Toggle long content visibility
  - **View More**: Load additional items or navigate to detail view
  - **Download**: Export section content (CSV, PDF, etc.)
  - **Filter**: Quick filter toggle specific to section
  - **Sort**: Change sort order of items
- [ ] Consistent visual design:
  - Outlined style with theme border color
  - Fill on hover with smooth color transition
  - Icon + label (icon can be before or after text)
  - Loading state (spinner animation)
  - Disabled state (reduced opacity, no interactions)
- [ ] Micro-interactions:
  - Ripple effect on click
  - Icon rotation/transformation (e.g., chevron rotates on expand/collapse)
  - Color shift on hover (border + background + text)
  - Subtle scale on hover (1.02x)
- [ ] Keyboard accessible: Tab to focus, Enter/Space to activate
- [ ] Size variants: small, medium, large
- [ ] Position variants: inline, floating (absolute positioned)

**Component API Example**:
```typescript
interface SectionActionButtonProps {
  type: 'expand' | 'view-more' | 'download' | 'filter' | 'sort';
  label: string;
  icon?: React.ReactNode;
  iconPosition?: 'before' | 'after';
  onClick: () => void;
  loading?: boolean;
  disabled?: boolean;
  size?: 'small' | 'medium' | 'large';
  variant?: 'outline' | 'filled' | 'ghost';
}
```

**Oversight Checks**:
- ✓ Replace all section action buttons with standardized component
- ✓ Hover over each button - smooth color and scale transition
- ✓ Click button - ripple effect visible
- ✓ Test expand/collapse button - icon rotates smoothly (e.g., chevron)
- ✓ Tab through buttons - focus indicators clear
- ✓ Verify loading state shows spinner
- ✓ Verify disabled state prevents interaction
- ✓ Check all size variants render correctly

**Dependencies**: Task 6.2 (Button system), Task 6.14 (Section headings)

**Estimated Effort**: 1 day

---

#### Task 6.17: Section Dividers with Decorative Elements
**Description**: Create elegant, animated dividers between sections that enhance visual flow and maintain design consistency.

**Acceptance Criteria**:
- [ ] Create `src/components/SectionDivider.tsx` component
- [ ] Multiple divider styles:
  - **Line with Icon**: Horizontal line with centered icon/ornament
  - **Gradient Fade**: Gradient line that fades at edges
  - **Dots Pattern**: Row of decorative dots
  - **Wave**: Wavy SVG path
  - **Minimal**: Simple thin line
- [ ] Animations:
  - Line expands from center outward on scroll into view
  - Icon fades in and scales up
  - Dots appear with stagger effect
- [ ] Contextual icons based on adjacent sections (optional):
  - Education → graduation cap
  - Experience → briefcase
  - Skills → star/badge
  - Projects → code/tools
  - Publications → book/document
- [ ] Theme-aware colors
- [ ] RTL-compatible animations
- [ ] Spacing: 64px margin vertical (separates sections clearly)

**Visual Specifications**:
- Line height: 2px (standard), 1px (minimal)
- Icon size: 32x32px, in circle (48x48px) with theme background
- Gradient: from transparent → primary → accent → transparent
- Dots: 6-8 dots, 8px diameter, spaced 16px apart
- Wave: Subtle amplitude (20px), theme accent color

**Oversight Checks**:
- ✓ Dividers appear between all major sections
- ✓ Scroll to divider - animation triggers (line expands, icon appears)
- ✓ Verify appropriate icon for each section transition
- ✓ Check gradient colors match current theme
- ✓ Switch to RTL - animations flip direction correctly
- ✓ Test `prefers-reduced-motion` - dividers appear instantly
- ✓ Verify consistent spacing (64px) between sections

**Dependencies**: Task 1.1 (Theme system), Task 3.3 (Scroll animations)

**Estimated Effort**: 1 day

---

#### Task 6.18: Section Metadata Display System
**Description**: Create a consistent system for displaying metadata within sections (dates, tags, counts, status indicators) with unified styling.

**Acceptance Criteria**:
- [ ] Create reusable metadata components:
  - `<DateRange />`: Display date ranges with icon (start-end or ongoing)
  - `<Tag />`: Styled badge for categories, skills, technologies
  - `<StatusBadge />`: Status indicators (active, completed, in-progress, published)
  - `<Counter />`: Number display with icon (views, likes, items count)
  - `<LocationPin />`: Location display with pin icon
- [ ] Consistent visual design:
  - Tags: Rounded pills, theme surface background, border, small padding
  - Dates: Icon + formatted date, theme secondary color
  - Status: Colored dot + label, specific colors per status
  - Counter: Icon + number, theme accent color
- [ ] Hover effects on interactive metadata (e.g., clickable tags)
- [ ] Truncation handling for long metadata
- [ ] Group spacing between multiple metadata items
- [ ] Mobile-responsive: stack or wrap gracefully

**Visual Specifications**:
- Tags: 24px height, 8px padding horizontal, 12px border-radius, 12px font-size
- Dates: 14px font-size, icon 16x16px, secondary color
- Status badge: 8px dot, 14px font-size, 4px gap between dot and label
- Counter: 16x16px icon, 14px font-size, bold number

**Color Coding for Status**:
- Active/Published: Green (#10b981)
- In Progress/Draft: Yellow (#f59e0b)
- Completed/Archived: Blue (#3b82f6)
- Inactive/Unpublished: Gray (#6b7280)

**Oversight Checks**:
- ✓ Replace all inline metadata displays with standardized components
- ✓ Verify consistent styling across all sections
- ✓ Hover over tags - subtle scale or background change
- ✓ Check date formatting handles various formats (ISO, relative, etc.)
- ✓ Verify status colors match specification
- ✓ Test long metadata - truncation works correctly
- ✓ Mobile view - metadata wraps/stacks appropriately
- ✓ RTL mode - icons and spacing flip correctly

**Dependencies**: Task 2.1-2.10 (all sections)

**Estimated Effort**: 1-2 days

---

#### Task 6.19: Unified Card Component System
**Description**: Create a flexible card component system used across all sections for consistent item display (education entries, projects, publications, etc.).

**Acceptance Criteria**:
- [ ] Create `src/components/Card.tsx` base component
- [ ] Card variants:
  - **Timeline Card**: Vertical timeline connector, date on side
  - **Grid Card**: Equal height cards in grid layout
  - **List Card**: Full-width horizontal layout
  - **Feature Card**: Large with image/media at top
  - **Compact Card**: Minimal vertical space, dense info
- [ ] Visual elements:
  - Subtle shadow/border
  - Hover effect: lift (translateY -4px) + shadow elevation
  - Optional header image/thumbnail
  - Content area with proper spacing
  - Footer area for metadata/actions
- [ ] Interactive states:
  - Default: subtle shadow
  - Hover: elevated shadow, slight lift
  - Active/Selected: border highlight with theme accent
  - Disabled: reduced opacity, no interactions
- [ ] Consistent spacing and padding
- [ ] Theme-aware colors and shadows
- [ ] Click to expand/view details (optional)

**Component API Example**:
```typescript
interface CardProps {
  variant?: 'timeline' | 'grid' | 'list' | 'feature' | 'compact';
  header?: React.ReactNode;
  thumbnail?: string;
  content: React.ReactNode;
  footer?: React.ReactNode;
  interactive?: boolean;
  selected?: boolean;
  onClick?: () => void;
  className?: string;
}
```

**Visual Specifications**:
- Border-radius: 12px
- Padding: 24px (compact: 16px)
- Shadow (default): 0 2px 8px rgba(0,0,0,0.1)
- Shadow (hover): 0 8px 24px rgba(0,0,0,0.15)
- Transition: all 200ms ease-out
- Thumbnail: 16:9 aspect ratio, border-radius 8px on top corners

**Oversight Checks**:
- ✓ Replace all section items with appropriate Card variant
- ✓ Hover over card - smooth lift and shadow animation
- ✓ Verify consistent spacing across all card instances
- ✓ Click interactive card - onClick handler fires
- ✓ Check selected state has accent border
- ✓ Verify thumbnail images have correct aspect ratio and border-radius
- ✓ Test grid layout - cards have equal heights
- ✓ Mobile view - cards stack and maintain readability
- ✓ Theme switch - card colors and shadows update

**Dependencies**: Task 1.1 (Theme system), Task 2.1-2.10 (all sections)

**Estimated Effort**: 2-3 days

---

#### Task 6.20: Section Loading States & Skeletons
**Description**: Implement elegant loading skeletons and states for sections while data is being fetched or filtered.

**Acceptance Criteria**:
- [ ] Create `src/components/SkeletonLoader.tsx` component
- [ ] Skeleton variants matching actual content:
  - Card skeleton (for education, projects, etc.)
  - List item skeleton
  - Timeline entry skeleton
  - Grid item skeleton
  - Heading skeleton
- [ ] Shimmer animation effect (gradient moves across skeleton)
- [ ] Correct dimensions matching actual content
- [ ] Show appropriate number of skeleton items (3-5 typically)
- [ ] Smooth transition from skeleton to actual content (fade)
- [ ] Loading indicator for actions (e.g., applying filters)
- [ ] Empty state messaging when no data (different from loading)

**Visual Design**:
- Skeleton color: theme surface color with slightly lighter overlay
- Shimmer gradient: linear gradient moving left to right
- Animation duration: 1.5s infinite
- Border-radius matches actual components
- Spacing matches actual layout

**Oversight Checks**:
- ✓ Temporarily add loading state - skeletons appear
- ✓ Verify shimmer animation smooth and not distracting
- ✓ Skeleton dimensions match actual content
- ✓ Transition to real content is smooth (no jump)
- ✓ Apply filter - loading indicator appears briefly
- ✓ Empty state shows appropriate message, not skeleton
- ✓ Test on slow connection (throttle network) - UX acceptable
- ✓ Theme switch - skeleton colors update

**Dependencies**: Task 6.19 (Card system), Task 2.1-2.10 (all sections)

**Estimated Effort**: 1-2 days

---

### PHASE 6 SUMMARY (Updated)

**Total Tasks in Phase 6**: 20 tasks (6.1 - 6.20)

**Focus Areas**:
- Interactive carousels and sliders (Language, Skills, Projects)
- Premium micro-interactions (buttons, hover effects, cursor)
- Smooth animations and transitions (scroll, page load, theme switching)
- Visual depth and polish (parallax, timeline, progress indicator)
- **Universal design system (headings, containers, cards, metadata)**
- **Visual consistency and integrity across all sections**
- Delightful details (FAB, easter egg)

**Estimated Total Effort for Phase 6**: 23-30 days

**Design Principles for Tasks 6.14-6.20**:
- **Consistency First**: All sections use the same visual language
- **Contextual Variation**: Components adapt to section needs without breaking consistency
- **Progressive Enhancement**: Core content works, animations enhance
- **Theme Integration**: All components respect active theme
- **RTL Compatibility**: All visual elements flip correctly
- **Accessibility**: Keyboard navigation, screen readers, reduced motion support
- **Performance**: Smooth 60fps animations, optimized rendering

**Integration Checklist**:
- [ ] All sections use `<SectionHeading />` component
- [ ] All sections wrapped in `<SectionContainer />`
- [ ] All action buttons use `<SectionActionButton />`
- [ ] Dividers placed between major sections
- [ ] Metadata displays use standardized components
- [ ] All list items use appropriate `<Card />` variant
- [ ] Loading states implemented for all sections
- [ ] Visual consistency verified across all themes
- [ ] RTL mode works perfectly for all new components
- [ ] No accessibility regressions

---

**End of Plan**
