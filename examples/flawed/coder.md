# Spec sheet: Inbox (flawed on purpose) (for a coding AI)

Each screen is 800 x 600 px. The first screen is `inbox`.
Positions are the top-left corner of each block, in pixels.
A block's `event` is what it raises when the user uses it; transitions below say what happens next.
Every block also has a resolved style (built-in default for its type, then its named style, then its own overrides); see the table under each screen and the Styles section.

## Screen `inbox`: Inbox

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 20 | 300 | 40 | Inbox | inbox.title |  |  |
| `unread` | text | 20 | 80 | 300 | 40 | Unread: {{inbox.unread}} | inbox.unread |  |  |
| `badge` | badge | 340 | 80 | 160 | 40 | Unread: {{inbox.unread}} | inbox.unread |  | FLAW: shows the unread count a second time (duplicate-info, duplicate-label) |
| `messages` | list | 20 | 140 | 500 | 300 | Messages | inbox.messages |  |  |
| `promo` | text | 400 | 380 | 300 | 100 | Upgrade now! | inbox.promo |  | FLAW: sits on top of the message list (overlap) |
| `compose` | button | 20 | 500 | 160 | 48 | Compose | action.compose | compose | FLAW: raises 'compose' but no transition handles it (dead-control) |
| `settings` | button | 200 | 500 | 160 | 48 | Settings | action.settings |  | FLAW: a button that raises no event (button-without-event) |
| `archive` | button | 380 | 500 | 160 | 48 | Archive | action.archive | open_archive |  |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |
| `unread` | body | #ffffff | #333333 | #667788 | 0 | 0 | 4 | 14 | normal | left | 1 | false | - |
| `badge` | body | #ffe9b8 | #333333 | #667788 | 0 | 10 | 4 | 12 | normal | center | 1 | false | - |
| `messages` | body | #fafafa | #333333 | #667788 | 1 | 0 | 4 | 14 | normal | left | 1 | false | - |
| `promo` | body | #ffffff | #333333 | #667788 | 0 | 0 | 4 | 14 | normal | left | 1 | false | - |
| `compose` | primary | #2a6cf0 | #ffffff | #667788 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |
| `settings` | primary | #2a6cf0 | #ffffff | #667788 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |
| `archive` | primary | #2a6cf0 | #ffffff | #667788 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |

## Screen `archive`: Archive

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 20 | 300 | 40 | Archive | archive.title |  | FLAW: this screen has no way out and is not final (dead-end) |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |

## Screen `trash`: Trash (final)

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 20 | 300 | 40 | Trash | trash.title |  | FLAW: no transition leads here (unreachable-state) |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |

## Styles

- **body**: text_color=#333333. Used by: `inbox.unread`, `inbox.badge`, `inbox.messages`, `inbox.promo`
- **heading**: text_color=#1a2b4c, font_size=28, font_weight=bold. Used by: `inbox.title`, `archive.title`, `trash.title`
- **primary**: fill=#2a6cf0, text_color=#ffffff, radius=8, align=center. Used by: `inbox.compose`, `inbox.settings`, `inbox.archive`

## Sample data

Text such as `{{key}}` stands for a value; these are the sample values (live mode):

- `inbox.unread`: 12

## Transitions

- `inbox` --`open_archive`--> `archive`

## Iterations

If you are asked to refine this UI more than once, settle the number of passes first: use the number the user gave, ask if they gave none, and use 2 (saying so) if you cannot ask. Every pass after the first must change something you can name (a position, size, type, label or style, or removing duplicated information); if nothing is left to change, stop early and say so. Log each pass in one line: `Pass k of N: <what changed>, because <why>`.
