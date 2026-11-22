# Spec sheet: Dashboard (for a coding AI)

Each screen is 1280 x 800 px. The first screen is `overview`.
Positions are the top-left corner of each block, in pixels.
A block's `event` is what it raises when the user uses it; transitions below say what happens next.
Every block also has a resolved style (built-in default for its type, then its named style, then its own overrides); see the table under each screen and the Styles section.

## Screen `overview`: Overview

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `menu` | nav | 0 | 0 | 200 | 800 | Menu | nav.main |  |  |
| `title` | heading | 230 | 24 | 500 | 40 | Overview | overview.title |  |  |
| `revenue` | card | 230 | 90 | 300 | 120 | Revenue {{stats.revenue}} | stats.revenue |  |  |
| `orders` | card | 550 | 90 | 300 | 120 | Orders {{stats.orders}} | stats.orders |  |  |
| `users` | card | 870 | 90 | 300 | 120 | Active users {{stats.users}} | stats.users |  |  |
| `recent` | table | 230 | 240 | 940 | 420 | Recent orders | orders.recent |  |  |
| `report` | button | 1000 | 700 | 170 | 48 | View report | action.open_report | open_report |  |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `menu` | chrome | #1a2b4c | #ffffff | #667788 | 1 | 0 | 4 | 14 | bold | left | 1 | false | options=Overview / Orders / Customers |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |
| `revenue` | card | #f7f8fa | #222222 | #c9ced8 | 1 | 10 | 12 | 14 | normal | left | 1 | true | - |
| `orders` | card | #f7f8fa | #222222 | #c9ced8 | 1 | 10 | 12 | 14 | normal | left | 1 | true | - |
| `users` | card | #f7f8fa | #222222 | #c9ced8 | 1 | 10 | 12 | 14 | normal | left | 1 | true | - |
| `recent` | body | #fafafa | #333333 | #667788 | 1 | 0 | 4 | 14 | normal | left | 1 | false | - |
| `report` | primary | #2a6cf0 | #ffffff | #667788 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |

## Screen `report`: Report

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 230 | 24 | 500 | 40 | Monthly report | report.title |  |  |
| `month` | text | 230 | 90 | 500 | 40 | Revenue this month: {{report.month_revenue}} | report.month_revenue |  |  |
| `back` | button | 230 | 700 | 200 | 48 | Back to overview | action.back | back |  |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |
| `month` | body | #ffffff | #333333 | #667788 | 0 | 0 | 4 | 14 | normal | left | 1 | false | - |
| `back` | primary | #2a6cf0 | #ffffff | #667788 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |

## Styles

- **body**: text_color=#333333. Used by: `overview.recent`, `report.month`
- **card**: fill=#f7f8fa, border_color=#c9ced8, border_width=1, radius=10, shadow=True. Used by: `overview.revenue`, `overview.orders`, `overview.users`
- **chrome**: fill=#1a2b4c, text_color=#ffffff. Used by: `overview.menu`
- **heading**: text_color=#1a2b4c, font_size=28, font_weight=bold. Used by: `overview.title`, `report.title`
- **primary**: fill=#2a6cf0, text_color=#ffffff, radius=8, align=center. Used by: `overview.report`, `report.back`

## Sample data

Text such as `{{key}}` stands for a value; these are the sample values (live mode):

- `report.month_revenue`: $48,900
- `stats.orders`: 318
- `stats.revenue`: $12,400
- `stats.users`: 1,092

## Transitions

- `overview` --`open_report`--> `report`
- `report` --`back`--> `overview`

## Iterations

If you are asked to refine this UI more than once, settle the number of passes first: use the number the user gave, ask if they gave none, and use 2 (saying so) if you cannot ask. Every pass after the first must change something you can name (a position, size, type, label or style, or removing duplicated information); if nothing is left to change, stop early and say so. Log each pass in one line: `Pass k of N: <what changed>, because <why>`.
