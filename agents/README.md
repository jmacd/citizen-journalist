# Mendocino Government Observatory agents

This Python sidecar uses Microsoft Agent Framework (MAF) to coordinate an
auditable evidence workflow over the existing Node/SQLite casebook. The
casebook remains the deterministic system of record. Agent results are
proposals, not evidence.

## Active organization

The first workflow uses five stable roles defined in
[`organization/society.yaml`](organization/society.yaml):

| Role | Responsibility |
| --- | --- |
| Case Worker | Intake, routing, budgets, and dispositions |
| Scout | Official-source discovery and constrained public downloads |
| Archivist | MIME, hash, identity, duplicate, version, and OCR validation |
| Analyst | Atomic claims with page-addressed evidence and limitations |
| Skeptic | Premise, citation, contradiction, supersession, and overclaim review |

Hashing, MIME checks, corpus search, indexing, and citation resolution are
functions or deterministic executors—not simulated personalities. Repository
skills under `.github/skills/` are loaded as procedural policy, and their
SHA-256 values are stored in every run manifest.

## Local setup

From the repository root:

```sh
python3 -m venv agents/.venv
agents/.venv/bin/python -m pip install --upgrade pip
agents/.venv/bin/python -m pip install -r agents/requirements.lock
agents/.venv/bin/python -m pip install -e agents --no-deps
```

Rebuild the case corpus before running agents:

```sh
npm run build:case-db
```

The default `scripted` provider is deterministic and requires no cloud
credentials:

```sh
agents/.venv/bin/mendo-agents --repo-root . \
  ask 'What did the Planning Commission decide on August 20, 2026?'
```

Use a monitor observation to route a known change through the same workflow:

```sh
agents/.venv/bin/mendo-agents --repo-root . observe \
  --monitor-id mendocino_planning_commission \
  --summary 'A new meeting packet was published' \
  --url 'https://www.mendocinocounty.gov/example.pdf'
```

Validate the nine monitor definitions and route the difference between two
normalized snapshots through the workflow:

```sh
agents/.venv/bin/mendo-agents --repo-root . monitor-tick \
  --previous captures/monitors/planning-commission/previous.yaml \
  --current captures/monitors/planning-commission/current.yaml
```

Snapshots marked `fixture: true` are rejected unless
`--allow-fixtures` is supplied explicitly. This prevents demonstration data
from entering an operational run accidentally. The command performs one tick;
the cadence fields under `monitors/` are metadata and do not start a scheduler.

Downloads may be staged automatically only from allowlisted HTTPS hosts.
Authentication failures, 403 responses, and rate limits are recorded as
`identified_unretrieved`; the system does not bypass access controls.

## CIO approvals

The workflow pauses through a MAF request/response port before:

- canonical document registration;
- knowledge or authority-rule promotion;
- supersession;
- publication outside the run workspace;
- public-record requests or any external communication.

The terminal shows the exact approval bundle. Rejecting it preserves the
analysis, Skeptic review, evidence gaps, and CIO feedback in the ignored run
journal.

## Commanding deeper research

The anonymous public chatbot is intentionally read-only. It may identify and
deduplicate evidence gaps into triage, but it does not browse arbitrary sites,
download records, or send requests. A prompt that says “search the web” does
not expand those permissions.

Use a CIO research directive in Copilot CLI to activate repository skills and
bounded acquisition work. State the act, actors, authority question, required
primary records, and publication/request limits. For example:

```text
Research the authority to supply potable emergency water outside MCCSD's
boundary. Distinguish MUSD, MCCSD, County, DDW, LAFCo, hauler, and recipient.
Retrieve primary authority and determine where possession transfers. Treat the
Emergency Water Service Area only as an eligibility map. Record what each
source does not establish. Do not send a PRA request without CIO approval.
```

Copilot should invoke `trace-legal-authority` and `acquire-public-record`, write
the durable directive and provenance under the case, search official public
sources first, and leave inaccessible deciding records as explicit acquisition
tasks. `mendo-agents ask` analyzes the local corpus; it is not a general web
search command. `observe --url` stages a known allowlisted official URL through
Scout and Archivist.

