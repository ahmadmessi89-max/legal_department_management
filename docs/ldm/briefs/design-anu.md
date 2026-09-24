# Design direction: the ANU identity

*Binding for every screen of `legal_department_management` from 24 September
2026. Supersedes `design-direction.md` (the identity built around SAG's
mockup), which the owner judged flat and without character. His direction:
follow anu.ltd, and use the design skills, the MCP tools and professional
component patterns.*

## Where it comes from

Read from the live site on 24 September 2026 (computed styles, not guesses):

- anu.ltd is built on **shadcn/ui**: its CSS variables are shadcn's token set.
  Primary is ink `#090B11`, accent electric blue `#2563EB`, secondary and muted
  `#F1F5F9`, muted text `#64748B`, borders `#E2E8F0`, ring `#64748B`.
- Type: **Inter Tight** for everything Latin (display at weight 400 with
  tracking −3%, body 16px), **Tajawal** for Arabic at the same light weight,
  **Roboto Mono** for actions, indices and utility labels (uppercase in
  English, 13px, −0.26px tracking).
- Surfaces: ink `#090B11` bands carrying a faint blue line-network
  (the hero's constellation), and bone-white `#F8FAFC` sections holding
  white paper.
- Components: a floating segmented bar (white at 92%, radius 16, hairline
  `rgba(9,11,17,.08)`, shadow `0 18px 40px -26px rgba(0,0,0,.45)`, items
  12×16, active item with a 2px blue underline); the primary action as a blue
  gradient `135deg #2563EB → #1D4ED8` with a blue glow
  `0 12px 22px -22px rgba(37,99,235,.75)`; pill chips (white, radius 20,
  hairline `#E2E8F0`, 13px slate `#475569`, a 1px lift).

## Tokens

| Name | Value | Role |
|---|---|---|
| Ink | `#090B11` | structure: the band, the navbar, headings, the secondary button's text |
| Signal | `#2563EB` (hover `#1D4ED8`, soft `#EFF6FF`, ring `rgba(37,99,235,.35)`) | the one accent: the screen's primary action, the active item, focus, links |
| Bone | `#F8FAFC` | the canvas every screen sits on |
| Paper | `#FFFFFF` | cards, tables, forms, dialogs |
| Slate | `#475569` / `#64748B` | secondary and muted text |
| Lichen | `#E2E8F0` | hairlines and borders |

Status keeps four meanings, drawn as shadcn "soft" badges (tinted fill, strong
text, no border): overdue or rejected red `#DC2626` on `#FEF2F2`; due soon or
missing amber `#B45309` on `#FFFBEB`; done or received green `#15803D` on
`#F0FDF4`; waiting on someone else blue, the Signal on `#EFF6FF`. Anything
officially confirmed (approved, confirmed genuine, registered, issued,
signed) carries the **seal**: an ink hairline pill with a blue check, instead
of the old violet stamp.

Type roles: Inter Tight 400/500/600 for Latin UI and display; Tajawal
400/500/700 for Arabic; Roboto Mono 400/500 for numbers that line up (matter
numbers, amounts, counts, dates in tables) and for action labels in English.
Scale 12 · 13 · 15 · 18 · 24 · 32 · 44, display sizes tracked −2 to −3%.
Arabic never below 13px, line-height 1.6.

Shape follows hierarchy: floating bars and dialogs 16, cards 12, controls 8,
chips and pills fully round. Depth has three levels: the canvas (bone), paper
(white, hairline, `0 1px 2px rgba(9,11,17,.05)`), and floating (the segmented
bar's long soft shadow, used for bars, menus and dialogs only).

## Layout

- Every workspace screen opens with the **ink band**: the date or the matter's
  title set large and light (Inter Tight or Tajawal 400, tracked tight), the
  meta line in slate-on-ink, and a faint blue line-network in the far corner,
  anu.ltd's hero reduced to a texture. This is the one bold element; nothing
  else on the screen competes with it.
- Directly under the band, **floating** on its lower edge, the screen's
  controls in ANU's segmented bar: the scope switch (me / my team / everyone),
  the search, the one primary action in Signal blue with its glow.
- Below, bone canvas with paper: lists stay lists (shadcn table rhythm:
  12.5px muted headers, 44px rows, hairlines, a muted hover), panels are
  cards with a small header. Not everything becomes a card.
- Native Odoo views inside the Legal app get the same system: ink navbar with
  a blue underline under the active menu, paper sheets on bone, notebooks as
  underlined segmented tabs, status bars as a quiet segmented track, primary
  buttons in Signal blue, secondary in shadcn outline.

```
┌──────────────────────────── ink band ─────────────────────── ░network░ ┐
│  Thursday 24 September 2026                                            │
│  Rabiʿ II 13 · 5 overdue · 10 today · Lawyer                           │
└──────┬──────────────────────────────────────────────────────────┬─────┘
       │ Me │ My team │ Everyone ┃ 🔍 Search by number…  ┃ ＋ New matter │  ← floating bar
       └──────────────────────────────────────────────────────────┘
  bone ┌ Overdue 5 ─────────────────────────┐ ┌ The next seven days ┐
       │ row · row · row  (paper, hairlines) │ │ day groups           │
```

## Principles

1. **One accent.** Blue marks the action and the active thing. Status tints
   are meanings, not decoration; the kinds of matter lose their colours and
   keep an icon.
2. **The band is the character.** Ink, light large type, the network texture.
   Everything under it is quiet and exact.
3. **Numbers are mono.** Matter numbers, money, counts and dates in tables
   line up in Roboto Mono, the way anu.ltd sets its indices.
4. **Finish like a component library.** Every control has hover, active,
   focus (3px ring), disabled and loading states; menus and dialogs float;
   motion only answers an action (a row settling after "Done", a seal landing).
5. **Arabic first.** Tajawal sets the rhythm; mirrored layouts come from
   logical properties; numbers and phones stay left to right.

## Checked against the generic defaults

- *Near-black with one bright accent* is a default look, but here it is the
  client's brand, so it stays. What keeps it from being generic: the band
  is a strip rather than a dark theme, the canvas is bone-white paper, and
  the network texture is anu.ltd's own motif.
- *SaaS card kit* (identical rounded cards, one radius, one grey shadow): refused.
  Radii vary with hierarchy, lists stay tables, and the floating shadow is
  kept for things that really float.
- *Mono for small labels*: taken from the brand. It is limited to numbers,
  indices and English action labels; Arabic labels stay Tajawal.
- *All-caps labels*: only the English action labels, as the brand does. No
  all-caps eyebrows over headings.

## Tools

The frontend-design skill set this process (plan, check against defaults,
build, critique from screenshots). The shadcn MCP registry gave the component
patterns, ported to Odoo SCSS and OWL. Lucide icons stay, since shadcn uses
them too. The accessibility MCP audits contrast and focus, and every screen is
judged from a Playwright capture.
