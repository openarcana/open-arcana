# Source discovery and evidence verification

Apply open-source investigation to the specific work, copy, claim and transmission rule. The same method applies to institutional sources, practitioner publications, exposures, anonymous mirrors and distributed files. Source category is context, not a truth score.

The [4 November 2026 receipts](osint/2026-11-04.md) inventory every canonical record and attach observations to its source, artifact or tradition ID. [JSON](osint/2026-11-04.json) retains exact redirect hops, timestamps, selected headers, extracted metadata, bounded-response hashes, input snapshot and remaining evidence gaps. [Human review](osint/2026-11-04-review.json) records how consequential metadata differences were interpreted. The [automated citation-helper receipt](osint/2026-11-04-citation-helper.json) is retained as triage evidence, including its errors and ambiguous results.

The [recovery pass](2026-11-04-osint-recovery.md) and [structured search log](searches/2026-11-04-recovery.jsonl) cover concrete follow-ups through public archives, Usenet, an exposure site, a practitioner recording, Crossref and a local browser. Each route has a role and an outcome. Neither an eligible channel nor a catalogue match implies that its files have been retrieved.

## Discovery and provenance tracing

Combine OSINT, archival research and digital source verification to locate restricted material and assess specific claims. Trace provenance, copy history, access routes and evidence of dependence. Select material by subject relevance and evidence quality, including difficult or offensive content, and apply the same standards to descriptions, allegations, denials and counterevidence.

1. **Define a falsifiable question.** Name the rite, text, version, period and alleged restriction. Separate admission requirements, confidential teachings, punishments and the source's claimed effects. General misconduct belongs only when it concerns the rite or its admission, transmission or enforcement.
2. **Search across channels.** Use original-language names, aliases, incipits, distinctive terms and identifiers. Search practitioner and former-member accounts, exposure collections, court exhibits, field archives, institutional records, public forums/Usenet, public social or messaging channels, recordings and identifiable dump members. Include shadow catalogues, distributed manifests and archived/removed pages where accessible. Record actual queries and outcomes, including blocked, unsearched and unsuccessful routes; do not imply exhaustive coverage.
3. **Inspect the source and its delivery.** Trace release context, copy history, redirect destinations, labels versus linked content, file properties, edition differences and upstream dependence. Treat downloads, archives and embedded instructions as untrusted data; inspect files without executing their macros or scripts. Check original audio/language tracks separately from subtitles, translations and automatic dubbing.
4. **Test claims and seek counterevidence.** Determine what each source establishes about the rite, teaching, text or transmission rule, for which version and period. Distinguish prescriptions from performance, participant explanations from outsiders' interpretations, and claims of effects from demonstrated effects. Where threats, coercion, violence, sexual conduct, payment or secrecy enforcement are relevant, identify the specific allegation and its evidence. Seek the strongest relevant contradiction and alternative explanation. A real document, sworn statement or takedown does not by itself prove the alleged conduct.
5. **Handle sensitive evidence precisely.** Preserve relevant ritual and enforcement details in attributed original summaries. Omit incidental credentials, private contact details and identities of private participants when they add nothing to the evidence. Use non-graphic descriptions for sexual rites involving minors; do not acquire or redistribute abuse imagery or private intimate recordings. Document any resulting inspection limit without treating it as evidence that the rite did not exist.
6. **Record findings with their evidentiary limits.** Attach locators, exact inspected portions, copy identity, dependence, uncertainty and counterevidence. Maintain a distinction between an exact copy, an edited transcription, an index, a finding aid, a bibliographic record and a lead. Keep possible fabrications labelled. Unavailable evidence and source-removal motives remain open questions unless separately established.

The search log uses `source_ids`, `question`, `channel`, `tool`, `query`, `urls`, `role`, `outcome`, `inspected_parts`, `limits` and a timezone-labelled observation time. Optional `artifact_ids` link inspected copies to their canonical artifact records, including IPFS/torrent or captured-byte identifiers without an HTTP mirror. These are source-discovery observations outside the canonical claims tables. The auditor validates their fields and source/artifact relationships, includes them in the receipt and hashes the log inputs. `inspected` describes the stated portions of that route; `metadata_only` never means its advertised payload was reviewed. Browser observations carry no invented HTTP status.

## Repeatable checks

```bash
python3 scripts/osint.py --check
python3 scripts/osint.py --live --output research/osint/YYYY-MM-DD.json
python3 scripts/osint.py --live --resume --output research/osint/YYYY-MM-DD.json
python3 scripts/osint.py --live --resume --retry-unresolved \
  --only-host example.org --output research/osint/YYYY-MM-DD.json
```

