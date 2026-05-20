"""
Terminology scanner — finds camelCase/snake_case ID field names in source content
and detects cross-service naming inconsistencies.

Detection approach:
  1. Scan source content for patterns like buyerId, customerId, customer_id
  2. Extract the root concept (e.g. "buyer" from "buyerId")
  3. Use synonym groups to find related concepts across services
  4. Flag when different services use different names for the same concept

Known synonym groups used for grouping ID fields by semantic concept.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Matches camelCase ID fields like: buyerId, customerId, OrderId, _buyerId
# Also matches snake_case: buyer_id, customer_id
CAMEL_ID_RE = re.compile(r'\b_?([A-Za-z][a-zA-Z]*)Id\b')
SNAKE_ID_RE = re.compile(r'\b([a-z][a-z_]*)_id\b')

# Synonym groups: terms that refer to the same business concept
# When two different terms from different services fall in the same group,
# they are flagged as terminology inconsistencies.
SYNONYM_GROUPS: list[frozenset] = [
    frozenset({"buyer", "customer", "client", "user", "consumer", "purchaser"}),
    frozenset({"order", "transaction", "purchase", "request", "sale"}),
    frozenset({"product", "item", "stock", "inventory", "sku", "article"}),
    frozenset({"payment", "billing", "charge", "invoice", "fee"}),
    frozenset({"address", "location", "shipping", "delivery", "destination"}),
    frozenset({"seller", "vendor", "merchant", "supplier", "provider"}),
    frozenset({"account", "profile", "member", "subscriber", "tenant"}),
]


def get_id_root(term: str) -> str:
    """
    Extract the root concept from an ID field name.
    E.g. "buyerId" → "buyer", "_customerId" → "customer", "order_id" → "order"
    """
    clean = term.lstrip("_")
    if clean.endswith("Id"):
        return clean[:-2].lower()
    if clean.endswith("_id"):
        return clean[:-3].lower()
    return clean.lower()


def find_synonym_group(root: str) -> Optional[frozenset]:
    """Return the synonym group containing root, or None if not in any group."""
    for group in SYNONYM_GROUPS:
        if root in group:
            return group
    return None


def extract_id_terms(content: str) -> list[str]:
    """
    Extract all ID field names from source content.
    Returns normalized variants (stripped of leading underscore, original case preserved).
    """
    found = {}
    # camelCase: buyerId, CustomerId, _buyerId
    for match in CAMEL_ID_RE.finditer(content):
        full = match.group(0).lstrip("_")
        root = get_id_root(full)
        if root and len(root) > 2 and find_synonym_group(root) is not None:
            # Use root as dedup key, keep first occurrence's casing
            if root not in found:
                found[root] = full
    # snake_case: buyer_id, customer_id
    for match in SNAKE_ID_RE.finditer(content):
        full = match.group(0)
        root = get_id_root(full)
        if root and len(root) > 2 and find_synonym_group(root) is not None:
            if root not in found:
                found[root] = full
    return list(found.values())
