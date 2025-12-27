# Plan 11: Advanced Features - Download, Blog, Video, Accessibility (Phase 7, Tasks 7.6-7.10)

## Goal
Implement advanced content and accessibility features including multiple download formats, blog/articles section, video integration, enhanced accessibility, and Progressive Web App capabilities.

## Scope
This plan covers:
- Task 7.6: Interactive Resume/CV Download Options
- Task 7.7: Blog/Articles Section Integration
- Task 7.8: Video Introduction & Media Embeds
- Task 7.9: Accessibility Enhancements & ARIA Live Regions
- Task 7.10: Progressive Web App (PWA) Features

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

### Task 7.6: Interactive Resume/CV Download Options

**Acceptance Criteria**:
- [ ] Create `src/components/DownloadModal.tsx`
- [ ] Download format options:
  - PDF (Browser Print) - current implementation
  - PDF (API-generated) - LaTeX-based, professional formatting (backend seam)
  - Word/DOCX - for recruiters
  - JSON - raw data export
  - Markdown - plain text readable format
- [ ] Customization options before download:
  - Select sections to include
  - Choose theme/style for PDF
  - Apply focus filter to downloaded content
  - Include/exclude contact information
  - Include/exclude references
- [ ] Preview before download
- [ ] Generate public shareable link (short URL seam)
- [ ] Track download analytics

**Verification Checks**:
- Click download - modal opens with options
- Select PDF format - downloads correctly
- Customize sections - preview updates
- Download JSON - valid file with correct data
- Track downloads in analytics

### Task 7.7: Blog/Articles Section Integration

**Acceptance Criteria**:
- [ ] Add `articles` to JSON schema with fields:
  - `title`, `slug`, `summary`, `content`
  - `coverImage`, `publishDate`, `readTime`
  - `tags`, `external`, `externalURL`
  - `views`, `featured`, `type_key`
- [ ] Create `src/components/ArticlesSection.tsx`
- [ ] Grid layout with article cards
- [ ] Card shows: cover image, title, summary, date, read time, tags
- [ ] Click internal article: opens modal or sub-page
- [ ] Click external article: opens in new tab
- [ ] Featured articles highlighted
- [ ] Sort by date/views/featured
- [ ] Search/filter by tags
- [ ] Markdown rendering for article content
- [ ] Social share buttons on articles

**Verification Checks**:
- Articles display in grid layout
- Click internal article - content renders
- Click external article - opens in new tab
- Featured articles visually distinct
- Filter by tag - relevant articles show
- Markdown content renders correctly

### Task 7.8: Video Introduction & Media Embeds

**Acceptance Criteria**:
- [ ] Extend JSON to support video fields:
  - `videoIntro` - YouTube/Vimeo URL or direct MP4
  - `videoTestimonials` - array of video testimonials
  - `mediaGallery` - mixed media gallery
- [ ] Create `src/components/VideoPlayer.tsx`
- [ ] Hero section: optional video introduction with play button overlay
- [ ] Lazy load videos (only load when user clicks play)
- [ ] Support YouTube, Vimeo, and direct video files
- [ ] Video controls: play/pause, mute, fullscreen
- [ ] Custom video player UI matching site theme
- [ ] Thumbnail/poster image before play
- [ ] Accessibility: captions support, keyboard controls

**Verification Checks**:
- Video introduction appears in hero with play button
- Click play - video loads and plays
- Video controls work (play/pause, mute, fullscreen)
- Lazy loading verified (video not loaded until played)
- YouTube/Vimeo embeds work correctly
- Keyboard controls work (space to play/pause)

### Task 7.9: Accessibility Enhancements & ARIA Live Regions

**Acceptance Criteria**:
- [ ] Implement ARIA live regions for dynamic content:
  - Filter changes announcement
  - Section navigation announcements
  - Modal open/close announcements
  - Loading state announcements
- [ ] Skip navigation links (skip to main content, skip to section)
- [ ] Landmark roles properly assigned
- [ ] Focus management on modal open/close
- [ ] High contrast mode detection and support
- [ ] Reduced transparency mode
- [ ] Font size controls (user can increase text size)
- [ ] Dyslexia-friendly font option (OpenDyslexic)
- [ ] Screen reader-only content for context
- [ ] Descriptive button labels (not just "Click here")
- [ ] Alt text for all images
- [ ] Closed captions for videos

**Verification Checks**:
- Test with NVDA/JAWS - all content accessible
- Apply filter - screen reader announces change
- Open modal - focus moves to modal, announcement made
- Enable high contrast mode - site readable
- Increase font size - layout doesn't break
- Enable dyslexia font - font changes globally
- Tab through page - skip links work
- Lighthouse accessibility score: 100

### Task 7.10: Progressive Web App (PWA) Features

**Acceptance Criteria**:
- [ ] Create `manifest.json` with app metadata:
  - Name, short_name, description
  - Icons (192x192, 512x512, maskable)
  - Theme color, background color
  - Display mode: "standalone"
  - Start URL
- [ ] Service worker for offline functionality:
  - Cache static assets (HTML, CSS, JS, fonts)
  - Cache JSON data files
  - Offline fallback page
  - Background sync for analytics
- [ ] Install prompt handling:
  - Detect install capability
  - Custom install button in header/footer
  - Defer native prompt, show custom UI
- [ ] App-like features:
  - Splash screen on launch
  - Status bar theming (mobile)
  - Full-screen mode option
- [ ] Update notification when new version available
- [ ] Offline indicator in UI

**Verification Checks**:
- Lighthouse PWA score > 90
- Install button appears in browser
- Click install - app installs to home screen/desktop
- Open installed app - looks native
- Disconnect network - site still loads (offline)
- Offline page shows when no cache
- Reconnect - data syncs
- Theme color applied to browser UI

---

## Success Criteria

- [ ] Multiple download format options working
- [ ] Blog/articles section rendering correctly
- [ ] Video integration with lazy loading
- [ ] Advanced accessibility features complete
- [ ] Lighthouse Accessibility score: 100
- [ ] PWA features working with offline support
- [ ] Lighthouse PWA score > 90

---

## Dependencies
- **Requires**: Plan 1-10 (core MVP, Enhanced UI, and Phase 7 Part A)

## Estimated Effort
- 12-15 days
