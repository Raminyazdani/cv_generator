# Frontend Plan 0: Frontend Readiness & Tooling

## Goal
Establish the development environment, tooling, and local workflow for the React/TypeScript frontend before any feature development begins.

## Scope
This plan covers:
- Development environment setup
- Build system configuration
- Linting and type checking
- Local development workflow
- Integration testing setup

---

## CRITICAL RULES (MUST FOLLOW)

### LOCKED FILES / IMMUTABILITY
- `data/cvs/ramin.json`, `data/cvs/mahsa.json` are byte-identical locked inputs.
- **Absolutely no edits, no formatting changes, no sorting, no whitespace modifications** to these files.

### SELF-OVERSEER / DO-NOT-STOP
- You must continuously self-audit and do not stop until:
  (a) The plan's acceptance criteria are fully satisfied,
  (b) You can run the relevant project locally after changes with zero errors,
  (c) You verified behavior with evidence (logs/tests/screens), not assumptions.
- Do not claim "done" unless you can run dev + build/test (as applicable) and confirm expected behavior.

### NO FEATURE CREEP
- Only implement what is required for this plan's scope.
- No unrelated refactors or redesigns.

---

## Deliverables

### Task 0.1: Node.js Environment Verification

**Acceptance Criteria**:
- [ ] Verify Node.js 18+ installed
- [ ] Verify npm 9+ or yarn 3+ installed
- [ ] Document required versions in README

**Verification Checks**:
- [ ] `node --version` shows v18+
- [ ] `npm --version` shows 9+
- [ ] Package manager commands work

### Task 0.2: Project Initialization

**Acceptance Criteria**:
- [ ] Create React + TypeScript project using Vite:
  ```bash
  npm create vite@latest frontend -- --template react-ts
  ```
- [ ] Or use Create React App:
  ```bash
  npx create-react-app frontend --template typescript
  ```
- [ ] Set up project in `frontend/` directory
- [ ] Configure `tsconfig.json` with strict mode

**Verification Checks**:
- [ ] `npm run dev` starts development server
- [ ] No TypeScript errors on initial setup
- [ ] Hot reload works

### Task 0.3: Linting Configuration

**Acceptance Criteria**:
- [ ] Configure ESLint with TypeScript support:
  ```bash
  npm install -D eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser
  ```
- [ ] Configure Prettier for code formatting:
  ```bash
  npm install -D prettier eslint-config-prettier
  ```
- [ ] Create `.eslintrc.json`:
  ```json
  {
    "extends": [
      "eslint:recommended",
      "plugin:@typescript-eslint/recommended",
      "plugin:react-hooks/recommended",
      "prettier"
    ],
    "parser": "@typescript-eslint/parser",
    "rules": {
      "@typescript-eslint/no-unused-vars": "error",
      "@typescript-eslint/no-explicit-any": "error"
    }
  }
  ```
- [ ] Create `.prettierrc`:
  ```json
  {
    "semi": true,
    "singleQuote": true,
    "tabWidth": 2,
    "trailingComma": "es5"
  }
  ```
- [ ] Add lint scripts to `package.json`:
  ```json
  {
    "scripts": {
      "lint": "eslint src --ext .ts,.tsx",
      "lint:fix": "eslint src --ext .ts,.tsx --fix",
      "format": "prettier --write src/**/*.{ts,tsx,css}"
    }
  }
  ```

**Verification Checks**:
- [ ] `npm run lint` runs without configuration errors
- [ ] `npm run format` formats files correctly
- [ ] No `any` types allowed (strict)

### Task 0.4: TypeScript Strict Configuration

**Acceptance Criteria**:
- [ ] Update `tsconfig.json`:
  ```json
  {
    "compilerOptions": {
      "strict": true,
      "noImplicitAny": true,
      "strictNullChecks": true,
      "noUnusedLocals": true,
      "noUnusedParameters": true,
      "noImplicitReturns": true,
      "esModuleInterop": true,
      "skipLibCheck": true,
      "forceConsistentCasingInFileNames": true,
      "resolveJsonModule": true,
      "declaration": true,
      "jsx": "react-jsx"
    }
  }
  ```
- [ ] Verify strict mode catches type errors

**Verification Checks**:
- [ ] `tsc --noEmit` runs without errors
- [ ] Strict null checks enabled
- [ ] Implicit any forbidden

### Task 0.5: Testing Setup

**Acceptance Criteria**:
- [ ] Install testing dependencies:
  ```bash
  npm install -D vitest @testing-library/react @testing-library/jest-dom
  ```
