# Plan 14: Production Infrastructure - Part B (Phase 8, Tasks 8.9-8.15)

## Goal
Complete production infrastructure with browser compatibility, automated testing, CI/CD pipeline, monitoring dashboard, legal compliance, performance budgets, and graceful degradation.

## Scope
This plan covers:
- Task 8.9: Browser Compatibility & Polyfills
- Task 8.10: Automated Testing Infrastructure
- Task 8.11: Continuous Integration & Deployment Pipeline
- Task 8.12: Monitoring Dashboard & Alerting
- Task 8.13: Legal Pages & Compliance
- Task 8.14: Performance Budget & Monitoring
- Task 8.15: Graceful Degradation & Fallback Strategies

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

### Task 8.9: Browser Compatibility & Polyfills

**Acceptance Criteria**:
- [ ] Define browser support matrix:
  - Chrome/Edge: last 2 versions
  - Firefox: last 2 versions
  - Safari: last 2 versions
  - iOS Safari: last 2 versions
  - Android Chrome: last 2 versions
- [ ] Add necessary polyfills:
  - `core-js` for ES6+ features
  - Intersection Observer polyfill
  - ResizeObserver polyfill
  - CSS custom properties fallback (for old browsers)
- [ ] Graceful degradation strategy:
  - Advanced animations: fallback to simple transitions
  - CSS Grid: fallback to Flexbox
  - Custom fonts: fallback to system fonts
- [ ] Add browserslist config
- [ ] Display warning for unsupported browsers

**Verification Checks**:
- Test on Chrome, Firefox, Safari, Edge - all work
- Test on mobile browsers - functional
- CSS Grid areas work or fallback to Flexbox
- Animations work or degrade gracefully
- Bundle includes necessary polyfills

### Task 8.10: Automated Testing Infrastructure

**Acceptance Criteria**:
- [ ] Unit testing setup (Jest + React Testing Library)
- [ ] Component tests for all major components
- [ ] Utility function tests
- [ ] E2E tests (Playwright or Cypress):
  - Homepage loads
  - Navigation works
  - Language switching
  - Theme switching
  - Filter applies correctly
  - PDF export triggers
  - Contact form validation
  - Mobile responsive
- [ ] Test coverage reports (aim for > 80%)
- [ ] Accessibility tests (axe-core)

**Test Example**:
```typescript
describe('LanguageSwitch', () => {
  it('switches content when language changed', () => {
    render(<App />);
    const langButton = screen.getByRole('button', { name: /language/i });
    fireEvent.click(langButton);
    fireEvent.click(screen.getByText('Deutsch'));
    expect(screen.getByText(/Bildung/)).toBeInTheDocument();
  });
});
```

**Verification Checks**:
- Run `npm test` - all tests pass
- Test coverage report generated
- Coverage > 80% for critical components
- E2E tests cover main user journeys

### Task 8.11: Continuous Integration & Deployment Pipeline

**Acceptance Criteria**:
- [ ] CI/CD platform setup (GitHub Actions recommended)
- [ ] Pipeline stages:
  1. Lint: ESLint, Prettier, TypeScript check
  2. Test: Run all unit/integration tests
  3. Build: Production build
  4. Security: Dependency audit
  5. Deploy: Deploy to staging/production
- [ ] Automated testing on pull requests
- [ ] Branch protection rules (require PR reviews, tests pass)
- [ ] Automated deployment:
  - `main` branch → production
  - `develop` branch → staging
  - Feature branches → preview deployments
- [ ] Deployment notifications
- [ ] Build artifact caching for speed

**GitHub Actions Example**:
```yaml
name: CI/CD Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build
  
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: npm run deploy
```

**Verification Checks**:
- Push to branch - CI pipeline triggers
- Lint errors - pipeline fails
- Test failures - pipeline fails
- Push to main - auto-deploys to production
- Open PR - preview deployment created

### Task 8.12: Monitoring Dashboard & Alerting

