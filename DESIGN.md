---
name: Apple Music Skip Fix
description: A calm Windows repair desk with a visible next step and a way back.
colors:
  raspberry: "#B22B47"
  raspberry-hover: "#97213B"
  raspberry-dark-theme: "#F1879D"
  light-background: "#FFFFFF"
  light-surface: "#F4F5F8"
  light-ink: "#202735"
  light-muted: "#566174"
  light-line: "#D7DCE5"
  light-active: "#F8E9EE"
  dark-background: "#191C22"
  dark-surface: "#22262E"
  dark-ink: "#F2F3F6"
  dark-muted: "#B7BFCC"
  dark-line: "#3F4754"
  dark-field: "#2B303A"
  dark-active: "#412B35"
  mark-raspberry: "#C73854"
  mark-ink: "#17292B"
typography:
  headline:
    fontFamily: "Segoe UI"
    fontSize: "29px"
    fontWeight: 600
  title:
    fontFamily: "Segoe UI"
    fontSize: "17px"
    fontWeight: 600
  intro:
    fontFamily: "Segoe UI"
    fontSize: "15px"
  body:
    fontFamily: "Segoe UI"
    fontSize: "14px"
  button:
    fontFamily: "Segoe UI"
    fontSize: "14px"
    fontWeight: 600
  step:
    fontFamily: "Segoe UI"
    fontSize: "13px"
  caption:
    fontFamily: "Segoe UI"
    fontSize: "12px"
  technical:
    fontFamily: "Consolas"
    fontSize: "12px"
rounded:
  step: "8px"
  button: "7px"
  field: "6px"
  scroll-thumb: "4px"
spacing:
  small: "8px"
  control: "10px"
  field: "12px"
  section: "18px"
  compact: "24px"
  footer: "28px"
  wide: "36px"
components:
  button-primary:
    backgroundColor: "{colors.raspberry}"
    textColor: "{colors.light-background}"
    typography: "{typography.button}"
    rounded: "{rounded.button}"
    padding: "10px 15px"
  button-primary-hover:
    backgroundColor: "{colors.raspberry-hover}"
  button-secondary-light:
    backgroundColor: "{colors.light-background}"
    textColor: "{colors.light-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.button}"
    padding: "10px 15px"
  button-secondary-dark:
    backgroundColor: "{colors.dark-field}"
    textColor: "{colors.dark-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.button}"
    padding: "10px 15px"
  step-current-light:
    backgroundColor: "{colors.light-active}"
    textColor: "{colors.raspberry}"
    typography: "{typography.step}"
    rounded: "{rounded.step}"
    padding: "13px 10px"
  step-current-dark:
    backgroundColor: "{colors.dark-active}"
    textColor: "{colors.raspberry-dark-theme}"
    typography: "{typography.step}"
    rounded: "{rounded.step}"
    padding: "13px 10px"
  theme-field-light:
    backgroundColor: "{colors.light-background}"
    textColor: "{colors.light-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.field}"
    padding: "7px 12px"
  theme-field-dark:
    backgroundColor: "{colors.dark-field}"
    textColor: "{colors.dark-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.field}"
    padding: "7px 12px"
  fact-row:
    typography: "{typography.body}"
    padding: "10px 0"
  technical-detail:
    typography: "{typography.technical}"
    rounded: "{rounded.field}"
    padding: "8px"
---

# Design System: Apple Music Skip Fix

## Overview

**Creative North Star: "The Windows Repair Desk"**

A calm Windows repair desk, organized around a single recoverable task. The next action is always visible and verification is earned. The approved direction in PRODUCT.md and docs/SURFACE.md supplies this language; this document captures the built system rather than proposing a replacement identity.

This is a native Windows desktop interface built with PySide6 Qt Widgets. A quiet step rail, a clear work area and a persistent action footer carry the workflow. Raspberry marks the current step and primary action; neutral surfaces, ruled facts and Segoe UI keep findings easy to scan. The original music-and-check SVG provides the only illustrated brand mark.

