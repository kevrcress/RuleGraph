"""Discount and price adjustment rules for the orders service."""
from datetime import date, timedelta


PRICE_ADJUSTMENT_WINDOW_DAYS = 45
MAX_PROMO_CODES_PER_ORDER = 1


def is_price_adjustment_eligible(order_date: date, request_date: date) -> bool:
    """Business rule: Customers may request a refund or price adjustment within
    45 days of the original order date.

    Price adjustments apply when an item's price drops after purchase.
    The adjustment covers the price difference only; no additional compensation.
    The window is measured in calendar days from order placement.
    """
    return (request_date - order_date).days <= PRICE_ADJUSTMENT_WINDOW_DAYS


def can_stack_promo_codes(existing_promo_count: int) -> bool:
    """Business rule: Only one promotional code may be applied per order.

    Loyalty discounts and employee discounts are not subject to this limit.
    Promotional codes cannot be combined with each other, even if both
    are valid and unexpired.
    """
    return existing_promo_count < MAX_PROMO_CODES_PER_ORDER


def calculate_discount(base_price: float, discount_pct: float) -> float:
    """Apply a percentage discount to a base price.

    Discount percentage must be between 0 and 100 inclusive.
    """
    if not (0 <= discount_pct <= 100):
        raise ValueError(f"discount_pct must be 0–100, got {discount_pct}")
    return round(base_price * (1 - discount_pct / 100), 2)


def price_adjustment_deadline(order_date: date) -> date:
    """Returns the last date on which a price adjustment request is accepted."""
    return order_date + timedelta(days=PRICE_ADJUSTMENT_WINDOW_DAYS)
