# HuntFact UI Redesign Spec 04 - Neo Surface

## 1) Goal
Redesign the Android UI with layered modern surfaces (soft glass-like depth) while preserving readability and performance.
This must remain a UI/UX-only change with zero backend or logic regressions.

## 2) Non-Negotiable Safety Rules

1. Do not modify anything under `backend/`.
2. Do not alter repositories, API interfaces, auth/session, worker flow, or notifications behavior.
3. Do not change intent keys, JSON keys, or parser assumptions.
4. Do not remove existing callbacks or interaction paths.
5. Do not delete resources/profile screens or code.
6. Prioritize runtime performance; no expensive custom rendering loops.

## 3) Allowed Scope
UI and resources only:

- `android/app/src/main/java/com/abhijeet/huntfact/MainActivity.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ResultActivity.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/theme/*`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/components/AppComponents.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/hunts/HuntsScreen.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/resources/ResourcesScreen.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/profile/ProfileScreen.kt`
- UI-only resources under `android/app/src/main/res/`

## 4) Visual Direction
Design language: layered translucent surfaces, soft glows, modern depth, clean typography.

- Use blur-like appearance via tonal/translucent overlays (without heavy runtime blur if costly)
- Maintain strong contrast on text
- Keep structure clear despite visual effects

## 5) Design Tokens (Use Exactly)

### 5.1 Color Tokens
- `Primary`: `#5B6BFF`
- `Secondary`: `#26C6DA`
- `BackgroundTop`: `#EEF2FF`
- `BackgroundBottom`: `#F8FBFF`
- `SurfaceGlass`: `#FFFFFFCC` (80% alpha)
- `SurfaceGlassStrong`: `#FFFFFFE6` (90% alpha)
- `SurfaceBorder`: `#FFFFFF99` (60% alpha)
- `OnSurface`: `#101426`
- `OnSurfaceVariant`: `#53607D`
- `Success`: `#18A454`
- `Warning`: `#CC7A00`
- `Error`: `#C53030`

Dark mode equivalents must preserve translucency concept with darker alpha surfaces.

### 5.2 Typography
- Screen title: 28sp / semibold
- Card title: 16sp / semibold
- Body: 14sp / regular
- Meta: 12sp / medium

### 5.3 Shape and Elevation
- Corner radii: 16dp (default), 22dp (hero)
- Layered card shadows: 1dp + soft tonal shadow
- Chips: fully rounded

### 5.4 Spacing
Use 6, 10, 14, 18, 24, 32 dp for this direction.
Keep consistent across all screens.

## 6) Component Rules

1. Bottom nav:
   - floating-style container with rounded 20dp top corners or pill container
   - icons: Home, Analytics, History
   - selected tab gets subtle glow/tonal pill
2. Cards:
   - glass-like background + border stroke
   - avoid opaque heavy blocks
3. Status/verdict chips:
   - solid accessible colors, not translucent (for readability)
4. Inputs:
   - rounded outlined style with soft background tint
5. Empty states:
   - icon badge + title + subtitle in glass card

## 7) Screen-Specific Layout Specs

### 7.1 Home
- Add gradient-like backdrop layer behind content area.
- Header glass hero:
  - title `Home`
  - subtitle `Track your hunts in real time`
  - compact stats
- Action row (refresh/signout) in separate glass card.
- Hunt list cards use layered glass style but keep current data and click actions.

### 7.2 Analyze
- Centered glass card placeholder with icon and concise coming-soon copy.
- Include non-interactive mini mock metrics rows (visual only, no backend dependency).

### 7.3 History
- List-only behavior remains.
- Add simple glass header with `History` and one-line context.
- No stats, no refresh/signout controls.

### 7.4 Result
- Top summary glass card with hunt identity and status.
- Search + filter chips in a frosted control tray.
- Claim rows in glass cards with clear source links and expandable explanation.

## 8) Motion and Interaction

1. Smooth motion allowed but lightweight:
   - tab transition 180ms
   - card hover/press elevation shift 100ms
   - chip selection color morph 120ms
2. Keep animation count low in long lists to avoid jank.

## 9) Accessibility and Performance Rules

1. Never sacrifice contrast for glass effect.
2. Keep text contrast AA in all states.
3. Maintain 48dp touch targets.
4. Avoid expensive blur shaders on low-end devices; use alpha surfaces if needed.
5. Keep scrolling smooth in lazy lists.

## 10) Backend/Core Integrity Checklist

- No changed callbacks or method signatures in viewmodels/repositories.
- Home refresh/signout/signin still work exactly as before.
- History list still opens result details via existing intent key.
- Result parsing and filtering behavior unchanged.
- No new network calls introduced for UI effects.

## 11) Non-Goals

- No backend or pipeline changes.
- No new data entities.
- No removal of existing hidden screens/components.