**Key Characteristics:**

- Six named stages with one primary action in the footer.
- Neutral light and dark themes with restrained raspberry emphasis.
- Ruled fact rows, open spacing and expandable local technical detail.
- Compact windows scroll their work area while preserving the action footer.
- Recovery and verification remain explicit, separately labeled states.

**Evidence and limits:** Extracted from src/amsf/gui.py and src/amsf/resources/icon.svg; visually checked against docs/images/check-light.png, result-dark.png, authorize-compact.png and check-200-percent.png. All four PNGs include embedded provenance identifying native Qt demo captures with synthetic data. They establish rendered appearance, not real playback, actual user data or repair efficacy. The finish reviewer reported SHIP for the reviewed UI/finding scope after 42 synthetic tests; that verdict does not establish live adapter, installer or repair behavior. Browser rendering and web design detectors do not apply to this Qt Widgets surface.

## Colors

One raspberry family sits within cool neutral light and dark themes. The frontmatter is the normative color source; runtime assignments remain in MainWindow.set_theme.

### Primary

- **Repair Raspberry** (`raspberry`): primary button fill in both themes; current-step text and focus/hover borders in light theme.
- **Deep Raspberry** (`raspberry-hover`): the implemented primary hover fill. No separate pressed-state fill is implemented.
- **Soft Raspberry** (`raspberry-dark-theme`): current-step text, focus/hover borders and progress chunks in dark theme. The primary button retains Repair Raspberry with white text.
- **Mark Raspberry** (`mark-raspberry`): the authored SVG tile. Keep it distinct from the button fill; it belongs to the icon artwork.

### Neutral

- **Light Paper** (`light-background`): window, work area, header, footer and light-theme fields; also the white primary-button text.
- **Cool Mist** (`light-surface`): light rail, technical detail background, secondary hover and disabled surfaces.
- **Slate Ink / Slate Caption** (`light-ink`, `light-muted`): primary and supporting text in light theme.
- **Light Rule / Raspberry Wash** (`light-line`, `light-active`): light dividers and borders; current-step and status backgrounds.
- **Night Paper / Raised Night / Night Field** (`dark-background`, `dark-surface`, `dark-field`): dark work area; rail, technical detail and hover surfaces; secondary buttons and combo fields.
- **Pale Ink / Pale Caption** (`dark-ink`, `dark-muted`): primary and supporting text in dark theme.
- **Night Rule / Raspberry Shade** (`dark-line`, `dark-active`): dark dividers and borders; current-step and status backgrounds.
- **Mark Ink** (`mark-ink`): the check badge inside the original SVG, independent of the theme palette.

**The State Is Text Rule.** Always label current, complete, unresolved and restored states in words. Accent, background and disabled styling reinforce those distinctions.

System theme is selected from Qt's color-scheme hint when the theme is applied. The header also offers explicit Light and Dark choices. Do not claim a separate live operating-system theme-change listener: none is implemented here.

## Typography

**Interface Font:** Segoe UI, requested directly by the Qt stylesheet. **Technical Font:** Consolas for the read-only detail viewer. No web font, custom font download or explicit fallback stack is configured.

Segoe UI carries both brand and task copy. The hierarchy is compact and practical: a single large task headline, a short muted introduction, then facts and actions. Native Qt/Windows font metrics supply line spacing; the implementation does not set line-height or letter-spacing tokens.

### Hierarchy

- **Headline** (`headline`): the stage heading; semibold and sentence case.
- **Title** (`title`): brand name and in-page subheadings.
- **Introduction** (`intro`): muted stage explanation.
- **Body** (`body`): facts, instructions, checkbox labels and secondary controls.
- **Primary action** (`button`): semibold footer action.
- **Step** (`step`): rail names and descriptions; the current step gains semibold weight.
- **Caption** (`caption`): brand promise, supporting caveats, compact step indicator and local-file reassurance.
- **Technical** (`technical`): local machine-readable detail in a read-only editor.

