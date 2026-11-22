# Spec sheet: Checkout (for a coding AI)

Each screen is 800 x 600 px. The first screen is `cart`.
Positions are the top-left corner of each block, in pixels.
A block's `event` is what it raises when the user uses it; transitions below say what happens next.
Every block also has a resolved style (built-in default for its type, then its named style, then its own overrides); see the table under each screen and the Styles section.

## Screen `cart`: Cart

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 20 | 400 | 40 | Your cart | cart.title |  |  |
| `items` | list | 20 | 80 | 500 | 300 | Items | cart.items |  | One row per product: name, quantity, price |
| `total` | text | 540 | 80 | 240 | 40 | Total: {{cart.total}} | cart.total |  |  |
| `checkout` | button | 540 | 520 | 240 | 48 | Checkout | action.checkout | checkout |  |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |
| `items` | body | #f7f8fa | #222222 | #c9ced8 | 1 | 0 | 4 | 14 | normal | left | 1 | false | - |
| `total` | body | #f7f8fa | #222222 | #c9ced8 | 0 | 0 | 4 | 14 | normal | left | 1 | false | - |
| `checkout` | primary | #2a6cf0 | #ffffff | #667788 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |

## Screen `payment`: Payment

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 20 | 400 | 40 | Payment | payment.title |  |  |
| `card` | input | 20 | 80 | 400 | 40 | Card number | payment.card_number |  |  |
| `back` | button | 20 | 520 | 160 | 48 | Back to cart | action.back | back |  |
| `pay` | button | 540 | 520 | 240 | 48 | Pay | action.pay | pay |  |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |
| `card` | body | #f7f8fa | #222222 | #c9ced8 | 1 | 0 | 4 | 14 | normal | left | 1 | false | - |
| `back` | primary | #2a6cf0 | #ffffff | #667788 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |
| `pay` | primary | #2a6cf0 | #ffffff | #667788 | 1 | 8 | 4 | 14 | bold | center | 1 | false | - |

## Screen `done`: Done (final)

| id | type | x | y | w | h | label | info | event | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | 20 | 20 | 400 | 40 | Thank you | done.title |  |  |
| `order` | text | 20 | 80 | 400 | 40 | Order {{done.order_number}} | done.order_number |  |  |

Background: `#ffffff`

Resolved style and properties of each block:

| id | style | fill | text_color | border_color | border_width | radius | padding | font_size | font_weight | align | opacity | shadow | properties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `title` | heading | #ffffff | #1a2b4c | #667788 | 0 | 0 | 4 | 28 | bold | left | 1 | false | - |
| `order` | body | #f7f8fa | #222222 | #c9ced8 | 0 | 0 | 4 | 14 | normal | left | 1 | false | - |

## Styles

- **body**: fill=#f7f8fa, border_color=#c9ced8. Used by: `cart.items`, `cart.total`, `payment.card`, `done.order`
- **heading**: text_color=#1a2b4c, font_size=28. Used by: `cart.title`, `payment.title`, `done.title`
- **primary**: fill=#2a6cf0, text_color=#ffffff, radius=8. Used by: `cart.checkout`, `payment.pay`, `payment.back`

## Sample data

Text such as `{{key}}` stands for a value; these are the sample values (live mode):

- `cart.total`: $42.00

## Transitions

- `cart` --`checkout`--> `payment`
- `payment` --`pay` if card is valid--> `done`
- `payment` --`back`--> `cart`

## Iterations

If you are asked to refine this UI more than once, settle the number of passes first: use the number the user gave, ask if they gave none, and use 2 (saying so) if you cannot ask. Every pass after the first must change something you can name (a position, size, type, label or style, or removing duplicated information); if nothing is left to change, stop early and say so. Log each pass in one line: `Pass k of N: <what changed>, because <why>`.
