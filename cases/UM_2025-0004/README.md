# UM_2025-0004 case inventory

This is the pilot record for a case-centered Mendocino planning archive. It
tracks documents by identity and version, preserves conflicting source
descriptions, and distinguishes verified events from unresolved outcomes.

## What the case is

`UM_2025-0004` is a modification of Mendocino Unified School District's Water
System Reconstruction Project. The current proposal adds restoration of an
unnamed tributary to Slaughterhouse Gulch, including removal or abandonment of
culverts, excavation of a new open channel, and revegetation.

The case is not a standalone 2025 project. Its direct public-record lineage is:

```text
SCH 2020080439 (2020-present)
  -> U_2023-0004 (County approval, April 4, 2024)
  -> A-1-MEN-24-0017 (Coastal Commission appeal)
  -> UM_2024-0008 / PC 2024-0019 (County modification, December 19, 2024)
  -> A-1-MEN-25-0002 (Coastal Commission appeal)
  -> Coastal Commission no-substantial-issue decision (April 9, 2025)
  -> UM_2025-0004 stream-restoration modification (heard August 20, 2026)
```

`SCH 2022020568` and `U_2022-0012` concern a related but separate recycled-water
project. `U_2020-0010` concerns high-school modernization and is a false match,
not a predecessor permit.

## Current evidentiary status

The August 20 hearing and its packet are verified. The County archive identifies
the staff report, MND, addendum, hydro study, drainage materials, maps, plans,
biological evaluation, agency comments, public comments, and both initial and
revised draft resolutions.

The August 20 hearing outcome is verified from the recording: the Commission
unanimously continued the matter to September 3, 2026. No conditions were
adopted on August 20. No executed resolution or Notice of Final Action has been
located.

The County's GovAccess CDN denies automated retrieval, but the separate,
case-centered eTRAKiT system supports anonymous current-attachment retrieval.
It supplied the signed 21-condition Resolution PC 2024-0019, its 22-condition
pre-adoption redline, the condition memorandum, Exhibit I, and the initial
19-condition UM_2025-0004 draft in both PDF and native DOCX form. The August 18
GovAccess revision remains unretrieved; hearing evidence strongly indicates
that it contains 20 conditions.

The structured comparison is in
[`condition-versions.yaml`](condition-versions.yaml). The County platform map
and stable retrieval endpoints are documented in
[`publication-systems.md`](publication-systems.md).

## Why this is a useful pilot

The case already demonstrates the core requirements for a planning casebook:

- one project has several County, Coastal Commission, CEQA, CDFW, and Regional
  Water Board identifiers;
- GovAccess organizes records by hearing while eTRAKiT organizes them by case,
  but neither public view alone is complete;
- the same MND is relabeled and reused in later packets;
- resolutions have distinguishable initial, revised-draft, and final states;
- addresses, acreage, and well counts differ among official records;
- a related MUSD water project can easily be mistaken for the direct lineage;
- the same condition number can refer to substantively different provisions in
  successive resolutions; and
- the August 2026 hearing ended in a continuance without an adopted resolution.

These are data-model requirements, not edge cases to hide with narrative
summarization.

## Water authority research

[Water authority questions in UM_2025-0004](water-law-notes.md) separates the
County permit, MUSD public-water-system permit, MCCSD powers and boundaries,
drought trigger, grant scope, and practical tanker-delivery area. The structured
authority and boundary map is in [`water-law.yaml`](water-law.yaml).
The actor-by-actor joint-powers reasoning model is in
[`authority-chain.yaml`](authority-chain.yaml), with narrative analysis in
[`water-authority-chain.md`](water-authority-chain.md).
Draft acquisition requests for the operative DDW and financing records are in
[`ddw-records-request.md`](ddw-records-request.md), with structured tracking in
[`records-requests.yaml`](records-requests.yaml).
Searches, archive paths, failed retrievals, false matches, and capture methods
are recorded in [`acquisition-log.yaml`](acquisition-log.yaml) so acquisition
provenance remains separate from conclusions drawn from the records.

The local database now indexes **103 documents and 7,539 pages**. The recovered
Town LCP corpus includes the complete 2016 and 2017 Coastal Commission reports,
424 exhibit pages, 584 appendix pages, the addendum, effective-certification
record, final Town Plan, and Ordinance 4395. It substantially reconstructs the
official material formerly released under public request 24-31.

The water-authority corpus now includes the complete 2012 MCCSD Groundwater
Management Plan and Programs, its embedded AB 786 chapter law, Resolution 113,
County-MCCSD Agreement 90-113, the 1997 recycled-water MOU and Joint Resolution
97-1, archived Ordinance 07-1, the signed April 20, 2023 potable-project MOU, and
MCCSD's November 25, 2024 packet and action minutes rescinding that agreement
and adopting its replacement.

The 2017 report states at PDF page 82 that the County had never applied to
incorporate MCCSD groundwater-extraction permit provisions into the certified
LCP. Public request 22-583 separately shows County staff relying on MCCSD
hydrology, drought-stage, extraction-permit, allotment, and sewer decisions in
an actual 2018-2022 coastal-permit process. The casebook records both facts:
interagency practice is not treated as legal incorporation into the LCP.

## Next evidence needed

1. Obtain GovAccess documents 79268 and 79272 and every later resolution
   revision or redline.
2. Obtain the native Exhibit I GIS package and parcel-intersection list.
3. Obtain non-current eTRAKiT attachments and both systems' version/audit
   metadata.
4. Obtain any LAFCo inquiry or determination about service authority, latent
   powers, or outside-boundary service.
5. Locate any resolution, approved minutes, and Notice of Final Action from the
   continued September 3 hearing.
6. Compare County document 79036 with the July 16, 2026 CEQAnet revised
   addendum.
7. Extract every cited permit, study, map, condition, and prior hearing from the
   staff report and resolutions, then mark any cited-but-unpublished record.