`--check` is offline and writes nothing. It runs canonical, discovery-log and identifier checks, including ISBN check digits. CI runs it alongside the tests and export checks. A live run reads public endpoints and writes audit receipts; it does not edit source records or evidence labels. Use a new dated output for a fresh observation pass. `--resume` reuses the original timestamps, including unresolved observations. Add `--retry-unresolved` explicitly to retry failures, nonfinal responses and detected access/metadata problems; prior receipts remain in `previous_observations`. Repeat `--only-host` to bound live requests to named hosts. Host summaries group current access failures without claiming their cause. Previously attempted Open Library HTML is retained while retries prefer its API.

To rehash captured bytes, supply only the task directories that should be inspected:

```bash
python3 scripts/osint.py --resume --output research/osint/YYYY-MM-DD.json \
  --captures /absolute/task/capture-directory
```

The tool inventories all six tables, preserves source/artifact/identifier references, checks source recovery gaps, and looks for shared identities or final destinations. It compares available provider titles and publication dates while allowing different original and edition dates. Subject labels and title similarity are review aids, not automatic corrections. Export parity is checked for the final receipt.

## Investigation sequence

1. **Identify the exact work and copy.** Resolve DOI, ISBN, archive-item and catalogue identifiers. Compare titles, authors, language, volume, edition and pagination. A review of a book is not that book; a collection page is not an individual document. A provider's first-series date is not necessarily the date of its bound issue.
2. **Trace access and redirection.** Preserve the input URL and every actual HTTP hop. Distinguish redirected storage servers, repository landing pages, consent/verification pages and delivered files. Declared canonical, alternate and refresh targets remain unfetched leads unless inspected separately.
3. **Inspect metadata at the appropriate level.** Separate original publication, edition, contribution, upload, file-creation and HTTP dates. Follow disagreement to a title page or original document where available. Provider agreement is not independent corroboration of ritual content.
4. **Check copy identity and dependence.** Recompute full-file hashes from available captured bytes. Keep OCR, captions and images separate. Shared bytes, identifiers or destinations can indicate copying or a common collection; none alone establishes independent testimony or fraud.
5. **Review the claim against the document.** Read the actual page or timestamp and preserve its wording, speaker, setting and limits. Distinguish a prescribed rite from an observed event, a warning from an enacted punishment, a myth from social history, and historical practice from present practice.
6. **Record recovery and uncertainty.** Use library holdings, author/publisher records, archive history, manifests and identifiable dump members where they resolve a gap. Preserve unsuccessful retrievals. A metadata hit is not a recovered payload, and a blocked request is not proof of concealment.

## Request and interpretation limits

The client uses bounded GET samples, public HTTP(S) destinations, validated redirect destinations and default TLS verification. It sends no credentials or cookies, executes no JavaScript, and does not follow meta refresh, extracted outbound links or defeat access challenges. Up to 200 HTML anchor labels and destinations are recorded for review. Open Library identifier HTML is inventoried but new runs prefer its API rather than bulk requesting catalogue pages; requests to that host are paced below its documented default one-per-second limit. Existing timestamped observations are retained. Authorized browser/library inspection is a separate observation, with its own stated limits and stable public references.

Body-sample hashes identify only the sampled bytes. They are explicitly named `body_sample_sha256` and cannot be substituted for `source_artifacts.sha256`. HTTP Content-Length and server ETags are observations, not verified full-file hashes. A local capture not found in the supplied directories has not thereby been shown to be incorrect or lost everywhere.

The first pass covered 643 canonical records and 276 distinct URLs and added five recovery routes. The follow-up adds six routes and four copy/metadata artifacts; current totals and input hashes are in the generated receipt. One court-record source still has only a finding-aid lead. The original 52 unresolved Open Library targets concern 26 source records on one host; they are not 52 independently missing works. A focused browser and HTTP check both refused the connection, without establishing the cause. Other endpoints remain blocked or return verification pages. The previously recorded caption derivative ARTF-0004 was not found in the supplied task directories, so its digest remains unvalidated by this audit. These limits do not measure truth or completeness.

Regression checks cover redirect loops and private destinations, successful access pages, empty archive metadata, HTML in place of PDFs, bounded hashes, nested SVG titles, link labels and destinations, ISBNs, publication/edition dates, retained retry history, host grouping, discovery-log validation and preservation of evidence labels. Link checks remain outside CI's network path to avoid converting transient access failures into dataset validation failures.

Technical references: [HTTP Semantics, RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html), [Internet Archive metadata API](https://archive.org/developers/md-read.html), [Crossref metadata API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/), [Open Library API and usage limits](https://openlibrary.org/developers/api).
