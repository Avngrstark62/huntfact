# HuntFact UI Redesign Spec 03 - Editorial Minimal

## 1) Goal
Redesign the Android UI to feel premium, calm, and editorial with typography-led hierarchy and generous whitespace.
Keep all behavior unchanged; update presentation only.

## 2) Non-Negotiable Safety Rules

1. Never modify backend code or backend contracts.
2. Do not alter auth/session logic, data fetching logic, or result parsing logic.
3. Do not rename callback signatures or viewmodel/public interfaces.
4. Do not remove any existing feature capability.
5. Do not delete resources/profile code, even if hidden from navigation.

## 3) Allowed Scope
UI-only files/resources:

- `android/app/src/main/java/com/abhijeet/huntfact/MainActivity.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ResultActivity.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/theme/*`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/components/AppComponents.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/hunts/HuntsScreen.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/resources/ResourcesScreen.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/profile/ProfileScreen.kt`
- UI resource files under `android/app/src/main/res/`

## 4) Visual Direction
Design language: refined typography, subtle contrast, low visual noise.

- Neutral-first palette
- Fewer decorative elements
- Strong spacing and text hierarchy
- Lightweight controls
- Content-first cards

## 5) Design Tokens (Use Exactly)

### 5.1 Color Tokens
- `Primary`: `#1F3A8A` (single accent)
- `Background`: `#F8F9FC`
- `Surface`: `#FFFFFF`
- `SurfaceVariant`: `#F0F2F7`
- `OnSurface`: `#111317`
- `OnSurfaceVariant`: `#646B7B`
- `Outline`: `#D9DDE6`
- `Success`: `#1B7F4A`
- `Warning`: `#A96A00`
- `Error`: `#A32A2A`

Dark mode should remain soft, not high-neon.

### 5.2 Typography
Use a strict hierarchy:

- Display title: 32sp / medium
- Screen title: 26sp / semibold
- Section label: 13sp / uppercase medium
- Card title: 17sp / medium
- Body: 15sp / regular
- Meta: 12sp / regular

Prefer increased line-height for readability:

- Body line height >= 22sp
- Meta line height >= 17sp

### 5.3 Shape and Elevation
- Corners: 8dp for most surfaces
- No heavy shadows; use border (`Outline`) to separate surfaces
- Elevation mostly 0dp-1dp

### 5.4 Spacing Scale
Use 8, 12, 16, 24, 32, 40 dp.
Top sections must breathe (minimum 24dp).

## 6) Component Rules

1. Bottom nav:
   - icons must be simple outlined icons (`Home`, `Analytics`, `History`)
   - selected item should use weight/color change, no flashy indicator
2. `SectionTitle` style:
   - large but understated
3. `InfoCard`:
   - clean surface + thin border
   - avoid gradient or decorative backgrounds
4. Chips:
   - tonal subtle backgrounds, small text
5. Links:
   - underlined or clear color contrast with compact icon when possible

## 7) Screen-Specific Layout Specs

### 7.1 Home
- Header block:
  - label: `HOME`
  - title: `Your hunts`
  - helper line: `Latest verification requests and statuses`
- Stats row should be compact and minimal.
- Refresh/signout controls should be secondary-visual buttons.
- Hunt list cards should prioritize claim text readability.

### 7.2 Analyze
- Minimal placeholder center panel:
  - title: `Analyze`
  - one short paragraph
  - no decorative art required

### 7.3 History
- Keep list-only behavior.
- Add simple top context:
  - label: `HISTORY`
  - title: `Previous hunts`

### 7.4 Result
- Structured editorial layout:
  - headline with hunt id
  - subdued status badge
  - search and filters in one slim controls row/card
  - claim cards with clear text width and spacing
- Source links should be grouped under small `Sources` heading.

## 8) Motion and Interaction

1. Minimal motion:
   - fade transitions only (100-150ms)
2. Avoid bouncing, scaling, or playful animation.
3. Focus states and pressed states must still be visible.

## 9) Accessibility Rules

1. Preserve text clarity and contrast AA.
2. Keep controls >= 48dp touch target.
3. Handle long text and large fonts without overlap/truncation bugs.

## 10) Backend/Core Integrity Checklist

- Home refresh callback unchanged.
- Sign in/out callbacks unchanged.
- Hunt row click opens same detail activity using same extra key.
- Result search/filter logic unchanged.
- No data model or parsing code contract changes.

## 11) Non-Goals

- No business logic redesign.
- No new backend dependencies.
- No removal of hidden but existing pages/components.

