# Flight & Hotel Tracker - QA Protocol

> "Quality is not an act, it is a habit." - Aristotle (and your Lead Engineer)

## 1. Testing Hierarchy

We adopt a 2-level testing strategy to ensure functionality and prevent regressions.

### Level 1: Component Unit Tests (Vitest + React Testing Library)
- **Scope**: Individual components (`ConfirmationModal`, `AddRouteForm`).
- **Goal**: Verify UI interactions (clicks, inputs) and state changes.
- **Run Command**: `npm run test`
- **When to Run**: On every file save (watch mode) or before commit.

### Level 2: Integration/E2E Tests (Playwright - *Planned*)
- **Scope**: Full user flows (Create Route → Scrape → Delete).
- **Goal**: Verify backend-frontend integration.
- **Run Command**: `npm run test:e2e`

## 2. Test Requirements for New Features

Every new feature PR MUST include:
1. **Happy Path Test**: Does it work when used correctly?
2. **Edge Case Test**: What happens on API failure or invalid input?
3. **Accessibility Check**: Are interactive elements labeled?

## 3. Bug Fix Protocol

When fixing a reported bug (like the "flickering delete popup"):
1. **Reproduce**: Create a test case that fails (or manually verify).
2. **Fix**: Implement the code change.
3. **Verify**: Run the test suite.
4. **Regression Test**: Ensure no other related features broke.

## 4. Current Test Suite Status
- **Framework**: Vitest (configured via Vite)
- **Environment**: jsdom
- **Location**: `frontend/src/__tests__/` (or co-located `*.test.tsx`)
