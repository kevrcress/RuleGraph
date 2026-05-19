# Terminology Normalization Skill

## Purpose
Normalize business terminology across rules so that rules using different words for the same concept can be discovered and linked.

## Status
Planned for a future stage. Not yet implemented.

## Design notes
- Build a domain glossary from extracted rule definitions
- Map synonyms (e.g., "cancellation window" == "cancellation period")
- Link rules that refer to the same concept with different terminology
- Store normalized terms in the knowledge graph for cross-rule discovery
