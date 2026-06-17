"""Inventory monitoring rules for the inventory service."""


REORDER_THRESHOLD_UNITS = 10
BACKORDER_STOCK_LEVEL = 0


def should_reorder(current_stock: int) -> bool:
    """Business rule: A reorder is automatically triggered when on-hand stock
    falls below 10 units.

    The reorder quantity is determined separately by the procurement system
    based on lead time and average daily sales.
    """
    return current_stock < REORDER_THRESHOLD_UNITS


def is_backorder(current_stock: int) -> bool:
    """Business rule: An item is considered on backorder when current stock
    equals zero.

    Backorder status causes the product page to display an estimated
    restock date rather than an 'Add to Cart' button.
    """
    return current_stock == BACKORDER_STOCK_LEVEL


def get_availability_label(current_stock: int) -> str:
    """Returns the customer-facing availability label based on stock level.

    Business rules:
      0 units   → "Backordered — see estimated date"
      1–9 units → "Low stock — order soon"
      10+ units → "In stock"
    """
    if current_stock == 0:
        return "Backordered — see estimated date"
    if current_stock < REORDER_THRESHOLD_UNITS:
        return "Low stock — order soon"
    return "In stock"


def reserve_stock(current_stock: int, quantity_requested: int) -> int:
    """Business rule: Stock reservation succeeds only when sufficient
    on-hand quantity is available.

    Returns the remaining stock after reservation, or raises ValueError
    if the requested quantity exceeds available stock.
    """
    if quantity_requested > current_stock:
        raise ValueError(
            f"Cannot reserve {quantity_requested} units; only {current_stock} available."
        )
    return current_stock - quantity_requested
