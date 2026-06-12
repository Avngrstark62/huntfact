# HuntFact UI Redesign Spec 05 - Dark-First Cyber Clean

## 1) Goal
Redesign the Android UI with a dark-first, high-contrast modern tech look while preserving clarity and trust.
This is strictly a presentation overhaul. Core logic and backend wiring must remain untouched.

## 2) Non-Negotiable Safety Rules

1. Do not edit backend files or backend contracts.
2. Do not modify network API interfaces, parsing logic, auth/session internals, worker processing, or push flow.
3. Do not change intent keys, model properties, callback signatures, or data flow.
4. Do not remove existing features or break current navigation actions.
5. Keep resources/profile implementations in codebase; do not delete.

## 3) Allowed Scope
Android UI/theming files and UI resources only:

- `android/app/src/main/java/com/abhijeet/huntfact/MainActivity.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ResultActivity.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/theme/*`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/components/AppComponents.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/hunts/HuntsScreen.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/resources/ResourcesScreen.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/profile/ProfileScreen.kt`
- UI-only files under `android/app/src/main/res/`

## 4) Visual Direction
Design language: disciplined dark surfaces, neon-accent highlights, crisp data readability.

- Default visual baseline tuned for dark mode
- Light mode still supported, but dark style is primary
- High contrast for status clarity
- Structured cards and strong information density

## 5) Design Tokens (Use Exactly)

### 5.1 Dark-First Color Tokens
- `Background`: `#0B1020`
- `Surface`: `#121A2B`
- `SurfaceVariant`: `#1A2438`
- `Primary`: `#6A7BFF`
- `Accent`: `#00D1C7`
- `OnSurface`: `#E8EEFF`
- `OnSurfaceVariant`: `#A8B3CC`
- `Outline`: `#2D3A56`
- `Success`: `#20C16D`
- `Warning`: `#FFB020`
- `Error`: `#FF5A67`

Provide light equivalents that preserve hierarchy and contrast.

### 5.2 Typography
- Title XL: 30sp / bold
- Title L: 24sp / semibold
- Card title: 16sp / semibold
- Body: 14sp / regular
- Meta: 12sp / medium
- Label: 11-12sp / medium

### 5.3 Shape and Elevation
- Corners: 12dp default, 16dp highlighted cards
- Elevation: low; rely more on border/contrast than shadows
- Chips/buttons: rounded pills

### 5.4 Spacing
Use 4, 8, 12, 16, 20, 24, 28 dp.
Keep compact but readable rhythm.

## 6) Component Rules

1. Bottom nav:
   - dark elevated container
   - icons: `Home`, `Analytics`, `History`
   - selected tab: accent glow/underline + stronger label
2. Cards:
   - dark layered surfaces with outline strokes
   - clear separation between title/body/meta
3. Status and verdict chips:
   - saturated semantic colors (success/warn/error/neutral)
   - label text always visible
4. Buttons:
   - primary filled accent
   - secondary outlined
5. Inputs:
   - dark outlined text field with high-contrast placeholder/label text

## 7) Screen-Specific Layout Specs

### 7.1 Home
- Top command header:
  - title `Home`
  - subtitle `Hunt status dashboard`
- Stats in compact metric cards with accent numbers.
- Action row under stats:
  - `Refresh hunts`
  - `Sign out`
- Hunt list cards include:
  - main text
  - status chip
  - compact metadata line

### 7.2 Analyze
- Keep placeholder-only behavior.
- Design as cyber-styled panel:
  - icon
  - title `Analyze`
  - subtitle `Advanced analysis tools will appear here.`
  - disabled action button

### 7.3 History
- Keep list-only behavior.
- Add heading `History` and short subtitle.
- No summary cards and no action row.

### 7.4 Result
- Build a dark summary header card with hunt id/status/source preview.
- Search/filter area uses compact control strip.
- Claim cards:
  - high-contrast text blocks
  - verdict chip near title
  - source links visually separated and easy to tap
  - expandable explanation behavior unchanged

## 8) Motion and Interaction

1. Use controlled micro-interactions:
   - tab selection transition 140ms
   - card press 90ms
   - chip select 100ms
2. Avoid flashy neon animations or constant pulsing.

## 9) Accessibility Rules

1. Verify AA contrast in dark surfaces.
2. Keep touch targets >= 48dp.
3. Ensure readability with large text scaling.
4. Do not use color-only meaning for statuses; keep text labels.

## 10) Backend/Core Integrity Checklist

- Home refresh still triggers original refresh logic.
- Sign-in/sign-out logic unchanged.
- Hunt opening still launches `ResultActivity` using `EXTRA_HUNT_ID`.
- Result filtering/search logic unchanged.
- No repository/viewmodel/network signature change.
- No changes in worker or notification behavior.

## 11) Non-Goals

- No backend modifications.
- No processing pipeline modifications.
- No content/business copy rewrites beyond UI labels needed for design polish.