**Acceptance Criteria**:
- [ ] Monitoring dashboard (placeholder/configuration)
- [ ] Metrics tracked:
  - Performance: Load time, TTFB, Core Web Vitals
  - Errors: Error rate, error types
  - Traffic: Page views, unique visitors
  - User behavior: Bounce rate, time on site
- [ ] Alert configurations:
  - Error rate spike
  - Performance degradation
  - Site downtime
- [ ] Incident response playbook document

**Verification Checks**:
- Dashboard shows real-time metrics (if configured)
- Trigger error - alert would be received
- Historical data available for analysis
- Alert thresholds documented

### Task 8.13: Legal Pages & Compliance

**Acceptance Criteria**:
- [ ] Create legal pages:
  - Privacy Policy: Data collection, usage, storage, rights
  - Terms of Service: Usage terms, disclaimers
  - Cookie Policy: What cookies used, why, how to disable
  - Accessibility Statement: WCAG compliance level, known issues
- [ ] Cookie consent banner (if using tracking cookies)
- [ ] Easy access to legal pages (footer links)
- [ ] Contact information for privacy concerns
- [ ] Analytics opt-out option
- [ ] Regular compliance audit checklist

**Verification Checks**:
- Privacy policy accessible from footer
- Cookie banner appears (if needed)
- Accept/decline cookies works
- Analytics opt-out functional
- Privacy policy up to date

### Task 8.14: Performance Budget & Monitoring

**Acceptance Criteria**:
- [ ] Define performance budgets:
  - Initial bundle: < 200KB (gzipped)
  - Total page weight: < 2MB
  - First Contentful Paint: < 1.5s
  - Time to Interactive: < 3.5s
  - Largest Contentful Paint: < 2.5s
  - Cumulative Layout Shift: < 0.1
  - First Input Delay: < 100ms
- [ ] Lighthouse CI integration
- [ ] Bundle size monitoring (bundlesize, size-limit)
- [ ] Fail CI if budgets exceeded
- [ ] Webpack bundle analyzer
- [ ] Image optimization automation
- [ ] Critical CSS extraction

**Verification Checks**:
- Run `npm run size` - within budget
- Add large dependency - size check fails
- Lighthouse CI runs on PR
- Performance scores meet targets
- Bundle analyzer shows chunk sizes

### Task 8.15: Graceful Degradation & Fallback Strategies

**Acceptance Criteria**:
- [ ] Feature detection:
  - JavaScript disabled: Show message
  - Cookies disabled: Show warning
  - LocalStorage unavailable: Use in-memory fallback
  - Service Worker not supported: Skip PWA features
- [ ] Network failure handling:
  - Offline banner
  - Retry mechanism
  - Show cached content
- [ ] Third-party failures:
  - Analytics fails: Continue without tracking
  - Font loading fails: Use system fonts
- [ ] Error boundaries around risky components
- [ ] Timeout limits for all async operations
- [ ] Fallback UI for broken images

**No-JavaScript Fallback**:
```html
<noscript>
  <div class="no-js-warning">
    <h1>JavaScript Required</h1>
    <p>This site requires JavaScript to function properly. 
       Please enable JavaScript in your browser settings.</p>
  </div>
</noscript>
```

**Verification Checks**:
- Disable JavaScript - warning message shows
- Go offline - offline banner appears
- Block external domain - site still works
- Font fails to load - system font used
- Break image URL - fallback icon shows
- Error boundary catches component errors

---

## Success Criteria

- [ ] Browser compatibility across all target browsers
- [ ] Automated testing with > 80% coverage
- [ ] CI/CD pipeline running on all commits
- [ ] Monitoring and alerting configured
- [ ] Legal pages and compliance complete
- [ ] Performance budgets enforced
- [ ] Graceful degradation for all failure modes

---

## Dependencies
- **Requires**: Plan 1-13 (all features and infrastructure Part A)

## Estimated Effort
- 12-15 days
