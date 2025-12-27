# Frontend Plans Index

This directory contains the comprehensive plan set for implementing a React/TypeScript frontend for the CV Generator project.

---

## Overview

The frontend plans cover building a premium, production-ready single-page CV/portfolio website that:
- Renders entirely from JSON data (via backend API or static files)
- Supports multiple languages (EN/DE/FA with RTL)
- Offers multiple visual themes
- Includes comprehensive filtering by type_key
- Provides rich media handling and modern UI/UX

---

## Plan Summary

### Core MVP Plans (Phases 0-5)

| Plan | Title | Original Plan | Dependencies | Est. Effort |
|------|-------|---------------|--------------|-------------|
| [plan0_frontend_readiness.md](./plan0_frontend_readiness.md) | Frontend Readiness & Tooling | New | None | 1 day |
| [plan1_project_setup.md](./plan1_project_setup.md) | Project Setup & Foundation | Plan 1 | Plan 0 | 1-2 days |
| [plan2_layout_theme.md](./plan2_layout_theme.md) | Core Layout & Theme System | Plan 2 | Plan 1 | 2-3 days |
| [plan3_section_rendering.md](./plan3_section_rendering.md) | Section Rendering & JSON Mapping | Plan 3 | Plans 1, 2 | 5-7 days |
| [plan4_advanced_features.md](./plan4_advanced_features.md) | Advanced Features (Filtering, Media) | Plan 4 | Plans 1-3 | 3-4 days |
| [plan5_robustness_polish.md](./plan5_robustness_polish.md) | Robustness & Polish | Plan 5 | Plans 1-4 | 2-3 days |

### Enhanced UI Plans (Phase 6)

| Plan | Title | Original Plan | Dependencies | Est. Effort |
|------|-------|---------------|--------------|-------------|
| [plan6_enhanced_ui_a.md](./plan6_enhanced_ui_a.md) | Enhanced UI - Part A (3D Carousel, Effects) | Plan 7 | Plans 1-5 | 8-10 days |
| [plan7_enhanced_ui_b.md](./plan7_enhanced_ui_b.md) | Enhanced UI - Part B (Cursor, FAB) | Plan 8 | Plans 1-6 | 6-8 days |
| [plan8_enhanced_ui_c.md](./plan8_enhanced_ui_c.md) | Enhanced UI - Part C (Tooltips, Cards) | Plan 9 | Plans 1-7 | 8-10 days |

### Advanced Features Plans (Phase 7)

| Plan | Title | Original Plan | Dependencies | Est. Effort |
|------|-------|---------------|--------------|-------------|
| [plan9_seo_analytics.md](./plan9_seo_analytics.md) | SEO, Analytics, Skills Visualization | Plan 10 | Plans 1-8 | 10-12 days |
| [plan10_download_blog_pwa.md](./plan10_download_blog_pwa.md) | Download, Blog, Video, A11y, PWA | Plan 11 | Plans 1-9 | 12-15 days |
| [plan11_comments_i18n.md](./plan11_comments_i18n.md) | Comments, A/B Testing, i18n, Monitoring | Plan 12 | Plans 1-10 | 12-15 days |

**Total Estimated Effort: 70-89 days**

---

## Execution Order

### MVP Track (Essential)
```
Plan 0 (Readiness) → Plan 1 (Setup) → Plan 2 (Layout) → Plan 3 (Sections) → Plan 4 (Features) → Plan 5 (Polish)
```
This delivers a functional, production-ready CV website.

### Premium UI Track
```
Plan 6 → Plan 7 → Plan 8
```
This adds beautiful animations and interactive effects.

### Advanced Features Track
```
Plan 9 → Plan 10 → Plan 11
```
This adds SEO, analytics, PWA, and enterprise features.

---

## Key Features by Plan

### Plan 1-2: Foundation
- React + TypeScript project setup
- 6 theme presets with CSS custom properties
- RTL support for Persian/Farsi
- Sticky header with navigation
- Responsive layout

### Plan 3: Content Rendering
- Hero section with profile photo
- Social links/profiles
- Education, Experience, Skills sections
- Projects, Publications, References sections
- type_key filtering support

### Plan 4-5: Polish
- Media thumbnails and modal system
- Global focus filter context
- Smooth scroll and animations
- PDF export (browser print)
- Accessibility (WCAG 2.1 AA)
- Performance optimization

### Plan 6-8: Enhanced UI
- 3D language carousel
- Premium button effects
- Parallax scrolling
- Custom cursor effects
- Floating action button
- Theme transitions
- Skeleton loading screens

### Plan 9-11: Advanced
- SEO meta tags and structured data
- Analytics integration
- Skills visualization dashboard
- Progressive Web App features
- Full i18n for UI labels

---

## Integration with Backend

The frontend integrates with the Django backend API:

```typescript
// API endpoints used by frontend
const API_BASE = '/api/v1';

// Fetch CV data
fetch(`${API_BASE}/cvs/${person}/?lang=${lang}`);

// Fetch section
fetch(`${API_BASE}/cvs/${person}/${section}/?lang=${lang}`);

// Download PDF
window.location.href = `${API_BASE}/cvs/${person}/pdf/`;

// Get profile picture
const picUrl = `${API_BASE}/cvs/${person}/picture/`;
```

---

## Critical Rules

Every frontend plan includes these rules that MUST be followed:

### LOCKED FILES / IMMUTABILITY
- `ramin_de.json`, `ramin_fa.json`, `cv.json` (referenced in original plans) are read-only inputs.
- **Absolutely no edits** to locked data files.

### SELF-OVERSEER REQUIREMENT
- Continuously self-audit until all acceptance criteria are satisfied.
- Verify everything with evidence (logs/tests/screens).
- Do not declare "done" until the project runs without errors.

### DEBUG+RUN REQUIREMENT
- Run `npm run dev` AND `npm run build` after changes.
- Confirm no runtime errors.
- Navigate relevant pages to confirm functionality.

---

## Technology Stack

- **Framework**: React 18+
- **Language**: TypeScript 5+ (strict mode)
- **Build Tool**: Vite (recommended) or Create React App
- **Styling**: CSS Custom Properties, CSS Modules or Tailwind
- **State**: React Context API
- **Testing**: Jest, React Testing Library
- **Linting**: ESLint, Prettier

---

## Directory Structure (Target)

```
frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── public/
├── src/
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── HeroSection.tsx
│   │   ├── EducationSection.tsx
│   │   └── ...
│   ├── context/
│   │   ├── ThemeContext.tsx
│   │   ├── LanguageContext.tsx
│   │   └── FilterContext.tsx
│   ├── hooks/
│   ├── types/
│   │   └── cv.types.ts
│   ├── styles/
│   │   ├── themes.css
│   │   ├── rtl.css
│   │   └── print.css
│   ├── utils/
│   │   ├── themeManager.ts
│   │   └── mediaDetector.ts
│   ├── data/
│   │   └── (JSON files if not using API)
│   ├── App.tsx
│   └── main.tsx
└── tests/
```

---

## Success Metrics

After completing all frontend plans:

- [ ] TypeScript strict mode: 0 type errors
- [ ] ESLint: 0 errors, 0 warnings
- [ ] Lighthouse: Performance > 90, Accessibility 100
- [ ] Bundle size: Initial load < 500KB
- [ ] All 3 languages (EN/DE/FA) working with RTL
- [ ] All 6 themes working
- [ ] Focus filtering working across all sections
