# Mendocino planning publication systems

Mendocino County currently exposes planning records through separate systems
that should not be treated as one archive.

| System | Role | Case-centered | Anonymous documents |
|---|---|---:|---:|
| GovAccess / Granicus | Planning Commission meeting pages and posted packets | No | Intended, but automated clients currently receive Akamai 403 responses |
| eTRAKiT / Sungard-Superion | Planning projects, resolutions, permits, parcels, and current attachments | Yes | Yes |
| Accela Citizen Access | Public Cannabis workflow | No Planning records | Cannabis routes require login |
| NextRequest | Searchable County public-record request and released-document archive | Request-centered | Yes, while documents remain public |
| Legacy County planning site | Historical meeting agendas and staff reports | No | Historical links |

## eTRAKiT case retrieval

Planning cases use the Project search:

```text
https://etrakit.mendocinocounty.org/eTRAKiT3/Search/project.aspx?activityNo=UM_2025-0004
```

Current attachments can be enumerated anonymously:

```text
https://etrakit.mendocinocounty.org/eTRAKiT3/attachmentUpload.aspx?Group=Project&ActivityNo=UM_2025-0004&showCurrent=true&postbackid=nothing
```

Despite its name, an anonymous `GET` to `attachmentUpload.aspx` is an attachment
index, not an upload operation. Individual records use:

```text
https://etrakit.mendocinocounty.org/eTRAKiT3/viewAttachment.aspx?Group=PROJECT&key=<attachment-key>&ActivityNo=<record-number>
```

Verified case records include:

- `U_2023-0004`, linked to resolution record `PC_2024-0004`;
- `UM_2024-0008`, linked to `PC_2024-0019`; and
- `UM_2025-0004`.

The public index exposes only current attachments. Empty or incomplete results
do not prove that the administrative file lacks deleted, superseded, internal,
or non-current documents.

## GovAccess limitations

GovAccess is a meeting publication feed. Its document IDs are site-wide CMS
identities, not permit numbers. Revision tokens encode CMS publication time,
not hearing, adoption, execution, or legal-effect time. There is no demonstrated
case-number query endpoint.

## Accela limitation

The County Accela deployment advertises only a Cannabis module. Its Cannabis
search redirects anonymous users to login, while Planning module probes return
errors. Planning `U_`, `UM_`, and `PC_` records belong in eTRAKiT, not Accela.

## NextRequest public-request archive

The active County portal is:

```text
https://mendocinocounty.nextrequest.com/requests
```

Its anonymous request-search endpoint is:

```text
GET https://mendocinocounty.nextrequest.com/client/requests
    ?search_term=<term>
    &page_number=<page>
```

Request metadata and timelines are available at:

```text
/client/requests/<request-id>
/client/requests/<request-id>/timeline
```

Current released documents are enumerated with:

```text
/client/request_documents?request_id=<request-id>&page_number=1
```

Search it locally with:

```sh
npm run search:pra
npm run search:pra -- "UM_2024-0008" "Mendocino City Community Services District"
npm run search:pra -- --json "Emergency Water Service Area"
```

Portal search is not exact: punctuation and tokenization can produce false
matches. Retain the query term and review request text before linking a result
to the case. Released-document lists can later become empty even though the
timeline says records were produced, so preserve request metadata and download
public documents promptly.

The public document catalog can be snapshotted independently:

```sh
npm run inventory:pra-docs
```

This captures the portal's public document metadata under ignored `captures/`
and checks exact request IDs even when a request's current document tab is
empty.

The curated relevant results are in
[`public-request-index.yaml`](public-request-index.yaml).

## Evidence rule

Record the publication system, case identity, attachment key or document ID,
retrieval time, original filename, hash, and legal status separately. A current
eTRAKiT attachment, a GovAccess posting, and a signed adopted resolution can
represent different states of the same logical document.

The structured version ledger for this case is
[`condition-versions.yaml`](condition-versions.yaml).
