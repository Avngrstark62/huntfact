# HuntFact UI Redesign Spec 02 - Bold Modern Consumer

## 1) Goal
Redesign the Android UI to feel vibrant, confident, and contemporary with strong visual identity.
This redesign must change presentation only; backend integration and core functionality must remain intact.

## 2) Non-Negotiable Safety Rules

1. Do not touch any file under `backend/`.
2. Do not modify repositories, network models, auth/session internals, worker pipeline, or notification wiring.
3. Do not change intent extras, JSON parsing, or database-facing field names.
4. Do not remove existing screens or callbacks.
5. Keep all existing user actions operational (refresh, sign-in, sign-out, open hunt, filters, search).
6. UI refactor is allowed; logic refactor is not.

## 3) Allowed Scope
Edit only Android UI/theming resources and presentation code:

- `android/app/src/main/java/com/abhijeet/huntfact/MainActivity.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ResultActivity.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/theme/*`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/components/AppComponents.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/hunts/HuntsScreen.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/resources/ResourcesScreen.kt`
- `android/app/src/main/java/com/abhijeet/huntfact/ui/profile/ProfileScreen.kt`
- UI-only assets in `android/app/src/main/res/`

## 4) Visual Direction
Design language: energetic, branded, modern consumer app.

- Strong top hero areas
- Brighter accent usage
- Larger heading contrast
- Friendly iconography
- Soft gradients and expressive chips

## 5) Design Tokens (Use Exactly)

### 5.1 Color Tokens
- `Primary`: `#4A5DFF`
- `Secondary`: `#7A3DFF`
- `Tertiary`: `#00A7C4`
- `AccentGradientStart`: `#4A5DFF`
- `AccentGradientEnd`: `#8A46FF`
- `Background`: `#F4F6FF`
- `Surface`: `#FFFFFF`
- `SurfaceVariant`: `#EAEFFF`
- `OnSurface`: `#11162A`
- `OnSurfaceVariant`: `#525D7A`
- `Success`: `#0FA958`
- `Warning`: `#D88600`
- `Error`: `#C62828`

Dark mode must preserve the same brand personality (avoid flat gray-only dark palette).

### 5.2 Typography
- Hero title: 30sp / bold
- Screen title: 24sp / semibold
- Section title: 18sp / semibold
- Card title: 16sp / semibold
- Body: 14sp / regular
- Meta: 12sp / medium

### 5.3 Shape and Elevation
- Corners: 14dp base, 20dp large hero cards
- Buttons: pill or 14dp rounded
- Card elevation: 2dp default, 4dp featured
- Chips: pill with tonal background and medium-weight labels

### 5.4 Spacing Scale
Use 4, 8, 12, 16, 24, 32 dp.
Hero sections must use at least 24dp internal padding.

## 6) Component Rules

1. Bottom nav must use actual icons:
   - Home -> `Icons.Rounded.Home`
   - Analyze -> `Icons.Rounded.AutoGraph`
   - History -> `Icons.Rounded.History`
2. Selected tab style:
   - rounded pill indicator
   - icon and text both tinted with primary/secondary blend
3. Create a reusable `HeroHeaderCard` component for major screens.
4. Update `InfoCard` to support optional gradient border or accent strip.
5. Upgrade status/verdict chips to vivid but accessible tones.
6. Use icon + text pairings for metadata rows where appropriate.

## 7) Screen-Specific Layout Specs

### 7.1 Home
- Top hero card includes:
  - title: `Home`
  - subtitle: `Check, track, and verify quickly`
  - compact quick stats row
- Place refresh/signout actions in a segmented action row below hero.
- Hunt list section title: `Recent hunts`.
- Hunt cards:
  - prominent claim/caption line
  - status chip on top-right
  - creator/time in lighter metadata row with icons

### 7.2 Analyze
- Keep placeholder functionally.
- Build a polished placeholder panel:
  - analytics icon
  - title `Analyze`
  - subtitle `Deeper claim analysis tools are coming soon.`
  - disabled CTA button `Enable when ready`

### 7.3 History
- Use same hunt cards as home list for consistency.
- No top stats and no refresh/signout controls.
- Show heading `History` + subtitle `All your completed and in-progress hunts`.

### 7.4 Result
- Add hero summary at top with hunt status and source context.
- Search and filters inside one elevated control card.
- Claim cards:
  - high-contrast verdict chip near title
  - cleaner source links with link icon
  - collapsed explanation shows 3 lines + fade + `Read more`.

## 8) Motion and Interaction

1. Use tasteful motion:
   - tab switch 180ms
   - list item enter fade/slide 150ms stagger
   - chip selection animate color transition 120ms
2. Keep motion subtle; no long or distracting animation chains.

## 9) Accessibility Rules

1. Maintain AA contrast in all states.
2. Keep minimum touch targets 48dp.
3. Ensure text wraps gracefully in larger font scales.
4. Do not rely on gradient alone for state communication; always include labels.

## 10) Backend/Core Integrity Checklist
Must all remain true:

- Home refresh still triggers same refresh callback.
- Sign-in and sign-out behavior unchanged.
- Hunt tap still opens `ResultActivity` using unchanged `EXTRA_HUNT_ID`.
- Search and verdict filters in result screen still function identically.
- No changes to repository/viewmodel API signatures.

## 11) Non-Goals

- No new backend endpoints.
- No logic changes to hunt status lifecycle.
- No deletion of resources/profile code.

