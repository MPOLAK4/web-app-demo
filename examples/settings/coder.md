# Spec sheet: Settings (for a coding AI)

Each screen is 800 x 600 px. The first screen is `settings`.
Positions are the top-left corner of each block, in pixels.
A block's `event` is what it raises when the user uses it; transitions below say what happens next.
Every block also has a resolved style (built-in default for its type, then its named style, then its own overrides); see the table under each screen and the Styles section.

## Screen `settings`: Settings

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 20 | 400 | 40 | Settings | settings.title |  |  |
| `name` | input | 20 | 90 | 360 | 44 | Display name | settings.name |  |  |
| `notify` | toggle | 20 | 160 | 360 | 40 | Email notifications | settings.notifications |  |  |
| `language` | select | 20 | 220 | 360 | 44 | Language | settings.language |  |  |
| `volume` | slider | 20 | 290 | 360 | 40 | Volume | settings.volume |  |  |
| `cancel` | button | 20 | 520 | 160 | 48 | Cancel | action.cancel | cancel |  |
| `save` | button | 600 | 520 | 180 | 48 | Save changes | action.save | save |  |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |
| `name` | field | #ffffff | #222222 | #c9ced8 | 1 | 6 | 4 | 14 | normal | left | 1 | false | value="{{user.name}}" |
| `notify` | field | #ffffff | #222222 | #c9ced8 | 1 | 6 | 4 | 14 | normal | left | 1 | false | - |
| `language` | field | #ffffff | #222222 | #c9ced8 | 1 | 6 | 4 | 14 | normal | left | 1 | false | options=English / Espanol / Deutsch |
| `volume` | field | #ffffff | #222222 | #c9ced8 | 1 | 6 | 4 | 14 | normal | left | 1 | false | - |
| `cancel` | secondary | #ffffff | #2a6cf0 | #2a6cf0 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |
| `save` | primary | #2a6cf0 | #ffffff | #667788 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |

## Screen `saved`: Saved (final)

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 20 | 400 | 40 | Settings saved | saved.title |  |  |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |

## Screen `closed`: Closed (final)

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 20 | 400 | 40 | Closed without saving | closed.title |  |  |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |

## Styles

- **field**: fill=#ffffff, border_color=#c9ced8, border_width=1, radius=6. Used by: `settings.name`, `settings.notify`, `settings.language`, `settings.volume`
- **heading**: text_color=#1a2b4c, font_size=28, font_weight=bold. Used by: `settings.title`, `saved.title`, `closed.title`
- **primary**: fill=#2a6cf0, text_color=#ffffff, radius=8, align=center. Used by: `settings.save`
- **secondary**: fill=#ffffff, text_color=#2a6cf0, border_color=#2a6cf0, border_width=1, radius=8, align=center. Used by: `settings.cancel`

## Sample data

Text such as `{{key}}` stands for a value; these are the sample values (live mode):

- `user.name`: Sam Rivera

## Transitions

- `settings` --`save`--> `saved`
- `settings` --`cancel`--> `closed`

## Iterations

If you are asked to refine this UI more than once, settle the number of passes first: use the number the user gave, ask if they gave none, and use 2 (saying so) if you cannot ask. Every pass after the first must change something you can name (a position, size, type, label or style, or removing duplicated information); if nothing is left to change, stop early and say so. Log each pass in one line: `Pass k of N: <what changed>, because <why>`.
