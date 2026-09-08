# ADR 0001 — Record architecture decisions

- Status: accepted
- Date: 2026-01

## Context

Structural decisions need to be traceable for maintenance and open‑source
contribution (§15).

## Decision

We keep lightweight Architecture Decision Records in `docs/adr`, one Markdown
file per decision, numbered sequentially. Each records context, the decision,
and its consequences. Diagrams use Mermaid (versionable text), never binary
images.

## Consequences

Every structural choice is discoverable and reviewable in git history.
Superseded ADRs are kept and marked, not deleted.