For noninteractive test fixtures only, pass `--auto-approve`.

## Checkpoints and recovery

MAF file checkpoints are stored under:

```text
captures/agent-runs/checkpoints/<case-id>/
```

List checkpoint IDs:

```sh
agents/.venv/bin/mendo-agents --repo-root . checkpoints
```

Resume a run:

```sh
agents/.venv/bin/mendo-agents --repo-root . resume <checkpoint-id>
```

Pending CIO requests are carried in the checkpoint itself, so a fresh process
can rehydrate the workflow without relying on process memory.

## Model providers

Select a provider with `--provider`:

- `scripted`: deterministic test double;
- `ollama`: local `OllamaChatClient`;
- `foundry`: Microsoft Foundry using `FOUNDRY_PROJECT_ENDPOINT`,
  `FOUNDRY_MODEL`, and `DefaultAzureCredential` (Azure CLI locally or managed
  identity in Azure).

Provider-specific imports are lazy. Workflow topology, contracts, approval
rules, evidence adapters, and checkpoints do not change with the model.
Agent-produced analyst output must parse as the required JSON contract; invalid
output fails explicitly rather than being converted into a success-shaped
answer.

## Observability

MAF OpenTelemetry instrumentation is enabled with sensitive-data collection
off by default. Standard `OTEL_*` environment variables can route traces,
metrics, and logs to a local OTLP collector or Azure Monitor. The sidecar adds
non-sensitive counters for runs, approval requests, and terminal dispositions.

Local run state is stored at:

```text
captures/agent-runs/<run-id>/
  manifest.json
  events.jsonl
```

The journal records typed workflow events and decisions, not hidden
chain-of-thought.

## Tests

```sh
agents/.venv/bin/pytest agents/tests
npm test
```

Tests use a temporary SQLite/FTS corpus and scripted model. They verify
least-privilege policy, citation resolution, access-denied HTML rejection,
CIO approval, and checkpoint rehydration without modifying canonical evidence.

## Adding skills and roles

Refine a repository skill first. Then:

1. define its typed inputs and outputs;
2. expose only the minimum deterministic tools it needs;
3. add policy and replay tests;
4. record the skill hash in runs;
5. evaluate it against a known case;
6. request CIO activation.

Researcher and Theory Builder remain proposed roles. Evidence gaps, watch
proposals, and institutional-rule proposals exist as typed workflow products,
but a new autonomous role is not activated merely because an agent suggests it.

## Public chatbot MVP

The first public utility is a read-only chatbot for `UM_2025-0004`:

```sh
npm run chat
```

Open `http://127.0.0.1:4173/casebook.html` and use **Ask the casebook**. The
same MAF Case Worker → retrieval → Analyst → Skeptic path handles each question.
The browser retains the previous 12 user/assistant messages and sends them as
bounded context with follow-up questions. **New conversation** clears that
context. Conversation history is held in page memory, sent only as request
context, and is neither persisted by the chat service nor treated as canonical
evidence.

The runtime label above the composer is authoritative for each response:
`Scripted evidence mode (no LLM)`, `Ollama · <model>`, or
`Microsoft Foundry · <deployment>`. The same identity is returned by
`GET /api/health` and in every `/api/chat` response.

The public path has a deliberately narrower policy than the research CLI:

- it reads only the canonical SQLite case corpus;
- it cannot download, stage, register, supersede, or modify records;
- it returns only Skeptic-accepted claims with resolving source locators;
- it removes rule proposals, monitor proposals, and record-request drafts;
- it reports unsupported questions and missing records rather than inventing
  an answer;
- it does not persist public question text in the agent run journal.

The `scripted` provider supports curated answers and safe corpus-search
responses without credentials. For open-ended synthesis, set
`MENDO_MODEL_PROVIDER=ollama` or `foundry`; provider output remains subject to
the same structured claim contract and independent Skeptic review.

The bundled server is an MVP application server bound to localhost by default.
A public deployment must put it behind HTTPS, request-rate controls, process
supervision, and normal service monitoring. It must not expose the research CLI
or writable capture directories.
