# Spec sheet: Login (for a coding AI)

Each screen is 390 x 844 px. The first screen is `login`.
Positions are the top-left corner of each block, in pixels.
A block's `event` is what it raises when the user uses it; transitions below say what happens next.
Every block also has a resolved style (built-in default for its type, then its named style, then its own overrides); see the table under each screen and the Styles section.

## Screen `login`: Sign in

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 60 | 350 | 40 | Welcome | login.title |  |  |
| `email` | input | 20 | 140 | 350 | 44 | Email | login.email |  |  |
| `password` | input | 20 | 200 | 350 | 44 | Password | login.password |  |  |
| `remember` | checkbox | 20 | 260 | 350 | 32 | Keep me signed in | login.remember |  |  |
| `submit` | button | 20 | 320 | 350 | 48 | Sign in | action.submit | submit | Two outcomes: see the two guarded transitions |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |
| `email` | field | #ffffff | #222222 | #c9ced8 | 1 | 6 | 4 | 14 | normal | left | 1 | false | placeholder="you@example.com" |
| `password` | field | #ffffff | #222222 | #c9ced8 | 1 | 6 | 4 | 14 | normal | left | 1 | false | - |
| `remember` | field | #ffffff | #222222 | #c9ced8 | 1 | 6 | 4 | 14 | normal | left | 1 | false | - |
| `submit` | primary | #2a6cf0 | #ffffff | #667788 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |

## Screen `failed`: Sign-in failed

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 60 | 350 | 40 | Sign-in failed | failed.title |  |  |
| `message` | text | 20 | 120 | 350 | 60 | We could not sign {{user.email}} in. | failed.message |  |  |
| `retry` | button | 20 | 200 | 350 | 48 | Try again | action.retry | retry |  |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |
| `message` | body | #ffffff | #333333 | #667788 | 0 | 0 | 4 | 14 | normal | left | 1 | false | - |
| `retry` | primary | #2a6cf0 | #ffffff | #667788 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |

## Screen `home`: Home (final)

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 60 | 350 | 40 | Welcome back, {{user.name}} | home.title |  |  |
| `visit` | text | 20 | 120 | 350 | 40 | Last visit: {{user.last_visit}} | home.last_visit |  |  |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |
| `visit` | body | #ffffff | #333333 | #667788 | 0 | 0 | 4 | 14 | normal | left | 1 | false | - |

## Styles

- **body**: text_color=#333333. Used by: `failed.message`, `home.visit`
- **field**: fill=#ffffff, border_color=#c9ced8, border_width=1, radius=6. Used by: `login.email`, `login.password`, `login.remember`
- **heading**: text_color=#1a2b4c, font_size=28, font_weight=bold. Used by: `login.title`, `failed.title`, `home.title`
- **primary**: fill=#2a6cf0, text_color=#ffffff, radius=8, align=center. Used by: `login.submit`, `failed.retry`

## Sample data

Text such as `{{key}}` stands for a value; these are the sample values (live mode):

- `user.email`: sam@example.com
- `user.last_visit`: Nov 20
- `user.name`: Sam Rivera

## Transitions

- `login` --`submit` if credentials accepted--> `home`
- `login` --`submit` if credentials rejected--> `failed`
- `failed` --`retry`--> `login`

## Iterations

If you are asked to refine this UI more than once, settle the number of passes first: use the number the user gave, ask if they gave none, and use 2 (saying so) if you cannot ask. Every pass after the first must change something you can name (a position, size, type, label or style, or removing duplicated information); if nothing is left to change, stop early and say so. Log each pass in one line: `Pass k of N: <what changed>, because <why>`.
