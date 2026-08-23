# Publication monitors

This directory defines publication surfaces that should be checked for new or
changed records. The Python sidecar validates these contracts and can compare
two normalized snapshots with a one-shot `monitor-tick`; there is no scheduler
or credential-bearing monitor daemon.

## Layout

- `schemas/v1/monitor.schema.yaml` validates one monitor definition.
- `schemas/v1/registry.schema.yaml` validates `registry.yaml`.
- `schemas/v1/snapshot.schema.yaml` validates normalized observations emitted
  by a future monitor runtime.
- `definitions/*.yaml` are the initial monitor definitions.
- `fixtures/*.yaml` are non-authoritative examples of normalized snapshots.

All contracts use `schema_version: 1`. A breaking field or semantic change
requires a new `schemas/vN/` directory; existing definitions and snapshots
retain their original version.

## Monitoring model

A monitor describes five distinct concerns:

1. **Discovery** identifies the official index, feed, API, meeting archive, or
   case page to enumerate. A search result or index row is not reviewed
   evidence.
2. **Cursor/snapshot semantics** state what can be enumerated, how ordering is
   interpreted, and whether absence can mean deletion. A cursor is only a
   checkpoint; it is never a claim of legal chronology.
3. **Fingerprints** separate stable repository identity, mutable metadata, and
   downloaded content. SHA-256 applies to captured bytes; weak metadata hashes
   are change detectors, not authenticity proof.
4. **Cadence** records a desired observation interval and rationale. These
   values are metadata for a future scheduler and do not schedule anything.
5. **Routing** sends observations to an evidence-review queue. Only a later
   acquisition workflow may download, validate MIME type and byte count, hash,
   review, and register a source in a case manifest.

`identified_unretrieved`, access failures, empty current views, and removals
must remain observable outcomes. They must not be converted into successful
captures or proof that a record never existed.

## Evidence workflow boundary

The definitions route candidates toward existing repository workflows:

- GovAccess, eTRAKiT, and NextRequest use their corresponding harvest skills.
- Downloadable records use `acquire-public-record`.
- Distinct drafts, adopted copies, and executed copies use
  `register-document-version`.
- Accepted evidence is ultimately registered under
  `cases/{case_id}/manifest.yaml`, with originals under
  `captures/cases/{case_id}/`.

Monitor snapshots are operational metadata. They are not themselves case
evidence and should not be cited as establishing document content or legal
effect.

## Validation

Parse every YAML file from the repository root:

```sh
node --input-type=module -e \
  'import fs from "node:fs"; import path from "node:path"; import {parse} from "yaml";
   const walk=d=>fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(d,e.name)):[path.join(d,e.name)]);
   for(const f of walk("monitors").filter(f=>f.endsWith(".yaml"))) parse(fs.readFileSync(f,"utf8"));
   console.log("monitor YAML parsed")'
```

For full schema validation and a one-shot comparison, see
[`agents/README.md`](../agents/README.md).
