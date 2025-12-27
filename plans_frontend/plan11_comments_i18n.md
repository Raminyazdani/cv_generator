# Plan 12: Advanced Features - Comments, A/B Testing, i18n, Monitoring (Phase 7, Tasks 7.11-7.15)

## Goal
Implement enterprise-grade features including commenting system, A/B testing framework, full internationalization, performance monitoring, and advanced print stylesheet.

## Scope
This plan covers:
- Task 7.11: Real-time Collaboration & Comments
- Task 7.12: A/B Testing Framework
- Task 7.13: Internationalization (i18n) Beyond Content
- Task 7.14: Performance Monitoring & Error Tracking
- Task 7.15: Advanced Print Stylesheet & Multi-page PDF

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

### Task 7.11: Real-time Collaboration & Comments

**Note**: This feature requires backend integration. This plan creates the frontend components and defines the API interface.

**Acceptance Criteria**:
- [ ] Add commenting system architecture (options: Disqus, Commento, custom)
- [ ] Comments on projects, publications, articles
- [ ] Create comment UI components
- [ ] Reply to comments (threading)
- [ ] Like/upvote functionality
- [ ] Report inappropriate content button
- [ ] User authentication placeholder (GitHub, Google, email)
- [ ] Markdown support in comments
- [ ] @ mentions support
- [ ] Backend API interface defined with TODO comments

**Verification Checks**:
- Comment form appears on supported sections
- Comment UI renders correctly with mock data
- Reply to comment - nested correctly displayed
- Like button - count increments (mock)
- Markdown in comment renders correctly
- TODO comments for backend integration present

### Task 7.12: A/B Testing Framework

**Acceptance Criteria**:
- [ ] Create `src/utils/abTesting.ts` utility
- [ ] Define experiment structure:
  ```typescript
  {
    experimentId: "hero_layout_v2",
    variants: ["control", "variant_a", "variant_b"],
    traffic: 0.5, // 50% of users
    targeting: { newVisitors: true }
  }
  ```
- [ ] Randomly assign users to variants
- [ ] Persist variant in localStorage (consistent experience)
- [ ] Track variant in analytics
- [ ] Easy component-level variant rendering:
  ```tsx
  <Experiment id="hero_layout_v2">
    <Variant name="control"><HeroV1 /></Variant>
    <Variant name="variant_a"><HeroV2 /></Variant>
  </Experiment>
  ```
- [ ] Admin panel to view experiment results (placeholder)
- [ ] Easy enable/disable experiments

**Verification Checks**:
- User assigned to variant consistently
- Variant tracked in analytics
- Different variants render correctly
- Switch experiment on/off - takes effect immediately
- Clear localStorage - new variant assigned

### Task 7.13: Internationalization (i18n) Beyond Content

**Acceptance Criteria**:
- [ ] Create translation files for UI text (not content):
  - `translations/en.json`
  - `translations/de.json`
  - `translations/fa.json`
- [ ] Translate all UI labels:
  - Button text ("Download", "View More", "Contact")
  - Section headings ("About", "Experience", "Projects")
  - Form labels ("Name", "Email", "Message")
  - Error messages
  - Tooltips and help text
- [ ] Date formatting per locale:
  - EN: "January 15, 2024"
  - DE: "15. Januar 2024"
  - FA: Persian calendar support (optional)
- [ ] Number formatting:
  - EN: "1,234.56"
  - DE: "1.234,56"
  - FA: Persian numerals (optional)
- [ ] Plural rules per language
- [ ] Create `useTranslation` hook for component usage

**Verification Checks**:
- Switch language - all UI text updates
- Dates formatted correctly per locale
- Numbers formatted per locale conventions
- Plurals handled correctly
- No hardcoded English text in components
- RTL languages (FA) - all text flows correctly

### Task 7.14: Performance Monitoring & Error Tracking

**Acceptance Criteria**:
- [ ] Integrate error tracking (Sentry, Rollbar, or similar placeholder)
- [ ] Capture JavaScript errors with stack traces
- [ ] Capture network errors
- [ ] Performance monitoring:
  - Core Web Vitals tracking (LCP, FID, CLS)
  - Custom performance marks
  - Resource loading times
  - API response times (if applicable)
- [ ] Error boundary components
- [ ] Graceful error UI (not just blank page)
- [ ] Retry logic for failed requests
- [ ] User feedback on errors ("Report Problem" button)
- [ ] Source map upload configuration (for production debugging)

**Verification Checks**:
- Trigger error - logged to console (and monitoring service if configured)
- Error boundary catches render errors
- Error UI shows user-friendly message
- Performance metrics visible in console (dev mode)
- User can report problem with context

### Task 7.15: Advanced Print Stylesheet & Multi-page PDF

**Acceptance Criteria**:
- [ ] Create `src/styles/print-advanced.css`
- [ ] Page setup:
  - A4 size with proper margins
  - Header on each page: name + page number
  - Footer on each page: contact info + date
- [ ] Intelligent page breaks:
  - Avoid breaking in middle of entries
  - Keep related content together (orphan/widow control)
  - Section headings always with following content
- [ ] Multi-page optimizations:
  - Table of contents on first page (optional)
  - Section markers for easy navigation
  - Continued indicators ("continued on next page")
- [ ] Print-specific styling:
  - Higher contrast for readability
  - Optimized typography (serif for print)
  - QR code with website URL
  - Simplified color palette
- [ ] Print preview mode in browser

**CSS Techniques**:
```css
@media print {
  @page {
    size: A4;
    margin: 2cm;
    @top-center { content: "Ramin Yazdani - CV"; }
    @bottom-right { content: counter(page); }
  }
  .section-heading { page-break-after: avoid; }
  .card { page-break-inside: avoid; }
}
```

**Verification Checks**:
- Print preview shows professional layout
- Headers/footers on every page
- No awkward page breaks mid-entry
- QR code visible and scannable
- Typography optimized for print
- Save as PDF - result is professional quality

---

## Success Criteria

- [ ] Comment system UI components complete
- [ ] A/B testing framework functional
- [ ] Full i18n for UI labels and formatting
- [ ] Error tracking and monitoring configured
- [ ] Advanced print stylesheet producing professional PDFs

---

## Dependencies
- **Requires**: Plan 1-11 (all previous features)

## Estimated Effort
- 12-15 days
