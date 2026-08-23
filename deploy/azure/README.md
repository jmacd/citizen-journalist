# Azure public case-chat milestone

The first cloud milestone deploys the existing read-only case chatbot before
moving evidence authority or acquisition into managed services. The acceptance
question is:

> What County groundwater guideline did the MUSD representative cite around
> 1:16 in the August 20 hearing, and what does it say?

The cloud answer must retain both the recording timestamp and official PDF page
citations. A provider or retrieval change that loses either locator fails the
milestone.

## Initial topology

| Concern | First Azure service | Boundary |
| --- | --- | --- |
| Web and MAF API | Azure Container Apps | Runs `Dockerfile.chat`; no research or acquisition endpoints exposed |
| Reasoning | Microsoft Foundry model deployment | `MENDO_MODEL_PROVIDER=foundry`; managed identity via `DefaultAzureCredential` |
| Canonical MVP corpus | Immutable SQLite file in the image | Same reviewed 30 MB database used locally |
| Checkpoints and triage queue | Azure Files mounted at `/data` | Operational state only; never substitutes for canonical evidence |
| Raw media and records | Azure Blob Storage | Original bytes, hashes, and derived transcript outputs remain separate |
| Meeting transcription | Azure AI Speech batch transcription | Word timestamps and diarization; output is derived evidence requiring validation |
| Retrieval upgrade | Azure AI Search | Hybrid/vector index keyed by source ID plus page or timestamp locator |
| Telemetry | OpenTelemetry to Azure Monitor/Application Insights | Sensitive prompt and response capture remains disabled |

This sequencing preserves a rollback path. Blob, Speech, and AI Search adapters
can be introduced behind `CorpusRepository`; SQLite remains the authority until
parity tests prove that cloud retrieval returns the same source IDs and
locators.

## Build the deployable image

Rebuild the corpus immediately before the image:

```sh
npm run build:case-db
npm run build:casebook
docker build -f Dockerfile.chat -t mendo-case-chat:local .
docker run --rm -p 4175:4173 mendo-case-chat:local
```

The image contains the web client, agent policy and skills, and generated
SQLite corpus. It excludes downloaded PDFs, audio, transcript JSON, run
journals, and credentials.

## Foundry configuration

Configure an existing Foundry project and model deployment on the Container App:

```text
MENDO_MODEL_PROVIDER=foundry
FOUNDRY_PROJECT_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>
FOUNDRY_OPENAI_BASE_URL=https://<account>.openai.azure.com/openai/v1/
FOUNDRY_MODEL=<deployment-name>
MENDO_CHECKPOINT_ROOT=/data/checkpoints
MENDO_RUN_ROOT=/data/runs
ENABLE_SENSITIVE_DATA=false
```

Assign the Container App's managed identity the least-privilege Foundry model
inference role required by the project. Do not store model keys in application
settings. Local development continues to authenticate through Azure CLI via the
same `DefaultAzureCredential` chain.

`FOUNDRY_OPENAI_BASE_URL` selects the Foundry account's Azure OpenAI v1 data
plane while retaining managed-identity authentication. If it is omitted, the
provider uses `FOUNDRY_PROJECT_ENDPOINT`.

## Durable operational state

Create an Azure Storage account and file share, register it on the Container
Apps environment, and mount it at `/data`. This preserves the deduplicated
research-triage queue and MAF checkpoints across revisions. The queue is not a
public-record request sender: every item starts in `triage`, and external
communication still requires CIO approval.

Cosmos DB checkpoint storage is the next scale step when multiple replicas need
concurrent workflow continuation. Do not use Cosmos-backed conversational
memory as evidence or allow it to bypass the canonical citation resolver.

SQLite locking is not reliable on the Container Apps Azure Files SMB mount.
The production specification therefore sets
`MENDO_RESEARCH_QUEUE_PATH=/data/research-queue.json`. That queue uses atomic
file replacement and is valid only while `minReplicas` and `maxReplicas` are
both one. SQLite remains the local default. Move the queue to Azure Table
Storage or Cosmos DB before enabling multiple replicas.

## Meeting-media pipeline

1. Preserve the original public recording or audio derivative in a private Blob
   container with source URL, retrieval time, byte count, and SHA-256.
2. Submit the Blob URL to Azure AI Speech batch transcription with diarization
   and word-level timestamps.
3. Preserve the unmodified Speech JSON as a derived artifact and hash it.
4. Normalize utterances into source ID, start/end time, speaker label, text,
   confidence, and transcription-engine version.
5. Index those segments in Azure AI Search alongside page-addressed records.
6. Treat statements as discovery leads. When a speaker names a document, route
   it to Scout → Archivist before the Analyst relies on the underlying text.
7. Cite the video timestamp for what was said and the document page for what
   the referenced authority actually says.

## Promotion gates

Cloud deployment is accepted only when:

- the health endpoint and web interface are available over HTTPS;
- anonymous clients cannot reach acquisition, registration, approval, or
  external-communication functions;
- the guideline acceptance question returns timestamp `01:15:47-01:16:29` and
  guideline page 18;
- the drought-trigger question returns Water Code §13198(a), plan pages 18 and
  22, and the three deduplicated triage items;
- restarting the Container App preserves queued triage items;
- logs contain dispositions and latency but not public question text, model
  prompts, source contents, credentials, or hidden reasoning;
- a blocked or failed Skeptic review publishes no answer.

Provisioning remains CIO-controlled; the deployed names, regions, identity
roles, and accepted image are recorded below.

## Deployed production resources

The first production deployment was accepted on 2026-08-22:

| Resource | Deployed value |
| --- | --- |
| Resource group | `rg-mendo-observatory-prod` |
| Public app | `https://mendo-casebook-chat.victoriousdune-666b9406.eastus2.azurecontainerapps.io/` |
| Container Apps environment | `mendo-observatory-env` in East US 2 |
| Container registry | `mendoobservatoryacr` Basic |
| Foundry account/project | `mendoobservatoryai` / `mendo-casebook` in East US 2 |
| Model deployment | `gpt-5-6-sol`, Global Standard |
| Storage | `mendoobservatorystg`, private Blob containers and `mendo-state` Azure Files share |
| Search | `mendoobservatorysearch`, free tier in West US 2 because East US 2 had no free-tier capacity |
| Speech | `mendoobservatoryspeech`, free tier in East US 2 |
| Telemetry | `mendo-observatory-logs` and `mendo-observatory-appinsights` |

The Container App uses a system-assigned identity with only `AcrPull` at the
registry and `Cognitive Services OpenAI User` at the Foundry account. The
deployment stores no model key. Public completion logs contain disposition,
latency, provider, claim count, and queue count only.

`deploy/azure/containerapp.production.yaml` pins the accepted image digest
`sha256:1dbdf00ccba28570c183c43a99130f5593e832a06f681d3b9b2e2b93dea8ead5`
(revision `mendo-casebook-chat--0000010`),
HTTPS-only ingress, health probes, managed-identity inference settings, and the
single-replica persistent-state mount.
