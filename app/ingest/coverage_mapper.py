"""
Coverage mapper — maps test files to business rules and sets coverage_status.

Coverage statuses:
  covered      — tests exist covering all known permutations
  partial      — some permutations tested but not all
  uncovered    — no tests found anywhere
  coverage_gap — tested in one service but not another that implements it
  stale        — tests exist but rule changed after last test update
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Keywords that indicate a file is a test file
TEST_FILE_INDICATORS = re.compile(
    r'(\btest\b|\bspec\b|\bfixture\b)', re.IGNORECASE
)

# Patterns indicating test assertions
ASSERTION_PATTERNS = re.compile(
    r'\b(assert|should|expect|verify|check|ensure|must)\b', re.IGNORECASE
)


def is_test_file(filename: str, content: str) -> bool:
    """Heuristic: determine if a file is a test file."""
    name_lower = filename.lower()
    if any(ind in name_lower for ind in ["test", "spec", ".test.", ".spec."]):
        return True
    # Check content for test patterns
    if ASSERTION_PATTERNS.search(content):
        return True
    return False


def extract_tested_concepts(content: str) -> set[str]:
    """
    Extract business concepts mentioned in test code.
    Returns a set of lowercase keyword strings.
    """
    words = re.findall(r'\b[a-zA-Z]{3,}\b', content)
    return {w.lower() for w in words}


def map_coverage(
    rule_title: str,
    rule_definition: str,
    test_contents: list[tuple[str, str]],
) -> str:
    """
    Given a rule and a list of (filename, content) test files,
    return the coverage_status for the rule.

    Phase 1: simple keyword overlap between rule definition and test content.
    """
    if not test_contents:
        return "uncovered"

    rule_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', f"{rule_title} {rule_definition}".lower()))
    # Remove very common words
    stopwords = {"that", "this", "must", "will", "should", "when", "from", "with", "have", "been"}
    rule_words -= stopwords

    matched_tests = 0
    for _filename, content in test_contents:
        test_words = extract_tested_concepts(content)
        overlap = rule_words & test_words
        if len(overlap) >= 2:
            matched_tests += 1

    if matched_tests == 0:
        return "uncovered"
    elif matched_tests == 1:
        return "partial"
    else:
        return "covered"