Labels wrap with Qt word wrapping and use plain text. Most QLabel content is mouse-selectable. Preserve sentence case and the existing English UI; do not replace compact captions with decorative all-caps labels.

## Layout

The nominal window is 1060 × 760 and the minimum is 680 × 440, measured in Qt logical pixels. The outer layout has zero margins and no gaps between the header, middle area and footer surfaces.

The header spans the window. Its margins are 24 horizontally and 16 vertically. A 38 × 38 rendering of the authored SVG sits beside a two-line brand block; the theme selector aligns right. The brand name has a 260 minimum width.

At widths of 900 and above, the left rail is fixed at 228. Its margins are 24 left, 30 top, 20 right and 24 bottom, with 8 between step entries. Recovery reassurance and version/project attribution sit at its bottom. The six stage labels are progress indicators, not clickable navigation.

Below 900, the rail is hidden and a compact `Step n of 6 · Name` indicator appears above the work area. Its margins are 28 horizontally and 14 at the top. Content margins are 24 on all sides in compact mode. In wide mode they are 36 horizontally and 24 vertically after responsive layout is applied. Content spacing is 18. The initial builder's 30 top margin is superseded by apply_responsive; use the applied values when extending the layout.

The work area is a frameless, widget-resizable QScrollArea. A stretch below the stage content keeps short pages aligned to the top. The 760 × 580 authorization capture visibly scrolls its instructions; the footer stays in place. The footer has 28 horizontal and 18 vertical margins, the restore action on the left when available and the primary action on the right. The primary action has a minimum height of 44. Status text and a 3-high indeterminate progress bar occupy rows above the footer when needed.

**The Anchored Action Rule.** Keep the primary action in the footer outside the scrolling stage. At small sizes or enlarged DPI, scroll content rather than moving the action below it.

The 200% capture is 1800 × 1360 raster pixels. Treat screenshot pixels separately from Qt logical layout values; use Qt's DPI scaling. That capture verifies one enlarged rendering, not every display or window size between 100% and 200%.

## Elevation & Depth

The application defines no shadows, blur, gradients or hover lift. Depth comes from the rail's contrasting surface tone, subtle 1-pixel rules and filled control backgrounds. Header and footer dividers establish stable boundaries; facts use bottom rules rather than cards. Native Windows/Qt popup and dialog rendering is platform-owned, not an additional application shadow vocabulary.

**The Flat Desk Rule.** Use tonal separation and rules for ordinary structure; preserve the open work area without inventing floating card containers.

## Shapes

Controls have small, steady curves: buttons use the button radius, combo fields and technical viewers use the field radius, and active rail entries use the step radius. Facts have square, borderless sides and a bottom rule. The vertical scrollbar is 10 wide with a rounded thumb and a 28 minimum thumb height; add/sub-line controls have zero height.

The authored SVG is a raspberry rounded tile with a white music note and a dark circular check badge. It is original vector artwork, not an Apple logo. Use the existing SVG and packaged icon assets; screenshots are synthetic product evidence rather than decoration. This system does not require generated raster illustrations.

## Components

### Buttons

Buttons are compact and legible, with a 1-pixel border and padding defined in the frontmatter. The footer's single primary button uses Repair Raspberry and white semibold text in both themes. Secondary buttons use the theme field background and normal interface text. In the stage area, secondary actions expand to the available layout width; footer buttons remain content-sized.

Hover changes the secondary background to the theme surface and the border to its accent. Primary hover uses the darker raspberry fill. Focus for buttons, combos and checkboxes is an explicit 2-pixel theme-accent border. Disabled buttons use muted text, theme surface and line border, including the primary button. There is no custom active/pressed animation.

### Progress rail and compact indicator

