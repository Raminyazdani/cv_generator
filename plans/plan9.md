# Plan 9: Enhanced UI Features - Part C (Phase 6, Tasks 6.13-6.20)

## Goal
Implement advanced UI components including morphing navigation, page corner effects, skill tooltips, micro-feedback system, sound effects, card design system, and skeleton loading screens.

## Scope
This plan covers:
- Task 6.13: Morphing Navigation Menu
- Task 6.14: Page Corner Curl Effect
- Task 6.15: Skill Hover Tooltips & Previews
- Task 6.16: Micro-Feedback & Success Animations
- Task 6.17: Sound Effects (Optional)
- Task 6.18: Advanced Typography (Variable Fonts)
- Task 6.19: Card Design System
- Task 6.20: Skeleton Loading Screens

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

### Task 6.13: Morphing Navigation Menu

**Acceptance Criteria**:
- [ ] Navigation bar morphs shape based on scroll position
- [ ] At top: full-width, transparent background
- [ ] After scrolling: compact, solid background with shadow
- [ ] Smooth transition between states (300ms)
- [ ] Logo scales down when compact
- [ ] Navigation items may hide into hamburger on compact mode
- [ ] Respect `prefers-reduced-motion`

**Verification Checks**:
- At page top - navigation is full-width and transparent
- Scroll down - navigation morphs to compact with shadow
- Scroll back up - morphs back to full-width
- Transition is smooth, no jumps
- Logo scales appropriately

### Task 6.14: Page Corner Curl Effect

**Acceptance Criteria**:
- [ ] Create subtle page corner curl effect in bottom-right corner
- [ ] Reveals a hint of "page behind" effect
- [ ] Hover interaction: curl increases slightly
- [ ] Click interaction: could trigger PDF download or navigation
- [ ] CSS-only or minimal JS implementation
- [ ] Disable on mobile (too small for effect)

**Verification Checks**:
- Visual corner curl visible in bottom-right
- Hover over corner - curl increases
- Click corner - action triggers (if implemented)
- Mobile view - corner effect hidden

### Task 6.15: Skill Hover Tooltips & Previews

**Acceptance Criteria**:
- [ ] Hover over skill badge reveals detailed tooltip
- [ ] Tooltip content: full skill name, proficiency level, years of experience (if available)
- [ ] Tooltip positioning: appears above/below based on available space
- [ ] Smooth fade-in animation (150ms)
- [ ] Keyboard accessible: focus reveals tooltip
- [ ] Dismiss on click outside or ESC
- [ ] Mobile: long-press to reveal tooltip

**Verification Checks**:
- Hover over skill badge - tooltip appears with details
- Tooltip positioned correctly (not cut off by viewport)
- Tab to skill - tooltip appears on focus
- Press ESC - tooltip dismisses
- Mobile long-press works

### Task 6.16: Micro-Feedback & Success Animations

**Acceptance Criteria**:
- [ ] Success checkmark animation when form submitted
- [ ] Copied to clipboard animation (checkmark or tick)
- [ ] Error shake animation for invalid inputs
- [ ] Loading spinner for async operations
- [ ] Heart/star animation for "like" actions (if applicable)
- [ ] All animations brief (200-400ms)
- [ ] Respect `prefers-reduced-motion`

**Verification Checks**:
- Submit form - success animation plays
- Copy URL - copied animation plays
- Enter invalid input - shake animation on field
- Async operation - spinner visible until complete
- Test `prefers-reduced-motion` - simplified or no animations

### Task 6.17: Sound Effects (Optional)

**Acceptance Criteria**:
- [ ] Add optional sound effects system
- [ ] Default: muted (user must opt-in)
- [ ] Sounds for: button clicks, theme switch, navigation, success/error
- [ ] Volume control in settings
- [ ] Use Web Audio API for low-latency playback
- [ ] Sounds are subtle, not annoying
- [ ] Mute button easily accessible

**Verification Checks**:
- By default, no sounds play
- Enable sounds in settings - sounds play on interactions
- Volume control adjusts sound level
- Mute button silences all sounds
- Sounds don't interfere with screen readers

### Task 6.18: Advanced Typography (Variable Fonts)

**Acceptance Criteria**:
- [ ] Use variable font for main typography
- [ ] Weight range: 300-700 (light to bold)
- [ ] Width axis for responsive typography (if available)
- [ ] Smooth weight transitions on hover (headings)
- [ ] Optimal font loading strategy (font-display: swap + preload)
- [ ] Fallback to system fonts if variable font fails
- [ ] Different optical sizes for headings vs body

**Verification Checks**:
- Fonts load without FOUT (flash of unstyled text)
- Hover over heading - weight transition smooth
- Check font-feature-settings applied (ligatures, etc.)
- Verify fallback fonts work if web fonts blocked

### Task 6.19: Card Design System

**Acceptance Criteria**:
- [ ] Create unified card component system
- [ ] Card variants: default, elevated, outlined, interactive
- [ ] Consistent padding, border-radius, shadows across all cards
- [ ] Card states: default, hover, active, disabled
- [ ] Cards adapt to theme colors
- [ ] Responsive card grid layouts
- [ ] Card components: CardHeader, CardBody, CardFooter, CardMedia

**Verification Checks**:
- All sections using consistent card design
- Cards have appropriate hover states
- Theme switch - cards adapt colors correctly
- Cards responsive on mobile
- Card components compose properly

### Task 6.20: Skeleton Loading Screens

**Acceptance Criteria**:
- [ ] Create skeleton placeholder components for all sections
- [ ] Skeleton mirrors actual content structure
- [ ] Animated shimmer effect (moving gradient)
- [ ] Show skeleton while data loading (simulated or real)
- [ ] Graceful transition from skeleton to content
- [ ] Respect `prefers-reduced-motion` - static gray instead of shimmer

**Verification Checks**:
- Simulate slow load - skeleton screens appear
- Skeleton structure matches actual content layout
- Shimmer animation visible and smooth
- Content fades in smoothly after load
- Test `prefers-reduced-motion` - no shimmer animation

---

## Success Criteria

- [ ] Morphing navigation working on scroll
- [ ] Page corner curl effect (desktop only)
- [ ] Skill tooltips with detailed information
- [ ] Micro-feedback animations for user actions
- [ ] Sound effects system (optional, opt-in)
- [ ] Variable fonts with smooth weight transitions
- [ ] Unified card design system
- [ ] Skeleton loading screens for all sections

---

## Dependencies
- **Requires**: Plan 1-8 (core MVP and Enhanced UI Parts A & B)

## Estimated Effort
- 8-10 days
