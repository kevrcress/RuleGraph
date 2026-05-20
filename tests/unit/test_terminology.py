"""Unit tests for the terminology scanner (app/ingest/terminology_scanner.py)."""
import pytest
from app.ingest.terminology_scanner import (
    get_id_root,
    find_synonym_group,
    extract_id_terms,
)


# ---------------------------------------------------------------------------
# get_id_root
# ---------------------------------------------------------------------------

def test_root_from_camel_case():
    assert get_id_root("buyerId") == "buyer"
    assert get_id_root("customerId") == "customer"
    assert get_id_root("orderId") == "order"


def test_root_strips_leading_underscore():
    assert get_id_root("_buyerId") == "buyer"


def test_root_from_snake_case():
    assert get_id_root("buyer_id") == "buyer"
    assert get_id_root("customer_id") == "customer"


def test_root_lowercases_result():
    assert get_id_root("BuyerId") == "buyer"


# ---------------------------------------------------------------------------
# find_synonym_group
# ---------------------------------------------------------------------------

def test_buyer_and_customer_in_same_group():
    g_buyer = find_synonym_group("buyer")
    g_customer = find_synonym_group("customer")
    assert g_buyer is not None
    assert g_buyer == g_customer


def test_order_and_transaction_in_same_group():
    g_order = find_synonym_group("order")
    g_transaction = find_synonym_group("transaction")
    assert g_order is not None
    assert g_order == g_transaction


def test_unrelated_terms_in_different_groups():
    g_buyer = find_synonym_group("buyer")
    g_product = find_synonym_group("product")
    assert g_buyer != g_product


def test_unknown_term_returns_none():
    assert find_synonym_group("xyzzy") is None


# ---------------------------------------------------------------------------
# extract_id_terms
# ---------------------------------------------------------------------------

def test_extracts_camel_case_id():
    content = "var buyerId = request.buyerId;"
    terms = extract_id_terms(content)
    assert any("buyer" in t.lower() for t in terms)


def test_extracts_customer_id():
    content = "string customerId = payload.customerId;"
    terms = extract_id_terms(content)
    assert any("customer" in t.lower() for t in terms)


def test_extracts_snake_case_id():
    content = "customer_id = order.customer_id"
    terms = extract_id_terms(content)
    assert any("customer" in t.lower() for t in terms)


def test_excludes_unknown_concept():
    # "frobnicateId" — not in any synonym group
    content = "var frobnicateId = 42;"
    terms = extract_id_terms(content)
    assert not any("frobnicate" in t.lower() for t in terms)


def test_no_duplicates_per_root():
    content = "buyerId buyerId buyerId"
    terms = extract_id_terms(content)
    roots = [t.replace("Id", "").lower() for t in terms]
    assert roots.count("buyer") == 1


def test_eshop_example_detects_both():
    # The canonical eShop example from the spec
    ordering_content = "public string buyerId { get; set; }"
    payments_content = "private string customerId;"
    ordering_terms = extract_id_terms(ordering_content)
    payments_terms = extract_id_terms(payments_content)
    assert any("buyer" in t.lower() for t in ordering_terms)
    assert any("customer" in t.lower() for t in payments_terms)