Each rail entry includes its number, stage name and a short description. Current uses the theme active fill, accent text and semibold weight; earlier entries use normal ink; upcoming entries use muted text. Accessible names explicitly say current step, complete or upcoming. At the compact breakpoint the rail is replaced by the single textual step indicator, preserving stage context.

### Fact rows and status

Facts present `Label · Value` as plain text with vertical padding and a bottom rule. The same structure communicates protection promises, backup state, verification and results. They are rows, not interactive cards. Status text uses the active-tint background and normal ink; it is separate from the stage facts and can display progress, validation or recovery instructions without implying success by color alone.

### Selection controls

The header QComboBox offers System theme, Light and Dark. The optional offline-result combo separately represents not tested, user-confirmed playback and failure. Combos have a 105 minimum content width, field padding, a line border and the field radius; their selected popup row uses the active fill and normal ink.

QCheckBox uses an 18 × 18 indicator, 10 spacing from its text and 5 vertical padding. The glyph itself remains Qt/Windows-rendered. Confirmations are explicit: symptom match, permission to close Apple Music for protection, authorization completed inside Apple Music, and continuous audible playback. Do not imply that a checked demo checkbox is real evidence.

### Technical disclosure

`View technical details` toggles a read-only QPlainTextEdit. It begins collapsed, uses the technical font, theme surface, line border, field radius, 8 padding and a maximum height of 130. The action has an accessible expand/collapse description. There is no editable credential field: passwords and verification codes belong in Apple Music's window.

### Busy, verification and recovery states

Background work disables the page, primary action and restore action, shows an indeterminate progress bar and reports text above the footer. Completion or error re-enables those controls; an error leaves a readable recovery message. Closing the window while work is busy is refused with a status explanation. The theme selector remains in the shell.

Each stage change resets the scroll position and puts focus on the primary action. Advancing still validates the relevant confirmation. Playback progress observation, the user's audible-playback confirmation and optional offline playback are distinct evidence. If Windows observation is unavailable, the manual 30-second confirmation is shown and the result is labeled as user-confirmed. Do not turn an authorization click into a playback success state.

`Restore previous cache` is visible only for recoverable session states and remains a secondary footer action. Its native confirmation dialog explains that the new cache is preserved and the original cache returns. Result copy distinguishes confirmed playback, unconfirmed repair and previous-cache restoration. After restoration, earlier playback confirmations are historical and offline playback requires a new check. Retry authorization, sanitized report export, local recovery access and project help are separate actions.

The sidecar supplies self-contained HTML/CSS previews of selected visual patterns because the documentation panel accepts those formats. They are illustrative translations of native Qt controls, not shipping web components or substitutes for native keyboard, accessibility or dialog behavior. Generated tonal ramps in that sidecar are swatch previews only; runtime themes use the exact frontmatter colors.

## Do's and Don'ts

### Do:

- **Do** preserve the six named stages and keep one primary footer action visible while the work area scrolls.
- **Do** use the existing light/dark token assignments, including the fixed raspberry primary fill and the softer dark-theme accent.
- **Do** preserve native Qt controls, visible keyboard focus, wrapped copy and the compact step indicator.
- **Do** keep authorization, playback progress, audible confirmation, offline testing and restored-cache results separately labeled.
- **Do** retain synthetic-data notices and embedded provenance when sharing demo screenshots.
- **Do** use the existing authored vector mark and keep technical detail collapsed until requested.

### Don't:

- **Don't** replace the approved Windows assistant with a website, mobile screen or decorative card dashboard.
- **Don't** add shadows, gradients, hover lift or decorative animation to the flat visual system.
- **Don't** make rail labels behave like unrestricted stage navigation.
- **Don't** display credentials in the assistant or imply that opening Apple Music proves authorization or playback.
- **Don't** present synthetic screenshot outcomes or the UI review verdict as proof of a live repair or a universal success rate.
- **Don't** reuse historical playback confirmations as current evidence after restoring the previous cache.
