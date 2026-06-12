# HuntFact UI Redesign Spec 01 - Clean Enterprise

## 1) Goal
Redesign the Android app UI to look clean, trustworthy, and modern with a data-first enterprise style.
This is a UI/UX-only redesign. Core behavior, backend connectivity, and business logic must remain unchanged.

## 2) Non-Negotiable Safety Rules
Apply all rules below exactly.

1. Do not modify backend code under `backend/`.
2. Do not change API contracts, request/response parsing, auth logic, notification logic, or hunt processing flow.
3. Do not rename database keys, JSON fields, model properties, or intent extras.
4. Do not delete any existing screens, viewmodels, repositories, workers, or activities.
5. Do not remove or alter existing callbacks for refresh, sign-in, sign-out, open-hunt, or deeplink handling.
6. Do not change navigation destinations or screen semantics; only restyle and reorganize presentation.
7. Do not introduce blocking operations in UI thread.
8. Do not add new dependencies unless strictly required for UI and already approved. Prefer existing Compose Material3 APIs.

## 3) Allowed Scope
You may edit only Android UI presentation files and UI-only resources, including:

- `android/app/src/main/java/com/abhijeet/huntfact/MainActivity.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ResultActivity.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/theme/Color.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/theme/Type.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/theme/Theme.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/theme/Spacing.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/components/AppComponents.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/hunts/HuntsScreen.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/resources/ResourcesScreen.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/profile/ProfileScreen.kt`
- visual-only drawables/colors/typography resources under `android/app/src/main/res/`

## 4) Visual Direction
Design language: serious, minimal, structured, highly legible.

- Strong spacing rhythm
- Neutral surfaces
- Restrained accent color usage
- Clear hierarchy through type and card grouping
- Subtle motion only

## 5) Design Tokens (Use Exactly)

### 5.1 Color Tokens
Create/refine these semantic tokens in theme:

- `Primary`: `#2457FF`
- `OnPrimary`: `#FFFFFF`
- `PrimaryContainer`: `#E7EDFF`
- `OnPrimaryContainer`: `#0D1B57`
- `Background`: `#F5F7FC`
- `Surface`: `#FFFFFF`
- `SurfaceVariant`: `#EEF1F8`
- `Outline`: `#D6DBE8`
- `OnSurface`: `#161A24`
- `OnSurfaceVariant`: `#5C6478`
- `Success`: `#148A44`
- `Warning`: `#B96900`
- `Error`: `#B3261E`

Dark equivalents should keep contrast >= WCAG AA for text.

### 5.2 Typography
Keep current font family if custom font is unavailable. Enforce hierarchy:

- Screen title: 28sp / semibold
- Section title: 20sp / semibold
- Card title: 16sp / medium
- Body: 14sp / regular
- Meta: 12sp / medium
- Button label: 14sp / semibold

### 5.3 Shape and Elevation
- Corner radii scale: 10dp (small), 14dp (medium), 18dp (large)
- Card elevation: default 1dp, pressed 2dp
- Buttons: rounded 12dp
- Chips: pill (999dp)

### 5.4 Spacing Scale
Define and use: 4, 8, 12, 16, 20, 24, 32 dp.
Avoid ad-hoc spacing values.

## 6) Component Rules

1. Replace letter-only bottom-nav icons with proper Material icons:
   - Home -> `Icons.Outlined.Home`
   - Analyze -> `Icons.Outlined.Analytics`
   - History -> `Icons.Outlined.History`
2. Bottom nav selected state must include tonal indicator and stronger label weight.
3. Standardize cards:
   - Uniform padding 16dp
   - Title + subtitle + metadata zone
   - Optional trailing chip
4. Buttons:
   - Primary action full-width when alone
   - Split actions in balanced row when paired
5. Empty states:
   - Icon + title + one-line subtitle + optional action
6. Inputs:
   - Outlined text field with consistent corner radius and focused border color.

## 7) Screen-Specific Layout Specs

### 7.1 Home (Hunts)
- Add top app bar zone with:
  - Title: `Home`
  - Supporting text: `Track your latest fact-check hunts`
- Keep same data and callbacks.
- Keep stats and actions, but style them as structured dashboard blocks.
- Ensure hunt list starts after a visible section divider (`Latest hunts` label).

### 7.2 Analyze
- Keep placeholder behavior.
- Use centered template block with icon, title, subtitle, and disabled sample action button (`Coming soon`).

### 7.3 History
- Keep current logic: list-only hunts presentation.
- No stats, no refresh/signout row.
- Add top label `History` and subtitle `Past hunts and statuses`.
- Preserve open-hunt behavior.

### 7.4 Result Screen
- Add structured header card:
  - Hunt id
  - status chip
  - source caption/link preview
- Move search/filter into a dedicated control panel card.
- Improve claim card readability:
  - claim title
  - verdict chip
  - explanation with gradient fade when collapsed
  - sources list with external-link affordance

## 8) UX Behavior Rules

1. Keep all existing actions and logic.
2. Add subtle animation only:
   - tab change crossfade 150ms
   - card press scale 0.98 with spring back
3. No heavy/parallax animations.
4. Keep scroll performance smooth with lazy lists.

## 9) Accessibility and Quality Rules

1. Text contrast must satisfy AA.
2. Touch targets minimum 48dp.
3. Support dynamic font scaling without clipped text.
4. Avoid conveying state with color alone; keep text labels in chips.
5. Ensure TalkBack-friendly labels for icon-only controls.

## 10) Backend/Core Integrity Checklist (Must Pass)
Before finishing, verify all are true:

- Hunt list fetch still works.
- Refresh hunts still works on Home.
- Sign-in/sign-out flows still work where present.
- Opening a hunt still launches `ResultActivity` with same `EXTRA_HUNT_ID`.
- Result parsing and filters still work exactly as before.
- No repository/viewmodel/api signature changed.

## 11) Non-Goals

- Do not redesign business flow.
- Do not add new tabs or remove current tabs.
- Do not alter copy meaning or data values.
- Do not rewrite backend or storage layers.

