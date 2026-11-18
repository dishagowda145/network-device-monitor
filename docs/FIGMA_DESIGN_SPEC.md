# Figma Design Spec: Network Device Monitor

**Ready-made screens are in [`design/`](design/).** Drag the `.svg` files into Figma, then follow the steps below to turn them into a proper design file (components, styles, Auto Layout).

Design every screen below in Figma first, then build the React UI to match it. Use this as the brief a product designer would hand you.

## Screens to design

| # | Screen | Desktop (1440) | Mobile (375) |
| --- | --- | --- | --- |
| 1 | Dashboard | Header, 3 summary cards (Devices, Up, Down), then 2 columns: left "Add a device" form and alerts, right device cards grid | One column in the same order |
| 2 | Device selected | Selected card has a 2 px brand outline; the history panel opens on the left | History rows wrap: bar moves to its own line |
| 3 | Empty state | "No devices yet. Add one to start monitoring." | Same |
| 4 | Error state | Red message under the form (for example "Port must be between 1 and 65535") | Same |

## Components to build (with variants)

| Component | Variants / states |
| --- | --- |
| Summary card | Devices (blue edge), Up (green edge), Down (red edge); big count plus label |
| Device card | Up, Down, Unknown (4 px coloured top edge); Selected (outline) |
| Status pill | UP, DOWN, UNKNOWN |
| Button | Primary, Secondary, Danger; Default, Hover, Focus, Disabled |
| Input | Default, Focus, Error |
| History row | Dot (12), time (150), response bar (flexible), milliseconds (60) |
| Alert item | Down (red edge), Recovered (green edge) |

## Layout rules

- Page content max width 1050 px, centred, 16 px padding
- Columns 1fr and 2fr with 16 px gap (1 column below 760 px)
- Device cards: grid with at least 260 px per card and 12 px gap
- Response bar: 8 px high, rounded, length proportional to the slowest check shown


## How to do this (about 3 to 4 hours)

1. Create a free Figma account and a new **Design file** named "Network Device Monitor".
2. Make two pages: **Design System** and **Screens**.
3. **Design System page:** create the colour, text and spacing styles from the tables below (use *Local styles* / *Variables*). Build each component once, using Auto Layout, and make variants for its states.
4. **Screens page:** make a **Desktop** frame (1440 wide) and a **Mobile** frame (375 wide) for every screen. Use Auto Layout and constraints so the layout resizes.
5. Name layers like the code (`card`, `panel`, `badge`), so the Figma file and the React code stay easy to compare.
6. Share the file: **Share > Anyone with the link can view**. Paste the link into `README.md` in place of `FIGMA_LINK_HERE`, and into your resume and LinkedIn.
7. Put a screenshot of each frame in `docs/screenshots/` so recruiters see the design without opening Figma.

## Colour styles (match the CSS variables in `frontend/styles.css`)

| Name | Hex | Used for |
| --- | --- | --- |
| Background | `#F4F7FB` | Page background |
| Panel | `#FFFFFF` | Cards and panels |
| Text | `#17212B` | Main text |
| Muted | `#5B6B7B` | Labels, helper text |
| Brand | `#0B6BCB` | Buttons, focus ring, response bars |
| Border | `#DBE3EC` | Outlines |
| Up | `#1B8A4B` | Device is reachable |
| Down | `#C62828` | Device is not reachable |
| Unknown | `#8A96A3` | No check yet |
| Pill up | bg `#DFF3E7`, text `#135D32` | UP pill |
| Pill down | bg `#FDE4E4`, text `#8E1D1D` | DOWN pill |
| Alert down | bg `#FFF4F4`, edge `#C62828` | Down alert |
| Alert recovered | bg `#F1FAF4`, edge `#1B8A4B` | Recovered alert |

## Text styles

Figma cannot use the system font stack, so design with **Inter**, which looks almost identical. The code uses `system-ui`.

| Style | Size / Weight | Used for |
| --- | --- | --- |
| Heading 1 | 32 / Bold (26 on mobile for the long title) | Page title |
| Heading 2 | 18 / Bold | Panel titles |
| Count | 29 / Bold | Numbers on summary cards |
| Body | 16 / Regular | Normal text |
| Label | 14 / Regular, muted colour | Form labels |
| Small | 13 / Regular, muted colour | Timestamps, helper text |
| Badge | 12 / Regular | Status and priority badges |

## Spacing and shape

- Spacing scale: 4, 8, 12, 16, 24, 32 px (the code uses 0.25rem to 2rem)
- Corner radius: inputs and buttons 8 px, cards 10 px, panels 12 px, badges fully round
- Border: 1 px `Border` colour. Cards have a 4 to 5 px coloured edge showing their status.

## Build it exactly like Figma (the JD's preferred skill)

Do this after the design is done:

1. Open the file in **Dev Mode** (toggle top right). Click any element to see its exact size, colour, padding and font.
2. For each frame, open the running app next to Figma at the same width (1440 and 375) and compare.
3. Fix every difference in `styles.css`: spacing, font size, colours, radius, alignment.
4. Put the Figma frame and a screenshot of the finished page side by side in `docs/screenshots/` (name them `home-figma.png` and `home-app.png`).
5. Tick the issue "Match the UI to the Figma design" only when both match at 1440 and 375 px.
6. In interviews, say: *"I reviewed the mockup in Dev Mode and built the UI to match it, checking spacing, colour and type at desktop and mobile widths."*

## Accessibility checks (good UX practice)

- Text contrast of at least 4.5 to 1 (use Figma's free "Stark" or "A11y" plugin)
- Every input has a visible label, and error text is not shown by colour alone
- Buttons are at least 40 px tall on mobile
- Status is shown with text as well as colour (for example the "UP" and "DOWN" pills)

