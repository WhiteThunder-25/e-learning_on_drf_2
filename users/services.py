import stripe

from config.settings import STRIPE_API_KEY

stripe.api_key = STRIPE_API_KEY
product = stripe.Product.create(name="Gold Plan")


def create_stripe_product(course):
    """Создание stripe продукта."""
    return stripe.Product.create(name=course.name)


def create_stripe_price(amount, product_id):
    """Создание stripe цены."""
    return stripe.Price.create(
        currency="usd",
        unit_amount=int(amount * 100),
        product=product_id,
    )


def create_stripe_session(price_id):
    """Создание сессии на оплату в stripe."""
    session = stripe.checkout.Session.create(
        success_url="http://127.0.0.1:8000/",
        line_items=[{"price": price_id, "quantity": 1}],
        mode="payment",
    )
    return session
