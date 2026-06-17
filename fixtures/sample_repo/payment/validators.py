"""Payment validation rules for the payment service."""


def validate_cvv(cvv: str) -> bool:
    """Business rule: CVV must be exactly 3 or 4 digits.

    3-digit CVV is standard for Visa/Mastercard/Discover.
    4-digit CVV is used for American Express cards.
    Non-numeric characters are always rejected.
    """
    if not cvv or not cvv.isdigit():
        return False
    return len(cvv) in (3, 4)


def is_high_risk_transaction(amount: float, account_verified: bool) -> bool:
    """Business rule: Flag transaction as high-risk when amount exceeds $1,000
    and the account has not completed identity verification.

    High-risk transactions are held for manual review before processing.
    Verified accounts are exempt from this threshold regardless of amount.
    """
    if account_verified:
        return False
    return amount > 1000


def validate_card_expiry(month: int, year: int, current_month: int, current_year: int) -> bool:
    """Business rule: Card must not be expired at the time of transaction.

    Cards expire at the end of the stated month.
    """
    if year > current_year:
        return True
    if year == current_year and month >= current_month:
        return True
    return False
