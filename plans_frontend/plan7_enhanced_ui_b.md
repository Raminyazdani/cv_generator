# Plan 8: Enhanced UI Features - Part B (Phase 6, Tasks 6.7-6.12)

## Goal
Add additional premium UI features including custom cursor effects, page transitions, floating action button, theme transition animations, scroll progress indicator, and fun easter egg features.

## Scope
This plan covers:
- Task 6.7: Cursor Follower & Custom Cursor Effects
- Task 6.8: Smooth Page Transitions & Section Reveal Animations
- Task 6.9: Floating Action Button (FAB) with Quick Actions
- Task 6.10: Theme Transition Animations
- Task 6.11: Scroll Progress Indicator
- Task 6.12: Easter Egg: Konami Code Unlockable Theme

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

### Task 6.7: Cursor Follower & Custom Cursor Effects

**Acceptance Criteria**:
- [ ] Create `src/components/CursorFollower.tsx`
- [ ] Custom cursor circle follows mouse position (hidden default cursor)
- [ ] Trailing effect: second larger circle follows with delay (100-150ms)
- [ ] Cursor changes on hover: scale up over links/buttons, change color
- [ ] Blend mode for interesting visual effect (e.g., `mix-blend-mode: difference`)
- [ ] Smooth interpolation using lerp for fluid movement
- [ ] Only active on desktop (hide on mobile/touch devices)
- [ ] Respect `prefers-reduced-motion` - reduce trail effect complexity

**Cursor States**:
- Default: small circle (8px diameter)
- Hover link/button: large circle (32px diameter) with reduced opacity
- Hover text: vertical line cursor for text selection
- Click/active: shrink briefly (6px) then return

**Verification Checks**:
- Move mouse - custom cursor smoothly follows with trail
- Hover over button - cursor scales up to 32px
- Click - cursor briefly shrinks
- Verify trail circle follows with ~100ms delay
- Check on mobile - custom cursor hidden, native cursor visible
- Test performance - no impact on scroll/interaction smoothness

### Task 6.8: Smooth Page Transitions & Section Reveal Animations

**Acceptance Criteria**:
- [ ] Page load animation: fade in from dark with logo/name reveal
- [ ] Stagger section reveals as user scrolls
- [ ] Section entrance styles:
  - Hero: Fade in + scale from 0.95 to 1.0
  - Education/Experience: Slide in from left with fade
  - Skills: Slide in from right with fade
  - Projects: Grid items pop in with stagger (cascade effect)
  - Publications: Fade in from bottom
- [ ] Use Intersection Observer for scroll-triggered animations
- [ ] Each animation: 500ms duration, 100ms stagger between items
- [ ] Animations only trigger once (not on every scroll)
- [ ] Respect `prefers-reduced-motion` - instant appearance, no animation

**Verification Checks**:
- Refresh page - smooth fade in with logo reveal
- Scroll to each section - appropriate entrance animation triggers
- Verify stagger timing between items (100ms)
- Scroll back up and down - animations don't retrigger
- Test `prefers-reduced-motion: reduce` - all content immediately visible

### Task 6.9: Floating Action Button (FAB) with Quick Actions

**Acceptance Criteria**:
- [ ] Create `src/components/FloatingActionButton.tsx`
- [ ] Circular FAB button fixed in bottom-right corner
- [ ] Primary action: "Back to top" (scrolls to page top)
- [ ] Click to expand: reveals 3-4 quick action buttons radially
- [ ] Quick actions: Back to top, Download PDF, Contact, Toggle theme
- [ ] Smooth expand/collapse animation (rotate + scale sub-buttons)
- [ ] FAB hides when at top of page, appears when scrolling down
- [ ] Hover effect: FAB pulses subtly
- [ ] Mobile-friendly: adequate touch target (56x56px)
- [ ] Keyboard accessible: Tab to focus, Enter/Space to activate

**Verification Checks**:
- Scroll down - FAB appears with fade-in animation
- Scroll to top - FAB disappears
- Click FAB - sub-buttons expand radially
- Click "Back to top" - smoothly scrolls to top
- Click "Download PDF" - print dialog opens
- Verify FAB size is adequate for touch (56x56px)
- Tab to FAB - focus indicator visible, Enter activates

### Task 6.10: Theme Transition Animations

**Acceptance Criteria**:
- [ ] Cross-fade animation when changing themes (500ms duration)
- [ ] CSS transitions on all theme-related custom properties
- [ ] Visual feedback during theme switch: brief color wave or gradient sweep
- [ ] Prevent flash of unstyled content (FOUC) during transition
- [ ] Smooth transition for background colors, text colors, borders, shadows
- [ ] Theme preview thumbnails in theme switcher
- [ ] Theme switcher shows current theme with checkmark or highlight
- [ ] Persist theme smoothly: no flash on page reload

**Verification Checks**:
- Switch theme - smooth cross-fade occurs (500ms)
- Verify no jarring color shifts or flashes
- Check all elements transition smoothly
- Open theme switcher - preview thumbnails show each theme's colors
- Current theme clearly highlighted
- Refresh page - theme loads without flash

### Task 6.11: Scroll Progress Indicator

**Acceptance Criteria**:
- [ ] Horizontal progress bar at top of page (fixed position)
- [ ] Bar fills from left to right as user scrolls down
- [ ] Calculate progress: `scrollTop / (scrollHeight - clientHeight)`
- [ ] Smooth animation using CSS transition or requestAnimationFrame
- [ ] Color matches current theme's primary color
- [ ] Minimal height (2-3px) to avoid being intrusive
- [ ] Subtle glow effect on progress bar
- [ ] Optional: section markers on progress bar (dots indicating section boundaries)

**Verification Checks**:
- Scroll down - progress bar fills proportionally
- Scroll to bottom - progress bar reaches 100%
- Verify smooth animation (no jank)
- Check color matches theme primary color
- Switch theme - progress bar color updates

### Task 6.12: Easter Egg: Konami Code Unlockable Theme

**Acceptance Criteria**:
- [ ] Detect Konami code sequence: ↑ ↑ ↓ ↓ ← → ← → B A
- [ ] On successful entry: unlock "Secret" theme (e.g., retro, neon, matrix style)
- [ ] Show brief celebration animation (confetti, particles, or screen flash)
- [ ] Add "Secret" theme to theme switcher after unlock
- [ ] Persist unlock state in localStorage
- [ ] Add subtle hint in footer: "Try the Konami code 🎮"
- [ ] Ensure doesn't interfere with normal keyboard navigation
- [ ] Make it fun but professional

**Verification Checks**:
- Enter Konami code - celebration animation plays
- Secret theme appears in theme switcher
- Select Secret theme - unique styling applied
- Refresh page - unlock state persists
- Find hint in footer
- Verify normal keyboard navigation still works

---

## Success Criteria

- [ ] Custom cursor following mouse on desktop
- [ ] Page load and section reveal animations working
- [ ] FAB with expandable quick actions
- [ ] Smooth theme transitions
- [ ] Scroll progress indicator
- [ ] Easter egg Konami code working
- [ ] All features respect `prefers-reduced-motion`

---

## Dependencies
- **Requires**: Plan 1-7 (core MVP and Part A of Enhanced UI)

## Estimated Effort
- 6-8 days
