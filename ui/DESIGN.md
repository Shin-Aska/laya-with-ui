# Laya Playground design system

## Reference

The user supplied a 1762×954 Typesafe AI/Jev Playground screenshot on 24 September 2026. It sets the layout direction: a slim navigation rail, two stacked editors, a pinned Run bar, and a wide response table. Laya branding, copy, and inference remain its own. The UI is interactive React DOM, not a screenshot.

## Tokens

`app/globals.css` owns the palette, fonts, type scale, common spacing, control radii, column widths, and bar heights as CSS custom properties. Surface, ink, subdued text, dividers, selected navigation, probability marks, error, warning, and focus colors use semantic tokens. Component rules use these tokens for shared values; one-off measurements such as a ring diameter stay with the component. The type scale is 9, 10, 11, 12, 13, 14, 15, and 16px. The two font families are system sans-serif and Consolas with monospace fallbacks.

## Geometry

At 1762px, the rail is 256px, the editor column is about 625px, and the response fills the rest. Toolbars are 38px tall; the Run bar is 42px. State and Questions scroll independently within the editor column, and the response list has its own scroll. At 1150px the rail and editor minimum widths shrink. At 990px the editor and response stack. At 700px the rail becomes a horizontal top menu. At 520px the toolbars and Run bar adapt to phone width. CSS media-query thresholds remain literal because custom properties cannot be used in media-query conditions.

## Component and style patterns

`CodeEditor`, `ProbabilityMark`, and `ResponseRow` are React components in `app/page.tsx`. Navigation, toolbar controls, sample picker, status, Run bar, notices, and response view controls are semantic elements composed in `Page` and styled by the corresponding named CSS classes. These patterns share tokens and interaction states, but are not separate exported React components.

The response uses question rows and hairline dividers instead of cards. Choice rows show ranked options and probabilities. Score and yes/no questions use the same row structure with their own values. Confidence is labeled as model confidence, not measured accuracy. State and Questions editors preserve the supplied JSON shape.

## Interaction and accessibility

Buttons and selected rows use short 120ms color transitions; the running state uses a restrained spinner. Reduced-motion disables both. Navigation and main regions are semantic. State and Questions have labels, errors identify their editor, and visible focus is present. Narrow-screen interactive targets are at least 40px high where space permits. A backend outage shows the local startup command. The UI sends parsed input to the Python API and shows actual Laya results, which can differ from the Jev screenshot.

## Scope

The local UI uses a same-origin proxy to reach the loopback Python API. Users enter no service URL or token. A hosted deployment would need separate backend hosting and authentication configuration.
