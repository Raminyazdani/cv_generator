# Plan 1: Project Setup & Foundation (Phase 0)

## Goal
Set up the base React + TypeScript project with minimal dependencies, create TypeScript interfaces matching the JSON schema, and prepare multi-language JSON data files.

## Scope
This plan covers:
- Task 0.1: Initialize React + TypeScript Project
- Task 0.2: Create TypeScript Interfaces for JSON Schema  
- Task 0.3: Create Multi-Language JSON Files (EN, DE, FA)

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

### Task 0.1: Initialize React + TypeScript Project

**Acceptance Criteria**:
- [ ] Create React app with TypeScript template
- [ ] Configure `tsconfig.json` with strict mode
- [ ] Set up folder structure: `/src/components`, `/src/types`, `/src/data`, `/src/styles`, `/src/utils`
- [ ] Add only essential dependencies: React 18+, TypeScript 5+
- [ ] Configure build system (Vite or Create React App)
- [ ] Create `.gitignore` excluding `node_modules`, build artifacts

**Verification Checks**:
- Verify `tsconfig.json` has `"strict": true`
- Run `npm run build` succeeds without errors
- Verify no unnecessary dependencies in `package.json` (max 10 total dependencies)
- Check folder structure matches specification

### Task 0.2: Create TypeScript Interfaces for JSON Schema

**Acceptance Criteria**:
- [ ] Create `src/types/cv.types.ts` with all interfaces
- [ ] Define `Basics`, `Profile`, `Education`, `Experience`, `Skill`, `Project`, `Publication`, `Reference`, `Language`, `Certification` interfaces
- [ ] Include `type_key` as `string[]` in all relevant types
- [ ] Define `Pictures` type with `type_of` and `URL`
- [ ] Support nested skills structure (category → subcategory → items)
- [ ] Make all fields optional with `?` for robustness

**Verification Checks**:
- Load `ramin.json` and assign to typed variable - no TypeScript errors
- All top-level JSON keys have corresponding interfaces
- `type_key` present in Education, Skills, Experience, Projects, Publications, References, Certifications
- Run `tsc --noEmit` with no type errors

### Task 0.3: Create Multi-Language JSON Files

**Acceptance Criteria**:
- [ ] Copy `ramin.json` to `src/data/cv-en.json`
- [ ] Create `src/data/cv-de.json` with German translations (all text fields)
- [ ] Create `src/data/cv-fa.json` with Farsi translations (all text fields)
- [ ] Ensure identical structure across all three files (same keys, same nesting)
- [ ] Verify all URLs remain unchanged across files

**Verification Checks**:
- Parse all three JSON files successfully
- Compare object key sets - must be identical
- Count array lengths for each section - must match across files
- Verify `type_key` arrays are identical across language files

---

## Success Criteria

- [ ] Project initializes and runs with `npm start` or `npm run dev`
- [ ] Build succeeds with `npm run build`
- [ ] TypeScript strict mode enabled and passing
- [ ] All three language JSON files created with identical structures
- [ ] Folder structure organized as specified

---

## Dependencies
- None (this is the first plan)

## Estimated Effort
- 1-2 days
