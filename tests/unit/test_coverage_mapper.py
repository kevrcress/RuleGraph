"""Unit tests for coverage_mapper pure functions."""
import pytest
from app.ingest.coverage_mapper import is_test_file, extract_tested_concepts, map_coverage


class TestIsTestFile:

    def test_filename_with_test_prefix(self):
        assert is_test_file("test_orders.py", "") is True

    def test_filename_with_spec_suffix(self):
        assert is_test_file("orders.spec.ts", "") is True

    def test_filename_with_dot_test(self):
        assert is_test_file("orders.test.js", "") is True

    def test_non_test_filename_no_assertions(self):
        assert is_test_file("order_service.py", "def process_order(): pass") is False

    def test_non_test_filename_with_assertion_content(self):
        assert is_test_file("order_service.py", "assert result == expected") is True

    def test_spec_in_filename(self):
        assert is_test_file("OrderSpec.java", "") is True


class TestExtractTestedConcepts:

    def test_returns_set_of_lowercase_words(self):
        result = extract_tested_concepts("Order cancellation window test")
        assert "order" in result
        assert "cancellation" in result
        assert "window" in result

    def test_filters_short_words(self):
        result = extract_tested_concepts("if is at the order")
        assert "if" not in result
        assert "is" not in result
        assert "order" in result

    def test_empty_content(self):
        result = extract_tested_concepts("")
        assert result == set()


class TestMapCoverage:

    def test_no_tests_returns_uncovered(self):
        result = map_coverage("Order Cancellation", "Orders can be cancelled within 24 hours", [])
        assert result == "uncovered"

    def test_single_matching_test_returns_partial(self):
        tests = [("test_orders.py", "order cancellation window check assert")]
        result = map_coverage("Order Cancellation", "Orders can be cancelled within window", tests)
        assert result == "partial"

    def test_multiple_matching_tests_returns_covered(self):
        tests = [
            ("test_order_a.py", "order cancellation window assert"),
            ("test_order_b.py", "order cancellation assert verify"),
        ]
        result = map_coverage("Order Cancellation", "Orders can be cancelled within window", tests)
        assert result == "covered"

    def test_unrelated_test_content_returns_uncovered(self):
        tests = [("test_payments.py", "stripe billing invoice charge assert")]
        result = map_coverage("Order Cancellation", "Orders can be cancelled", tests)
        assert result == "uncovered"
