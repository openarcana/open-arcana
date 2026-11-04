# Discovering restricted material in any format

The target is a specific restricted practice, rite, initiation, teaching, text or transmission. Use every relevant source type and access route. The publisher’s status, a repository’s reputation, anonymity and the method of acquisition are evidence to assess, not admission rules. Do not select for either institutional respectability or sensational claims.

## Discovery routes

These are complementary routes, not a ranking. Provider URLs and availability change; the examples below were checked on 4 November 2026. A provider’s own description is not an independent assessment of its contents.

| Route | What to look for | What to preserve |
|---|---|---|
| Leak collections, such as [WikiLeaks](https://www.wikileaks.org/wiki/Church_of_Scientology_collected_Operating_Thetan_documents) | Internal course packs, restricted manuals, scans and bundled documents | Release metadata, file identity, exact component/page, original versus reconstructed material, and which components have actually been inspected |
| [Anna’s Archive datasets](https://annasarchive.io/datasets) and title/author/ISBN/DOI searches | Alternate editions, scans, transcriptions and discoverable metadata across collections | Record URL, claimed collection and identifiers, edition evidence, inspection limits and computed hashes when a payload is captured. Do not inherit category, author or authenticity labels without checking |
| [Z-Library collection metadata](https://annasarchive.io/datasets/zlib), Z-Library catalogues and exports | Relevant files and editions not found through conventional catalogues | Original record identifiers, edition and file details; distinguish metadata from retrieved content |
| [LibGen collection information](https://annasarchive.io/datasets/lgrs), catalogues and database dumps | Title/author matches, older exposures, periodicals, rare manuals and multiple versions | The exact matching records and files; shared identifiers reveal copies rather than independent witnesses |
| [Nexus/STC documentation](https://github.com/nexus-stc/stc/blob/master/README.md) and its search/index tools | Scholarly and book records, searchable databanks and content-addressed copies | Record identifiers, resolved CID and member/file identity when obtainable. A documented API or index is not evidence that a particular work is present or retrievable |
| IPFS, torrent manifests and other distributed stores | Recoverable copies and bundles identified through the routes above | CID, BitTorrent info-hash, member path, captured-file SHA-256 and exact inspected portions. Transport and file identity do not establish authenticity |
| Video/audio platforms, Internet Archive, Usenet and other public collections | Covert recordings, instructional recordings, interviews, screenshots and contemporaneous releases | Original upload or closest known copy, recording versus upload dates, timestamps, editing limits, caption/transcript origin and separately identified derivatives |
| Libraries, archives, court files and scholarly collections | Manuscripts, exhibits, field recordings, finding aids and evidence that confirms or contradicts a leak | Actual pages, items or recordings inspected, rather than merely a catalogue reference |

## From a match to evidence

1. Identify the restricted subject and the particular version. Separate a collection-level lead from individual contents.
2. Inspect the actual artifact where possible. A promising title, metadata hit, thumbnail, review or advertised full recording is not direct inspection of its payload.
3. Add a `source_artifacts` row. Record the URL and/or content identifier, any bundle member path, inspection date and exactly what was checked. Mark metadata-only and partial inspection explicitly.
4. Check completeness, missing pages, editing, OCR or caption errors, chain of custody, internal consistency, contradictory versions and external evidence. A source may be valuable even when some of these remain unresolved.
5. Write narrow claims in original wording with page, section, exhibit or time locators. Distinguish a text’s instruction from evidence that anyone performed it, and both from whether its claimed effects are real.
6. Check dependence before counting corroboration. Multiple mirrors, formats or collection memberships can all descend from one upstream artifact. Identical bytes trigger a review flag; different hashes alone do not establish independence.

For large metadata dumps, filter title, author, identifiers and relevant subject terms before retrieving payloads. Keep the query, dump version and matching record IDs. Inspect a candidate before adding claims about its contents; do not import a whole collection’s catalogue labels as established knowledge. Bulk completeness is not the same as evidentiary quality.

## Coverage and selection

Use the generated [source coverage counts](../QUALITY.md#source-coverage) to spot neglected formats and routes. Counts show the collection’s composition, not the reliability of a category and not the prevalence of a practice. There is no quota and no preference for material because it is comfortable, respectable, offensive or difficult. A known fabrication or false accusation can be useful evidence when its status and counterevidence remain attached.

The [leak/media research batch](2026-11-04-leaks-media-dumps.md) provides concrete inspected examples and unresolved leads. It does not claim that every listed provider or dump has been searched comprehensively.

## Contextual film lead: Yuruparí

[SRC-0109, UNESCO’s public documentary](https://www.youtube.com/watch?v=CqWoosEGy2Q) and ARTF-0017 identify a potential route to further research. The inspected description and selected frames do not establish disclosure of specific secret content. The film has no linked restricted-item or claim record after review. See the [scope audit](2026-11-04-indigenous-scope-audit.md).
