# Plan 7: Enhanced UI Features - Part A (Phase 6, Tasks 6.1-6.6)

## Goal
Add premium UI/UX features including 3D language carousel, interactive button effects, parallax scrolling, skills carousel, project gallery with lightbox, and animated timeline visualization.

## Scope
This plan covers:
- Task 6.1: Language Selector Carousel with 3D Card Effect
- Task 6.2: Premium Button & Interactive Elements System
- Task 6.3: Parallax Scrolling & Depth Effects
- Task 6.4: Skills Section Interactive Carousel/Slider
- Task 6.5: Projects Gallery with Lightbox Carousel
- Task 6.6: Timeline Visualization with Animated Progress

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

### Task 6.1: Language Selector Carousel with 3D Card Effect

**Acceptance Criteria**:
- [ ] Create `src/components/LanguageCarousel.tsx` component
- [ ] Display 3 language cards simultaneously (EN, DE, FA)
- [ ] Apply 3D transform effect: focused/selected card is larger and closer (z-axis forward)
- [ ] Non-selected cards positioned behind on left and right with reduced scale and opacity
- [ ] Smooth transition animations (300-500ms)
- [ ] Cards clickable to select language
- [ ] Keyboard navigation: Arrow keys to cycle, Enter to select
- [ ] Touch/swipe support for mobile
- [ ] Respect `prefers-reduced-motion` - disable 3D transforms, use simple fade

**Verification Checks**:
- Visual inspection: three cards visible simultaneously
- Click background card - it moves to center/foreground
- Press arrow keys - carousel cycles smoothly
- On mobile: swipe left/right works
- Check `prefers-reduced-motion: reduce` - 3D effects disabled
- Selected language triggers actual language switch

### Task 6.2: Premium Button & Interactive Elements System

**Acceptance Criteria**:
- [ ] Create `src/styles/interactions.css` with reusable interaction patterns
- [ ] Button hover states: scale (1.05x), shadow elevation, color shift
- [ ] Add magnetic button effect: buttons slightly follow cursor when nearby (subtle, < 10px)
- [ ] Implement ripple effect on click
- [ ] Smooth transitions (150ms ease-out)
- [ ] Focus-visible styles with animated border or glow
- [ ] Disabled state styling (reduced opacity, no-cursor)
- [ ] Loading state animation (spinner or pulsing)
- [ ] Active press-down effect (scale 0.95x)
- [ ] Respect `prefers-reduced-motion`

**Verification Checks**:
- Hover over any button - smooth scale and shadow animation
- Click button - ripple effect emanates from click point
- Tab to button - focus indicator animates in smoothly
- Verify disabled buttons have no hover effects
- Test with `prefers-reduced-motion: reduce`

### Task 6.3: Parallax Scrolling & Depth Effects

**Acceptance Criteria**:
- [ ] Implement parallax effect on hero cover image (scrolls slower than content)
- [ ] Create depth layers: background (0.3x speed), mid-ground (0.6x speed), foreground (1x speed)
- [ ] Keep effects subtle (max 30% speed difference) to avoid motion sickness
- [ ] Use `transform: translateY()` with `will-change` for performance
- [ ] Implement via Intersection Observer + requestAnimationFrame
- [ ] Disable parallax on mobile (performance concern)
- [ ] Respect `prefers-reduced-motion: reduce`

**Verification Checks**:
- Scroll page - hero cover image moves slower than content
- Verify performance: scrolling is smooth, no jank
- Check mobile - parallax disabled, normal scrolling
- Test `prefers-reduced-motion: reduce` - parallax disabled

### Task 6.4: Skills Section Interactive Carousel/Slider

**Acceptance Criteria**:
- [ ] Create carousel for skill categories
- [ ] Display 1-3 categories at a time depending on screen size
- [ ] Navigation arrows with smooth slide animations
- [ ] Dot indicators at bottom showing current position
- [ ] Swipe gestures on mobile/tablet
- [ ] Keyboard navigation: Arrow keys to navigate
- [ ] Each category card shows title and skill items
- [ ] Smooth easing function for transitions (cubic-bezier)

**Verification Checks**:
- Click next arrow - carousel slides smoothly
- Swipe left on mobile - carousel advances
- Click dot indicator - jumps to that category
- Verify responsive: 1 card on mobile, 2 on tablet, 3 on desktop
- Check transition is smooth (300-500ms cubic-bezier easing)

### Task 6.5: Projects Gallery with Lightbox Carousel

**Acceptance Criteria**:
- [ ] Display projects as grid of cards with thumbnails
- [ ] Hover effect: card lifts, shows overlay with title and description
- [ ] Click on project card opens lightbox modal
- [ ] Lightbox includes image carousel if multiple images
- [ ] Arrow keys navigate between projects in lightbox
- [ ] Close button, ESC key, click outside closes lightbox
- [ ] Filter/sort controls above gallery
- [ ] Animate grid layout changes when filtering

**Verification Checks**:
- Hover over project card - card lifts and overlay appears
- Click project card - lightbox opens
- Press arrow keys in lightbox - navigate between projects
- Press ESC - lightbox closes
- Filter projects - grid animates layout changes
- Verify focus trap in lightbox

### Task 6.6: Timeline Visualization with Animated Progress

**Acceptance Criteria**:
- [ ] Create `src/components/Timeline.tsx` component
- [ ] Vertical line connecting all timeline entries
- [ ] Animated dots/nodes at each entry point
- [ ] Progress bar fills as user scrolls down
- [ ] Timeline animates in from left/right as it enters viewport
- [ ] Entries stagger with fade + slide animation (200ms delay between items)
- [ ] Hover over entry: highlight with color, slight scale
- [ ] Active entry indicator based on scroll position

**Verification Checks**:
- Scroll to timeline section - line draws from top to bottom
- Verify entries fade and slide in with stagger effect
- Scroll through timeline - progress indicator fills dynamically
- Hover over entry - highlight animation occurs
- Test `prefers-reduced-motion` - no animation, all content visible

---

## Success Criteria

- [ ] 3D language carousel working with smooth transitions
- [ ] Interactive button effects across all buttons
- [ ] Parallax scrolling on hero (disabled on mobile)
- [ ] Skills carousel navigable with keyboard and touch
- [ ] Projects gallery with functional lightbox
- [ ] Timeline visualization with scroll-triggered animations
- [ ] All animations respect `prefers-reduced-motion`

---

## Dependencies
- **Requires**: Plan 1-6 (core MVP complete)

## Estimated Effort
- 8-10 days
