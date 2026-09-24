# Visual direction — an original identity, stronger than the mockup

The owner, 2026-09-24: make it "even more easy and better looking" with custom
OWL and whatever libraries truly help, re-read SAG's mockup to understand it,
and — explicitly — **"don't copy it, it is the idea: make it feel stronger and
design around that."**

So the mockup (`docs/mock-review/*.png`) is read for its *intent*: a legal
workspace that feels confident and official, with status you can read at a
glance, a company file you can scan body by body, and a matter page that tells
you what to do next. Its palette, layout and components are **not** reproduced.
This document is the design everyone builds to.

## Subject, audience, job

- **Subject:** Iraqi legal work: the file (الملف / الإضبارة), the court roll, the
  government counter, official letters and stamps, deadlines that forfeit rights.
- **Audience:** legal managers, lawyers and runners, Arabic first, often on a phone
  at a counter or in a court corridor.
- **Primary job of every screen:** say what must happen next, by when, and let it
  be done in one step.

## Tokens

| Token | Value | Use |
|---|---|---|
| Ink | `#14213D` | headings, the title band, the one primary action, structure |
| Ink soft | `#3B4A68` | secondary text on white |
| Paper | `#FFFFFF` | working surfaces |
| Desk | `#EEF1F5` | page background (cool grey, never cream) |
| Rule | `#D5DBE4` | hairlines, field borders |
| **Stamp violet** | `#5B3A9E` | *only* for what is officially confirmed: approved, confirmed genuine (صحة صدور), registered letter, issued opinion, signed agreement |
| Deadline red | `#B3122E` | overdue, missed, rejected |
| Amber | `#B96E00` (text) / `#FFF4DB` (fill) | due within 48 hours, missing documents |
| Green | `#1D6B45` / `#E6F4EC` | done, met, received |
| Blue | `#1D5FA0` / `#E7F0FA` | waiting on someone else (the body, the court, the client) |

Colour only ever means something. No gradients. Shadows only on things that float
(dialogs, dropdowns, the toast).

## Type

- **Noto Kufi Arabic** (OFL) for headings and the matter number: Kufi is the
  script of Kufa, in Iraq, and gives the official, confident weight the mockup
  reached for with colour. Weights 600/700.
- **IBM Plex Sans Arabic** (OFL) for everything else, with IBM Plex Sans for Latin:
  sturdy, very legible at small sizes on phones. Weights 400/500/600.
- Scale (px): 13 · 15 (body) · 18 · 22 · 28 (page title). Line height 1.6 for Arabic
  body text. Numbers in tabular figures inside lists and money.
- No all-caps labels, no eyebrow labels above headings, no single-word highlights.
- Both fonts are vendored as woff2 under `static/lib/fonts/` with their licences
  and applied inside `.o_ldm` only; Odoo's own screens are untouched.

## The one bold thing: the title band

Each workspace screen and the matter cockpit open with a solid ink band: the
screen's subject in Kufi (My Day: the date in Gregorian and Hijri and "what needs
you today"; the matter: its number and title, its client and body, its stage
pills). Everything below the band is quiet: white paper on the grey desk,
hairline rules, generous spacing. One amber-free primary action per screen, in
ink.

## The one motif: the stamp

A rounded-rectangle outline in stamp violet with a small Kufi word (معتمد، مؤكد
الصدور، مسجل، صادر) marks officially confirmed things, the way the paper file
carries a violet ministry stamp. It is used nowhere else, so it keeps its meaning.
The single orchestrated motion in the product belongs to it: when an approval or a
verification is recorded, the stamp lands (a short scale-and-settle, 180 ms,
skipped under reduced motion).

## Structure

- **Radii follow hierarchy:** bands 0, panels 10 px, inputs 6 px, pills fully round.
  Not every block is a card; lists are lists, separated by hairlines.
- **A kind spine:** matters show a 4 px start-edge spine in a quiet per-kind tint
  (lawsuit, government transaction, contract, opinion…) so a list reads by kind
  without badges.
- **Rows speak:** title (600), then client · body in ink-soft, then the reason in
  plain words ("ينتظر كتاب صحة الصدور من الهيئة منذ ٦ أيام عمل"), with the time
  left as a pill at the row's end. The largest text is always the title.
- **Status pills** use the token colours with a small Lucide icon; risk flags on
  rows come from real data (overdue, due in 48 h, urgent, at the body past target,
  missing documents).
- **The company file** is scanned body by body: each body a section with its
  services, a status pill per service and a thin completion bar; "Start" or "Open"
  at the row's end.
- **The matter page** keeps a strict order: title band → next step (with its one
  action, replaced by the approval notice while approval is pending) → vital
  facts → steps → documents → sessions/judgments → money → history.
- **The deadline suggestion** is a real calculation (matter type's working-day
  duration plus the body's usual answer time) shown as "Suggested target date"
  with "Use this date" — never called AI.
- **Charts** (managers' analytics only): Chart.js, flat fills in the token colours,
  direct labels instead of legends where possible, every bar or slice opens its
  matters.
- **Phones (390 px):** the band shrinks to one line, rows stack, actions become
  full-width, no horizontal scroll.

## Libraries (decided)

| Library | Why | Licence | How |
|---|---|---|---|
| OWL | every custom screen, inside Odoo's records, security, chatter, translations and RTL | LGPL | built in |
| Chart.js 4 | real charts on the analytics board | MIT | shipped by Odoo (`loadBundle("web.chartjs_lib")`) |
| Lucide (SVG subset) | one clean line-icon language, instead of Font Awesome 4 | ISC | `static/lib/lucide/` + `LdmIcon` component |
| Noto Kufi Arabic, IBM Plex Sans Arabic, IBM Plex Sans | the typography above | OFL | woff2 in `static/lib/fonts/` |
| FullCalendar, pdf.js, zxing, signature_pad | calendar, previews, QR, signatures | MIT/Apache | shipped by Odoo |
| TypeScript | not at runtime: Odoo 19 loads JS modules with no build step, so TS means committing compiled output SAG's developers cannot patch; type safety via JSDoc + `tsc --checkJs` in development | — | optional |
| React / Vue / Tailwind | no: they would sit beside Odoo's records and security rather than inside them, and Tailwind collides with Odoo's Bootstrap | — | — |

## What we deliberately do not take from the mockup

Its green-and-amber palette and layouts (we design our own), identical cards for
everything, a numbers-first dashboard as the landing screen, fabricated figures
and "AI" labels, emoji, and a React app beside Odoo.
