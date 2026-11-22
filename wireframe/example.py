"""A small, valid, finding-free wireframe: a three-screen checkout.

It is used as the worked example inside the AI authoring guide (R3) and by
`python -m wireframe new FILE --example`. Because it is built in code and
tested, the example the guide shows can never be invalid.
"""


def _block(id, type, x, y, w, h, label, info, event="", note="", style=None):
    # Every block names a shared style, so the example is finding-free (R7).
    style = style or {"heading": "heading", "button": "primary"}.get(type, "body")
    return {"id": id, "type": type, "x": x, "y": y, "w": w, "h": h,
            "label": label, "info": info, "note": note, "event": event, "style": style}


def example_wireframe():
    return {
        "name": "Checkout",
        "canvas": {"width": 800, "height": 600},
        "initial": "cart",
        "styles": {
            "heading": {"font_size": 28, "text_color": "#1a2b4c"},
            "primary": {"fill": "#2a6cf0", "text_color": "#ffffff", "radius": 8},
            "body": {"fill": "#f7f8fa", "border_color": "#c9ced8"},
        },
        "data": {"cart.total": "$42.00"},
        "states": [
            {"id": "cart", "title": "Cart", "final": False, "blocks": [
                _block("title", "heading", 20, 20, 400, 40, "Your cart", ["cart.title"]),
                _block("items", "list", 20, 80, 500, 300, "Items", ["cart.items"],
                       note="One row per product: name, quantity, price"),
                _block("total", "text", 540, 80, 240, 40, "Total: {{cart.total}}", ["cart.total"]),
                _block("checkout", "button", 540, 520, 240, 48, "Checkout", ["action.checkout"],
                       event="checkout"),
            ]},
            {"id": "payment", "title": "Payment", "final": False, "blocks": [
                _block("title", "heading", 20, 20, 400, 40, "Payment", ["payment.title"]),
                _block("card", "input", 20, 80, 400, 40, "Card number", ["payment.card_number"]),
                _block("pay", "button", 540, 520, 240, 48, "Pay", ["action.pay"], event="pay"),
                _block("back", "button", 20, 520, 160, 48, "Back to cart", ["action.back"], event="back"),
            ]},
            {"id": "done", "title": "Done", "final": True, "blocks": [
                _block("title", "heading", 20, 20, 400, 40, "Thank you", ["done.title"]),
                _block("order", "text", 20, 80, 400, 40, "Order {{done.order_number}}", ["done.order_number"]),
            ]},
        ],
        "transitions": [
            {"id": "t1", "source": "cart", "target": "payment", "event": "checkout", "guard": ""},
            {"id": "t2", "source": "payment", "target": "done", "event": "pay", "guard": "card is valid"},
            {"id": "t3", "source": "payment", "target": "cart", "event": "back", "guard": ""},
        ],
    }
