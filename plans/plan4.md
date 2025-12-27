# Plan 4: Advanced Features - Filtering, Media, Animations (Phase 3)

## Goal
Implement advanced interactive features including unified media handling with thumbnails and modals, global focus filtering across all sections, smooth scroll animations, PDF generation, and placeholder components for future backend integration.

## Scope
This plan covers:
- Task 3.1: Unified Media Thumbnail + Modal System
- Task 3.2: Global Focus Filter Implementation
- Task 3.3: Smooth Scroll & Scroll Animations
- Task 3.4: PDF Generation (Print-Based)
- Task 3.5: Contact Form Placeholder
- Task 3.6: Book a Call Placeholder

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

### Task 3.1: Unified Media Thumbnail + Modal System

**Acceptance Criteria**:
- [ ] Create `src/utils/mediaDetector.ts` to identify image/PDF URLs by extension
- [ ] Create `src/components/MediaThumbnail.tsx` component
- [ ] Thumbnail: small preview (image: actual thumbnail, PDF: icon + filename)
- [ ] Create `src/components/MediaModal.tsx` for full-view
- [ ] Modal: overlay, close button, ESC key closes, focus trap, click outside closes
- [ ] Display images directly, PDFs in iframe or link to open
- [ ] Keyboard navigation: Tab through close button, arrow keys for gallery (if multiple)

**Verification Checks**:
- Identify all media URLs in JSON (Pictures, publication URLs, reference URLs, project images)
- Click thumbnail - modal opens with full content
- Press ESC - modal closes
- Click outside modal content - modal closes
- Tab in modal - focus stays within modal (focus trap)
- Check PDF URL opens in iframe or new tab

### Task 3.2: Global Focus Filter Implementation

**Acceptance Criteria**:
- [ ] Create `src/context/FilterContext.tsx` (React Context)
- [ ] Store selected focus value (string)
- [ ] Provide function to change focus
- [ ] All sections (Education, Skills, Projects, etc.) subscribe to context
- [ ] Filter logic: if focus === "Full CV", show all; else show only entries where `type_key.includes(focus)`
- [ ] Derive filter options dynamically from JSON data (union of all type_key values)
- [ ] Persist selected focus to localStorage

**Verification Checks**:
- Change focus in header dropdown - verify all sections update simultaneously
- Count visible entries in each section - matches filter logic
- Select "Full CV" - all entries across all sections appear
- Select "Programming" - only relevant entries appear
- Refresh page - focus filter persists from localStorage
- Check DevTools React context value changes on filter switch

### Task 3.3: Smooth Scroll & Scroll Animations

**Acceptance Criteria**:
- [ ] Navigation links trigger smooth scroll via `scrollIntoView({ behavior: 'smooth' })`
- [ ] Detect when sections enter viewport using Intersection Observer
- [ ] Fade-in animation on sections as they enter viewport
- [ ] Stagger animation for lists (education, projects, etc.)
- [ ] Disable animations if `prefers-reduced-motion: reduce`

**Verification Checks**:
- Click nav link - page scrolls smoothly to section
- Scroll manually - sections fade in as they enter viewport
- Check DevTools: `prefers-reduced-motion: reduce` - animations disabled
- Verify no layout shift during animation

### Task 3.4: PDF Generation (Print-Based)

**Acceptance Criteria**:
- [ ] Create `src/styles/print.css` media query stylesheet
- [ ] Hide header, footer, theme switcher, language switcher in print mode
- [ ] Optimize layout for A4 page
- [ ] Ensure all sections visible (no pagination breaks in awkward places)
- [ ] PDF Export button in footer triggers `window.print()`
- [ ] Add comment in code for future backend API seam (e.g., LaTeX generator)

**Verification Checks**:
- Click PDF Export - print preview opens
- In print preview, header/footer not visible
- In print preview, content is well-formatted, readable
- Save as PDF from print dialog - PDF is usable
- Verify comment in code: `// TODO: Replace with backend API call for LaTeX PDF generation`

### Task 3.5: Contact Form Placeholder

**Acceptance Criteria**:
- [ ] Create `src/components/ContactForm.tsx`
- [ ] Fields: Name, Email, Subject, Message
- [ ] Submit button (onClick shows alert: "Backend not implemented yet")
- [ ] Form validation (client-side: required fields, email format)
- [ ] Accessible form labels and error messages
- [ ] Add comment for future backend integration point

**Verification Checks**:
- Fill form and submit - alert appears with message about backend
- Submit with empty required field - validation error shows
- Enter invalid email - validation error shows
- Tab through form - all fields keyboard accessible
- Verify comment: `// TODO: POST to /api/contact endpoint`

### Task 3.6: Book a Call Placeholder

**Acceptance Criteria**:
- [ ] Create `src/components/BookingWidget.tsx`
- [ ] Display placeholder calendar/scheduling UI
- [ ] Button: "Book a Call" (onClick shows alert: "Booking system not implemented yet")
- [ ] Add comment for future integration (e.g., Calendly API)

**Verification Checks**:
- Click "Book a Call" - alert appears
- Verify comment: `// TODO: Integrate Calendly or custom booking backend`

---

## Success Criteria

- [ ] Media thumbnails render for all detected media URLs
- [ ] Media modal works with keyboard navigation and focus trap
- [ ] Global filter updates all sections simultaneously
- [ ] Filter persists across page refresh
- [ ] Smooth scroll and animations working
- [ ] Animations respect reduced-motion preference
- [ ] PDF export via print working with proper styling
- [ ] Contact form and booking placeholders created with backend integration comments

---

## Dependencies
- **Requires**: Plan 1, Plan 2, Plan 3 (all sections implemented)

## Estimated Effort
- 3-4 days
