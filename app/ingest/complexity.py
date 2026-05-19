"""
Complexity scorer for source code and documents.
Scores content from 0.0 (simple) to 1.0 (highly complex).
Used to route extraction to the appropriate LLM tier.
"""
import re
from typing import Optional


# Branch keywords that increase cyclomatic complexity
BRANCH_KEYWORDS = [
    "if", "else", "elif", "switch", "case", "for", "while",
    "try", "catch", "except", "finally", "foreach", "do",
]

# Business logic keywords indicating domain-relevant content
BUSINESS_LOGIC_KEYWORDS = [
    "calculate", "calculation", "validate", "validation", "policy", "policies",
    "rule", "rules", "fee", "fees", "price", "pricing", "discount", "discounts",
    "eligibility", "eligible", "approve", "approval", "reject", "rejection",
    "authorize", "authorization", "payment", "billing", "invoice", "order",
    "cancel", "cancellation", "refund", "credit", "debit", "tax",
    "commission", "penalty", "limit", "threshold", "quota", "constraint",
    "status", "transition", "workflow", "process", "business",
]


def score_complexity(
    content: str,
    domain_terms: Optional[list[str]] = None,
) -> float:
    """
    Score content complexity from 0.0 to 1.0.

    Signals:
    - Line count: >100 adds 0.1, >200 adds 0.2 total
    - Branch keyword density: count / line_count, scaled
    - Business logic keyword density: presence of domain terms
    - Nesting depth: max indentation level / 10 (capped)

    All signals summed and clamped to [0.0, 1.0].
    """
    if not content or not content.strip():
        return 0.0

    lines = content.splitlines()
    line_count = max(len(lines), 1)
    lower_content = content.lower()

    # --- Signal 1: Line count ---
    line_score = 0.0
    if line_count > 200:
        line_score = 0.2
    elif line_count > 100:
        line_score = 0.1

    # --- Signal 2: Branch keyword density ---
    branch_count = 0
    # Use word-boundary matching to avoid partial matches
    for keyword in BRANCH_KEYWORDS:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        branch_count += len(re.findall(pattern, lower_content))

    # Density: branches per line, scaled to ~0.3 max
    branch_density = branch_count / line_count
    # Scale: density of 0.15 (1 branch per ~7 lines) -> 0.3 score
    branch_score = min(branch_density * 2.0, 0.3)

    # --- Signal 3: Business logic keyword density ---
    all_domain_terms = list(BUSINESS_LOGIC_KEYWORDS)
    if domain_terms:
        all_domain_terms.extend(domain_terms)

    business_count = 0
    for term in all_domain_terms:
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        if re.search(pattern, lower_content):
            business_count += 1

    # Normalize: presence of 5+ distinct terms -> 0.3 score
    business_score = min((business_count / max(len(all_domain_terms), 1)) * 1.5, 0.3)

    # --- Signal 4: Nesting depth ---
    max_depth = 0
    for line in lines:
        if not line.strip():
            continue
        # Count leading whitespace
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        # Estimate depth: assume 4-space or tab indentation
        depth = indent // 4 if '\t' not in line else (len(line) - len(line.lstrip('\t')))
        if depth > max_depth:
            max_depth = depth

    nesting_score = min(max_depth / 10.0, 0.2)

    # --- Combine all signals ---
    total = line_score + branch_score + business_score + nesting_score
    return min(max(total, 0.0), 1.0)