- [ ] Configure Vitest in `vite.config.ts`:
  ```typescript
  import { defineConfig } from 'vite';
  import react from '@vitejs/plugin-react';
  
  export default defineConfig({
    plugins: [react()],
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
    },
  });
  ```
- [ ] Create test setup file
- [ ] Add test scripts to `package.json`:
  ```json
  {
    "scripts": {
      "test": "vitest",
      "test:coverage": "vitest --coverage"
    }
  }
  ```

**Verification Checks**:
- [ ] `npm run test` runs without errors
- [ ] Sample test passes
- [ ] Coverage report generates

### Task 0.6: Backend Proxy Configuration

**Acceptance Criteria**:
- [ ] Configure Vite to proxy API requests to backend:
  ```typescript
  // vite.config.ts
  export default defineConfig({
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  });
  ```
- [ ] Document how to run frontend with backend
- [ ] Create environment variable for API base URL:
  ```
  VITE_API_BASE_URL=/api/v1
  ```

**Verification Checks**:
- [ ] Frontend can call `/api/v1/cvs/` via proxy
- [ ] Environment variable used in code
- [ ] Works with backend running

### Task 0.7: Directory Structure

**Acceptance Criteria**:
- [ ] Create standard directory structure:
  ```
  frontend/
  ├── public/
  │   └── favicon.ico
  ├── src/
  │   ├── components/
  │   │   └── .gitkeep
  │   ├── context/
  │   │   └── .gitkeep
  │   ├── hooks/
  │   │   └── .gitkeep
  │   ├── types/
  │   │   └── cv.types.ts
  │   ├── styles/
  │   │   └── global.css
  │   ├── utils/
  │   │   └── .gitkeep
  │   ├── services/
  │   │   └── api.ts
  │   ├── App.tsx
  │   ├── main.tsx
  │   └── test/
  │       └── setup.ts
  ├── .eslintrc.json
  ├── .prettierrc
  ├── package.json
  ├── tsconfig.json
  ├── vite.config.ts
  └── README.md
  ```
- [ ] Document directory purposes in README

**Verification Checks**:
- [ ] All directories created
- [ ] Directory structure documented
- [ ] Imports resolve correctly

### Task 0.8: Git Configuration

**Acceptance Criteria**:
- [ ] Create `.gitignore` for frontend:
  ```
  node_modules/
  dist/
  .vite/
  *.local
  coverage/
  .DS_Store
  *.log
  ```
- [ ] Configure pre-commit hooks (optional):
  ```bash
  npm install -D husky lint-staged
  npx husky install
  ```

**Verification Checks**:
- [ ] node_modules not tracked
- [ ] Build artifacts not tracked
- [ ] Pre-commit hooks run (if configured)

### Task 0.9: Development Workflow Documentation

**Acceptance Criteria**:
- [ ] Create `frontend/README.md`:
  ```markdown
  # CV Generator Frontend
  
  ## Quick Start
  ```bash
  npm install
  npm run dev
  ```
  
  ## Available Scripts
  - `npm run dev` - Start development server
  - `npm run build` - Build for production
  - `npm run preview` - Preview production build
  - `npm run test` - Run tests
  - `npm run lint` - Run linting
  - `npm run format` - Format code
  
  ## Directory Structure
  ...
  
  ## Environment Variables
  ...
  ```
- [ ] Include troubleshooting section

**Verification Checks**:
- [ ] README is complete
- [ ] All commands documented
- [ ] New developer can set up in < 10 minutes

---

## Self-Overseer Checklist

Before marking complete:
- [ ] Node.js environment verified
- [ ] Project initialized and running
- [ ] Linting configured and passing
- [ ] TypeScript strict mode enabled
- [ ] Testing framework set up
- [ ] Backend proxy configured
- [ ] Directory structure created
- [ ] Git configuration complete
- [ ] Documentation complete

---

## Success Criteria

- [ ] `npm run dev` starts development server
- [ ] `npm run build` creates production build
- [ ] `npm run test` runs tests
- [ ] `npm run lint` passes with no errors
- [ ] `tsc --noEmit` passes with no errors
- [ ] Backend proxy working (if backend running)

---

## Dependencies
- None (this is the first frontend plan)

## Estimated Effort
- 1 day

---

## Run Commands Summary

```bash
# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Run tests
npm run test

# Run tests with coverage
npm run test:coverage

# Lint code
npm run lint

# Fix lint issues
npm run lint:fix

# Format code
npm run format

# Type check
tsc --noEmit
```
