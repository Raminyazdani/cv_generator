# Plan 13: Production Infrastructure - Part A (Phase 8, Tasks 8.1-8.8)

## Goal
Build production-ready infrastructure including error pages, loading states, environment configuration, security headers, logging, caching, URL management, and data validation.

## Scope
This plan covers:
- Task 8.1: Error Pages & Navigation Edge Cases
- Task 8.2: Loading States & Lazy Loading Strategy
- Task 8.3: Environment Configuration & Build Profiles
- Task 8.4: Security Headers & Content Security Policy
- Task 8.5: Logging & Debugging Infrastructure
- Task 8.6: Cache Management & Service Worker Strategy
- Task 8.7: URL Management & Deep Linking
- Task 8.8: Data Validation & Schema Enforcement

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

### Task 8.1: Error Pages & Navigation Edge Cases

**Acceptance Criteria**:
- [ ] Create `src/pages/NotFound404.tsx` for 404 errors
- [ ] Create `src/pages/Error500.tsx` for server errors
- [ ] Create `src/pages/OfflinePage.tsx` for offline state
- [ ] Create `src/pages/Maintenance.tsx` for maintenance mode
- [ ] 404 page features:
  - User-friendly message ("Page not found")
  - Links to main sections
  - "Back to Home" button
  - Match site theme and language
- [ ] Handle invalid routes gracefully
- [ ] Handle hash/anchor navigation failures

**Verification Checks**:
- Navigate to `/invalid-route` - 404 page displays
- 404 page matches current theme
- Switch language - 404 page text updates
- Click "Back to Home" - navigates to home
- All error pages keyboard accessible

### Task 8.2: Loading States & Lazy Loading Strategy

**Acceptance Criteria**:
- [ ] Create global loading indicator component
- [ ] Route-based code splitting (React.lazy + Suspense)
- [ ] Component-level lazy loading for heavy sections
- [ ] Image lazy loading with intersection observer
- [ ] Loading states:
  - Initial app load (splash screen)
  - Route transitions
  - Image loading (blur-up effect)
  - Section reveal on scroll
- [ ] Timeout handling (show error after X seconds)
- [ ] Preload critical resources

**Verification Checks**:
- Check Network tab - chunks loaded on demand
- Navigate between sections - smooth transitions
- Slow 3G simulation - loading states appear
- Images load progressively with blur-up
- Initial bundle size < 200KB gzipped

### Task 8.3: Environment Configuration & Build Profiles

**Acceptance Criteria**:
- [ ] Create `.env.example` template file
- [ ] Environment variables for:
  - `REACT_APP_API_URL` (if backend exists)
  - `REACT_APP_ANALYTICS_ID`
  - `REACT_APP_ENV` (dev/staging/prod)
  - Feature flags (enable/disable features)
- [ ] Build profiles:
  - Development: source maps, hot reload, verbose logging
  - Staging: optimized but with debugging tools
  - Production: fully optimized, minimal logging
- [ ] Never commit `.env` files (add to `.gitignore`)
- [ ] Add env var validation on app startup

**Verification Checks**:
- `.env.example` exists with all variables
- Real `.env` files not in git (check .gitignore)
- Build succeeds with missing optional vars
- Environment displayed in console (dev only)
- Feature flags toggle features correctly

### Task 8.4: Security Headers & Content Security Policy

**Acceptance Criteria**:
- [ ] Content Security Policy (CSP):
  - Define allowed sources for scripts, styles, images, fonts
  - Block inline scripts (or use nonces)
- [ ] Security headers (via meta tags if no server):
  - `X-Frame-Options: DENY` (prevent clickjacking)
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] HTTPS enforcement recommendation (server-side)
- [ ] Subresource Integrity (SRI) for external scripts
- [ ] Regular dependency security audits (`npm audit`)

**Verification Checks**:
- CSP violations logged (if any)
- Site works with CSP enabled
- External resources load correctly
- Run `npm audit` - no high/critical vulnerabilities
- Mixed content warnings: 0

### Task 8.5: Logging & Debugging Infrastructure

**Acceptance Criteria**:
- [ ] Create `src/utils/logger.ts` utility
- [ ] Log levels: DEBUG, INFO, WARN, ERROR
- [ ] Development: verbose console logging with colors
- [ ] Production: minimal logging, errors to monitoring
- [ ] Structured log format with timestamp, level, message, context
- [ ] Log filtering by level/category
- [ ] Performance logging (timing operations)
- [ ] Sensitive data redaction (emails, tokens)
- [ ] Debug mode toggle (localStorage flag)

**Verification Checks**:
- Dev mode: console shows detailed logs
- Prod mode: only errors logged
- Enable debug mode - verbose logs appear
- Check logs - no sensitive data exposed
- Performance logs show operation timings

### Task 8.6: Cache Management & Service Worker Strategy

**Acceptance Criteria**:
- [ ] Service worker caching strategies:
  - Cache-First: Static assets (CSS, JS, images, fonts)
  - Network-First: JSON data files (CV content)
  - Stale-While-Revalidate: Non-critical assets
  - Network-Only: Analytics, tracking
- [ ] Cache versioning (invalidate on deploy)
- [ ] Cache size limits
- [ ] Clear old caches automatically
- [ ] Precache critical assets on install
- [ ] localStorage for settings (theme, language)
- [ ] Clear cache option in UI (dev tools)

**Verification Checks**:
- Go offline - site still loads (cached assets)
- Check Application tab - caches populated
- Deploy new version - old caches cleared
- JSON data updates - fetch from network
- Clear cache button works

### Task 8.7: URL Management & Deep Linking

**Acceptance Criteria**:
- [ ] URL structure:
  - `/` - Home (hero)
  - `/#section-name` - Anchor to section
  - `/?lang=de` - Language selection
  - `/?theme=dark` - Theme selection
  - `/?focus=Programming` - Filter state
  - `/?project=project-slug` - Specific project expanded
- [ ] Parse URL parameters on load
- [ ] Update URL on state changes (language, theme, filter)
- [ ] Browser back/forward buttons work correctly
- [ ] Sharable URLs: copy current state to clipboard
- [ ] Scroll to section on hash change
- [ ] Restore scroll position on back button

**Verification Checks**:
- Open URL with query params - state restored
- Change language - URL updates with `?lang=`
- Change theme - URL updates with `?theme=`
- Browser back button - previous state restored
- Share URL with friend - they see same state
- Hash links scroll to correct section

### Task 8.8: Data Validation & Schema Enforcement

**Acceptance Criteria**:
- [ ] Create JSON schema definitions (using Zod or similar)
- [ ] Validate JSON data on load:
  - Required fields present
  - Data types correct
  - Date formats valid
  - URLs properly formatted
  - Email addresses valid
- [ ] Graceful degradation on validation errors
- [ ] Log validation warnings in development
- [ ] Show fallback UI for invalid data
- [ ] Type guards in TypeScript
- [ ] Unit tests for validation logic

**Verification Checks**:
- Load invalid JSON - validation errors logged
- Invalid date format - fallback displayed
- Missing required field - doesn't crash
- Dev mode: validation warnings in console
- Prod mode: graceful fallback, error logged

---

## Success Criteria

- [ ] Error pages working for all error types
- [ ] Loading states and lazy loading functioning
- [ ] Environment configuration set up
- [ ] Security headers and CSP configured
- [ ] Logging infrastructure in place
- [ ] Caching strategy implemented
- [ ] Deep linking and URL management working
- [ ] Data validation preventing crashes

---

## Dependencies
- **Requires**: Plan 1-12 (all features implemented)

## Estimated Effort
- 12-15 days
