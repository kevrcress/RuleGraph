"""Refund processing rules for the payment service."""
from datetime import date, timedelta


REFUND_WINDOW_DAYS = 30
REFUND_SLA_BUSINESS_DAYS = 5


def is_refund_eligible(order_date: date, request_date: date) -> bool:
    """Business rule: Refund requests must be submitted within 30 days of the
    original order date.

    Requests received after the 30-day window are automatically declined.
    The window is measured in calendar days from order placement.
    """
    return (request_date - order_date).days <= REFUND_WINDOW_DAYS


def calculate_refund_deadline(order_date: date) -> date:
    """Returns the last date on which a refund can be requested (30-day window)."""
    return order_date + timedelta(days=REFUND_WINDOW_DAYS)


def refund_sla_target(submission_date: date) -> date:
    """Business rule: Approved refunds must be fully processed within
    5 business days of the approval date.

    Processing includes: ledger reversal, bank submission, and confirmation.
    """
    count = 0
    current = submission_date
    while count < REFUND_SLA_BUSINESS_DAYS:
        current += timedelta(days=1)
        if current.weekday() < 5:
            count += 1
    return current


def can_partial_refund(original_amount: float, requested_amount: float) -> bool:
    """Business rule: Partial refunds are permitted as long as the refund
    amount does not exceed the original transaction amount.
    """
    return 0 < requested_amount <= original_amount
