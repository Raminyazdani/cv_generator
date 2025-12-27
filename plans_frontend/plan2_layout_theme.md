# Plan 2: Core Layout & Theme System (Phase 1)

## Goal
Implement the foundational layout system including theme switching with 6 presets, RTL support for Farsi, sticky header with navigation controls, and footer component.

## Scope
This plan covers:
- Task 1.1: Implement Theme System with CSS Custom Properties
- Task 1.2: Implement RTL Support for Farsi
- Task 1.3: Build Sticky Header with Navigation
- Task 1.4: Build Footer Component

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

### Task 1.1: Implement Theme System with CSS Custom Properties

**Acceptance Criteria**:
- [ ] Create `src/styles/themes.css` with CSS custom properties
- [ ] Define 6 theme presets: Normal, Academic, Apple-like, Dark, Bright, Futuristic
- [ ] Each theme defines: `--primary`, `--secondary`, `--background`, `--surface`, `--text-primary`, `--text-secondary`, `--accent`, `--border`, `--shadow`
- [ ] Theme applied via `data-theme` attribute on root element
- [ ] Create `src/utils/themeManager.ts` to switch themes
- [ ] Save theme preference to localStorage
- [ ] Academic theme uses serif fonts, others use sans-serif

**Verification Checks**:
- Toggle through all 6 themes - visual changes confirm
- Check DevTools: root element has `data-theme` attribute changing
- Refresh page - theme persists from localStorage
- Verify Academic theme uses `font-family: Georgia, serif`
- Dark theme has `--background` darker than `--text-primary` (contrast check)

### Task 1.2: Implement RTL Support for Farsi

**Acceptance Criteria**:
- [ ] Detect language and set `dir="rtl"` on HTML root for FA
- [ ] Create `src/styles/rtl.css` with RTL-specific rules
- [ ] Flip margins, paddings, text-align for RTL
- [ ] Mirror icons/arrows that indicate direction
- [ ] Test all sections render correctly in RTL
- [ ] Logical properties: use `inline-start`, `inline-end` instead of left/right where possible

**Verification Checks**:
- Switch to FA language - inspect HTML root has `dir="rtl"` and `lang="fa"`
- Header navigation aligns right
- Profile photo appears on right side in RTL
- Text alignment is right for paragraphs
- Check skills section: categories flow right-to-left
- Verify no layout breakage (overlaps, cutoffs)

### Task 1.3: Build Sticky Header with Navigation

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

**Verification Checks**:
- Scroll page - header stays visible at top
- Click nav link - smooth scroll to section occurs
- Change language - verify content changes (check section headings)
- Change theme - verify colors change immediately
- Resize to mobile - hamburger menu appears
- Tab through header - all interactive elements receive focus indicators
- Press Esc on open dropdown - dropdown closes

### Task 1.4: Build Footer Component

**Acceptance Criteria**:
- [ ] Create `src/components/Footer.tsx`
- [ ] Display copyright with current year
- [ ] PDF Export button (onClick triggers print dialog for now)
- [ ] Render social links from `profiles` JSON data
- [ ] Responsive layout (stack on mobile)
- [ ] Consistent theme styling

**Verification Checks**:
- Footer appears at bottom of page
- Click PDF Export - browser print dialog opens
- Social links are clickable and open in new tab
- Verify links match `profiles` array URLs from JSON
- Resize to mobile - footer content stacks vertically

---

## Success Criteria

- [ ] All 6 themes switching correctly with visual confirmation
- [ ] RTL layout working correctly for Farsi language
- [ ] Sticky header with all dropdowns functional
- [ ] Language switching loads correct JSON data
- [ ] Footer rendering with social links from JSON
- [ ] Mobile responsive layout working
- [ ] All keyboard accessibility requirements met

---

## Dependencies
- **Requires**: Plan 1 (Project Setup & Foundation)

## Estimated Effort
- 2-3 days
