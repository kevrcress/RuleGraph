# Conflict Detection Skill

## Purpose
Detect conflicting or contradictory business rules in the knowledge graph.

## Status
Planned for a future stage. Not yet implemented.

## Design notes
- Use semantic similarity search via Cognee to find potentially conflicting rules
- Flag rules with overlapping scope but contradictory conditions
- Severity levels: critical (directly contradictory), warning (potentially overlapping)
