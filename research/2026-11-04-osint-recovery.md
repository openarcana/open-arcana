# Source recovery and discovery review, 4 November 2026

Question: can unresolved source references be made recoverable without treating a working endpoint, a catalogue entry or a mirrored description as verified ritual content?

This follow-up adds six source routes, changes one AustLII URL to its browser-readable document route, and adds four artifact records. It adds no ritual-content claims and upgrades no authenticity, independence or present-practice assessment. The catalogue now contains 647 records, including 46 artifacts. Source-linked queries, tools, references and inspection limits are in the [18-entry search log](searches/2026-11-04-recovery.jsonl); the generated [HTTP audit](osint/2026-11-04.md) retains its separate transport observations.

## Recovery results

| Source | Result | Remaining limit |
|---|---|---|
| SRC-0010, Wollersheim court records | [UCLA collection 590 finding-aid lead](https://oac.cdlib.org/findaid/ark:/13030/c84j0hcd); contemporary November 1985 press references | No original court exhibit or exact archival folder inventory recovered. Keep the missing direct-route qualification. The 1985 disclosure year is not replaced by the 1986 verdict year. |
| SRC-0011, Fishman declaration | [CMU collection index](https://www.scs.cmu.edu/~dst/Secrets/Fishman/Declaration/index.html), declaration reference and ARTF-0043 | The index says OT II/III were removed. Course-labelled external links point to Scientology-host addresses; Spaink summaries are separate resources. An index capture does not substantiate the seed's full-OT-III disclosure label. |
| SRC-0012, Usenet postings | [Public historical group archive](https://groups.google.com/g/alt.religion.scientology) | No exact 1994–1995 message ID or original posting recovered; extent narrowed to reference. The group archive is a collection, not an individual source text. |
| SRC-0022, Sirr-i Akbar | [University of Chicago microform holding](https://www.lib.uchicago.edu/e/collections/mideast/microformat/manuweba-h.html), entry 943 | Holding metadata only. A Gallica candidate returned a verification page in the local browser; its manuscript pages and copy date remain uninspected. The microform's 1993 date does not redraft the work's 1657 date. |
| SRC-0040, Panorama programme | [Third-party transcript and five embed references](https://scicrit.wordpress.com/2014/02/05/scientology-the-road-to-total-freedom/), ARTF-0045 | Selected OT III transcript passage inspected; the broadcast was not watched or compared with its audio. A separate [ICO record](https://ico.org.uk/action-weve-taken/decision-notices/2011/02/fs50358104/) supplies a programme-identity check, not a ritual-content verdict. |
| SRC-0041, NewNameNoah | [Identifiable endowment upload](https://www.youtube.com/watch?v=b8sbYtFOnxk), ARTF-0046 | Local browser confirms metadata and availability. Upload is dated 15 May 2013; the uploader describes footage from 2011 and 2012 and a separate veil segment. Full recording, audio and captions remain unchecked. The 2017 discussion date was not the recording date. |
| SRC-0074, Sackville article | [Working AustLII viewdoc route](https://www.austlii.edu.au/cgi-bin/viewdoc/au/journals/FedJSchol/2002/1.html) | Browser re-read of the relevant passage; older client failure retained. No HTTP status invented from a DOM view. |
| SRC-0080, Poulsen court record | [Edited transcription](https://www.heimskringla.no/wiki/Forh%C3%B8rsprotokol_over_Anders_Poulsen), ARTF-0044 | Selected passages and editorial apparatus inspected; not an original-manuscript collation. The credited 1903 print base, 1692 court record and other dated textual layers remain distinct. |

The two unsupported seed `full` disclosure extents are narrowed. Their records remain unreviewed; finding the index does not retrospectively inspect its missing exhibits. Sources that cite the same court record or copy one declaration remain dependent even when their hosts and formats differ.

## Access failures and channel coverage

The earlier audit's 52 unresolved Open Library URLs concern 26 source records on one host. A focused HTTP request and local-browser visit both refused the connection. These observations establish access failure here, without diagnosing its cause or establishing that any work is false, lost or suppressed. The auditor now groups errors by host and supports bounded explicit retries while retaining earlier receipts. Other sources' access restrictions and the unlocated ARTF-0004 caption capture remain open.

Crossref was queried directly for the Poulsen bibliography. Its returned DOI candidates identify further citation routes; matching metadata does not authenticate the original court record. The response capture's digest is in the search log. Library holdings and the local browser were used alongside a public forum, Usenet and an exposure archive.

Exact-work web queries naming Anna's Archive and LibGen did not recover a Sirr-i Akbar file. No exhaustive internal catalogue/dump search, Nexus/STC or Z-Library payload retrieval, new IPFS/torrent retrieval or Tor/onion access is claimed in this pass. Those channels remain eligible research routes. The log distinguishes an unsuccessful query from a route not searched. Earlier [grey-source](2026-11-04-grey-sources-and-initiations.md) and [leak/media](2026-11-04-leaks-media-dumps.md) batches document actual inspected unconventional material.

## Implementation changes

The [workflow](OSINT.md) combines OSINT, archival research and digital source verification: precise scope, channel and language pivots, provenance and copy analysis, claim assessment, counterevidence and sensitive-data handling. Discomfort, sacred status and reputation do not decide inclusion. The dataset preserves difficult knowledge with attribution and limits.

The auditor validates the search log, retains its input hashes, records bounded outbound anchor labels and destinations, groups current failures by host, and supports `--retry-unresolved` with `--only-host`. Earlier observations stay attached to retried URLs. Browser/search observations remain separate from HTTP response codes. Generated exports preserve the corrected source dates, recovery notes and artifact limits for automated consumers.
