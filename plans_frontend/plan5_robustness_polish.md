# Plan 5: Robustness & Polish (Phase 4)

## Goal
Ensure the application handles edge cases gracefully, works across all device sizes, meets accessibility standards (WCAG 2.1 AA), performs well, and functions correctly across all major browsers.

## Scope
This plan covers:
- Task 4.1: Handle Missing/Null/Invalid Data
- Task 4.2: Responsive Design Verification
- Task 4.3: Accessibility Audit (WCAG 2.1 AA)
- Task 4.4: Performance Optimization
- Task 4.5: Browser Compatibility Testing

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

### Task 4.1: Handle Missing/Null/Invalid Data

**Acceptance Criteria**:
- [ ] All components check for null/undefined before rendering
- [ ] Use optional chaining (`data?.field`) and nullish coalescing (`?? 'default'`)
- [ ] Invalid dates display as raw string or "Invalid Date" message
- [ ] Missing images fallback to placeholder or skip rendering
- [ ] Empty arrays don't render section headings (or show "No data available")

**Verification Checks**:
- Remove `education` key from JSON - section doesn't crash, shows nothing or "No education data"
- Set a date to invalid value (e.g., "2020-99-99") - no crash, fallback displayed
- Remove `Pictures` from basics - hero section renders without photos
- Set `type_key` to `null` on one entry - entry still renders, just not filtered

### Task 4.2: Responsive Design Verification

**Acceptance Criteria**:
- [ ] Test on mobile (< 640px), tablet (640-1024px), desktop (> 1024px)
- [ ] Header: hamburger menu on mobile, full nav on desktop
- [ ] Hero: stack content vertically on mobile
- [ ] Skills: grid adjusts from 3 columns to 1 column
- [ ] All sections readable and usable on small screens
- [ ] Touch targets minimum 44x44px for mobile

**Verification Checks**:
- Use DevTools device emulation: iPhone SE, iPad, Desktop
- Hamburger menu appears on mobile, works correctly
- No horizontal scroll on any screen size
- Text remains readable (min 14px on mobile)
- Verify touch targets with DevTools touch simulator

### Task 4.3: Accessibility Audit (WCAG 2.1 AA)

**Acceptance Criteria**:
- [ ] All interactive elements keyboard accessible
- [ ] Focus indicators visible on all focusable elements
- [ ] Semantic HTML (nav, main, section, article, footer)
- [ ] Images have alt text (from JSON or fallback)
- [ ] Color contrast ratio ≥ 4.5:1 for normal text, ≥ 3:1 for large text
- [ ] ARIA labels where needed (dropdowns, modals)
- [ ] Screen reader testing (basic): page structure navigable

**Verification Checks**:
- Tab through entire page - no keyboard traps, all elements reachable
- Run axe DevTools or Lighthouse accessibility audit - no critical issues
- Check contrast ratios with browser DevTools or Contrast Checker tool
- Verify modal has `role="dialog"` and `aria-modal="true"`
- Test with VoiceOver (Mac) or NVDA (Windows) - page makes sense

### Task 4.4: Performance Optimization

**Acceptance Criteria**:
- [ ] Lazy load images (use `loading="lazy"` or Intersection Observer)
- [ ] Code splitting for components (React.lazy)
- [ ] Minimize bundle size: check with `npm run build` and analyze
- [ ] Optimize images: suggest compression or responsive images
- [ ] Measure Lighthouse performance score > 90

**Verification Checks**:
- Run `npm run build` - check bundle size (< 500KB initial load target)
- Run Lighthouse in DevTools - Performance score > 90
- Check Network tab: images load progressively
- Verify code-splitting: lazy-loaded components show separate chunks

### Task 4.5: Browser Compatibility Testing

**Acceptance Criteria**:
- [ ] Test on Chrome, Firefox, Safari, Edge (latest versions)
- [ ] Check for CSS compatibility (Grid, Flexbox, Custom Properties)
- [ ] Add autoprefixer if needed
- [ ] Fallbacks for unsupported features

**Verification Checks**:
- Open site in Chrome, Firefox, Safari, Edge - all features work
- Check for console errors in each browser
- Verify CSS custom properties work (themes change)
- Test RTL in all browsers

---

## Success Criteria

- [ ] Application doesn't crash with malformed/incomplete JSON data
- [ ] Responsive layout working on mobile, tablet, and desktop
- [ ] WCAG 2.1 AA compliance (no critical accessibility issues)
- [ ] Lighthouse Performance score > 90
- [ ] Lighthouse Accessibility score ≥ 95 (target 100)
- [ ] Site works correctly in Chrome, Firefox, Safari, Edge

---

## Dependencies
- **Requires**: Plan 1-4 (all core features implemented)

## Estimated Effort
- 2-3 days
