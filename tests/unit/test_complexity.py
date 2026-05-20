"""Unit tests for the complexity scorer (app/ingest/complexity.py)."""
import pytest
from app.ingest.complexity import score_complexity


def test_empty_content_scores_zero():
    assert score_complexity("") == 0.0
    assert score_complexity("   ") == 0.0


def test_single_line_scores_low():
    score = score_complexity("int x = 1;")
    assert score < 0.2


def test_many_branches_score_higher():
    many_branches = "\n".join(["if (x) {", "  if (y) {", "    else {"] * 20)
    simple = "int x = 1;"
    assert score_complexity(many_branches) > score_complexity(simple)


def test_business_keywords_raise_score():
    business = "validate payment eligibility approve rule cancel order discount fee"
    plain = "int a = 1; int b = 2; return a + b;"
    assert score_complexity(business) > score_complexity(plain)


def test_deep_nesting_raises_score():
    deeply_nested = "\n".join(["    " * i + "do {" for i in range(10)])
    shallow = "if (x) { return 1; }"
    assert score_complexity(deeply_nested) >= score_complexity(shallow)


def test_score_clamped_to_1():
    # Pathologically complex content shouldn't exceed 1.0
    monster = "\n".join(
        ["if (x) { while (y) { for (z) { try { if (a) { elif b: cancel payment validation approval rule" ] * 300
    )
    assert score_complexity(monster) <= 1.0


def test_score_non_negative():
    assert score_complexity("just some text") >= 0.0


def test_long_file_scores_higher_than_short():
    short = "int x = 1;"
    long_code = "\n".join(["int x_{} = {};".format(i, i) for i in range(250)])
    assert score_complexity(long_code) >= score_complexity(short)


def test_domain_terms_param_increases_score():
    content = "The widget sprocket must engage the flibbertigibbet before handoff."
    score_without = score_complexity(content)
    score_with = score_complexity(content, domain_terms=["widget", "sprocket", "flibbertigibbet", "handoff"])
    assert score_with >= score_without
