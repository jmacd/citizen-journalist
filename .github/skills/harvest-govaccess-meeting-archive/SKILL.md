---
name: harvest-govaccess-meeting-archive
description: Inventory Mendocino County GovAccess meeting attachments, decode document revision tokens, and reconstruct case and version relationships across hearing cycles.
---

# Harvest a GovAccess meeting archive

The County Planning Commission page is a manually maintained meeting archive,
not a case repository. Treat it as a publication feed.

1. Capture the meeting page HTML with retrieval time and hash.
2. For each hearing cycle, extract the visible heading, meeting date, agenda
   item, link label, URL, and ordering.
3. Parse `/home/showpublisheddocument/<id>/<token>`:
   - `<id>` is the GovAccess document identity;
   - `<token>` is a .NET-tick revision token that can be decoded to UTC with
     `npm run inspect:govaccess -- <url>`.
4. Record both the page label and the document identity. Labels such as
   “Resolution” and “Revised Resolution” are not sufficient version metadata.
5. Group records into a logical family only after comparing permit IDs, titles,
   contents, meeting context, and hashes.
6. Record `first_seen_hearing` separately from document revision time and legal
   adoption time.
7. Preserve links that return 403 as `identified_unretrieved`; do not infer
   content from the label.
8. Crawl every meeting in which the permit identifier, applicant, APN, project
   name, or predecessor identifier appears.
9. Register each file with the `register-document-version` workflow and compare
   condition-bearing resolutions with `compare-condition-sets`.

GovAccess revision time indicates CMS publication state, not adoption,
execution, or legal effect. Use the separate `harvest-etrakit-case-record`
workflow for the County's case-centered Planning database. The Accela portal is
configured for Cannabis and is not the public `U_`/`UM_` Planning repository.
