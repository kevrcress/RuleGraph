"""Order workflow rules for the orders service."""
from datetime import datetime, timedelta


APPROVAL_THRESHOLD_USD = 500
CANCELLATION_WINDOW_HOURS = 24


def requires_approval(order_total: float) -> bool:
    """Business rule: Orders with a total value above $500 require explicit
    approval from a manager or purchasing authority before fulfillment begins.

    Orders at or below $500 are auto-approved and proceed directly to
    the fulfillment queue.
    """
    return order_total > APPROVAL_THRESHOLD_USD


def is_cancellable(placed_at: datetime, now: datetime) -> bool:
    """Business rule: Customers may cancel an order without penalty within
    24 hours of placing it, provided fulfillment has not yet begun.

    After the 24-hour window, cancellation requires customer support
    intervention and may incur a restocking fee.
    """
    return (now - placed_at) <= timedelta(hours=CANCELLATION_WINDOW_HOURS)


def get_cancellation_deadline(placed_at: datetime) -> datetime:
    """Returns the last moment at which a no-penalty cancellation is allowed."""
    return placed_at + timedelta(hours=CANCELLATION_WINDOW_HOURS)


def next_order_status(current_status: str, event: str) -> str:
    """State machine for order lifecycle transitions.

    Valid transitions:
      pending   → approved  (approval_granted)
      pending   → rejected  (approval_denied)
      approved  → shipped   (fulfillment_complete)
      shipped   → delivered (delivery_confirmed)
    """
    transitions = {
        ("pending", "approval_granted"): "approved",
        ("pending", "approval_denied"): "rejected",
        ("approved", "fulfillment_complete"): "shipped",
        ("shipped", "delivery_confirmed"): "delivered",
    }
    return transitions.get((current_status, event), current_status)
