# Cross-case government model

This directory is a reusable institutional model, seeded from
`cases/UM_2025-0004`. It describes governmental actors and authority without
turning a case conclusion into a universal rule. The seed is deliberately
conservative: every substantive assertion cites one or more IDs from that
case's `manifest.yaml`.

## Files

| File | Purpose |
| --- | --- |
| `schema.yaml` | Record shapes, controlled vocabularies, and validation rules |
| `agencies.yaml` | Governmental bodies and their high-level legal roles |
| `offices.yaml` | Subunits, boards, commissions, and decision-making offices |
| `jurisdictions.yaml` | Subject-matter and territorial competence |
| `legal-instruments.yaml` | Statutes, permits, ordinances, resolutions, and agreements |
| `boundaries.yaml` | District, sphere, permit-map, eligibility, funding, and operational areas |
| `procedures.yaml` | Required or evidenced decision processes |
| `relationships.yaml` | Regulatory, ownership, oversight, transfer, and cooperation links |
| `proposals.yaml` | Proposal, acceptance, supersession, and unresolved implementation status |

## Evidence semantics

`evidence_status` and `acceptance_status` answer different questions.
`evidence_status` says how strongly the cited record supports the assertion.
`acceptance_status` says whether a proposal or instrument was accepted by the
relevant institution. Acceptance does not prove legal sufficiency.

- `verified_fact`: directly stated or evidenced by the cited record.
- `supported_interpretation`: a bounded synthesis of cited facts.
- `proposal`: language or an arrangement proposed to a decision maker.
- `unresolved`: the present corpus cannot answer the question.
- `disputed`: the cited record preserves a material conflict.

Each assertion also states its limits or what it does not establish. A trigger,
funding condition, map, permit, or agreement must not be promoted into a grant
of authority unless a source supports that effect.

## Cross-case use

Stable institutional IDs may be reused by another case. Case-specific
instruments, boundaries, proposals, and assertions should be added with their
own `case_id` and source IDs. Source IDs are local to the named case manifest;
consumers should resolve the pair `(case_id, source_id)`, not `source_id`
alone.

Do not infer that similarly named boundaries are coterminous. In particular,
the MCCSD jurisdictional boundary, MCCSD sphere, DDW system-area map, County
emergency eligibility area, grant beneficiary scope, and practical hauling
area represent different legal or operational concepts.

This model is an evidence index and does not provide legal advice.
