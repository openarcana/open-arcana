# Source policy

Open Arcana is a truth-seeking directory. It records what traditions keep secret, how that became known, and how reliable the evidence is. It is not there to protect secrets or to expose particular groups.

## Impartiality

- **One standard for every tradition.** Country, region, tribe, size, age and number of followers make no difference. A world religion, a small sect, an indigenous tradition and a magical order are all held to the same rules.
- **No special status.** Calling something sacred, secret or taboo does not exempt it from being recorded. Calling something heretical or dangerous does not make it a target.
- **Past and present.** Current practices are in scope as much as historical ones. Record whether an item is still practiced, modified or abandoned.
- **Record perspectives and assess factual claims.** The tradition's own account and stated reasons are recorded next to those of critics and outsiders. Apply the same evidence tests to all of them. Stronger evidence receives stronger support labels; equal treatment does not imply equal evidentiary weight. Readers can inspect and challenge the assessment.

## Inclusion

Records concern specific restricted rites, initiations, practices, teachings, texts, oral transmissions or internal manuals. Identify what was restricted, to whom, and how the source documents it. Misconduct belongs in a record when it is part of that practice or its enforcement. A scandal, accusation, private affair or confidential investigation does not qualify merely because a group wanted it kept quiet.

Record the evidence that puts each item in scope: for example, an explicit confidentiality or transmission rule, controlled access, or a described initiation. A sacred label, specialist role, fee or exclusive performance role does not by itself establish secrecy. A public description can establish that an initiation exists without revealing its restricted content; keep that limit explicit. The purpose of a rite and the reason for restricting access are separate claims.

Open Arcana applies no categorical exclusion based on a source's origin, method of acquisition, institutional authorization, religious status or perceived legitimacy. Official publications, historical exposures, leaked documents, material obtained through unauthorized access or infiltration, anonymous disclosures, reconstructions and firsthand testimony are all eligible.

Within that subject scope, relevance and the quality of the evidence determine its treatment. No academic, institutional or public-domain preference applies. Leaked scans, internal manuals, recordings, photographs, messages, database exports and mixed document dumps are eligible. Unknown provenance is an uncertainty to record, not a reason to reject a source. Neither an institutional imprint nor an unauthorized release supplies an automatic authenticity or truth judgement.

Anna’s Archive, Z-Library, Library Genesis, Nexus/STC, IPFS, torrents and other archives may be used to discover and identify material. A repository or transport is an access route, not an independent evidentiary origin. Assess the actual file, edition, recording or collection; a mirror does not gain or lose factual credibility just by moving hosts. Access or redistribution rights are recorded separately from evidentiary quality.

Sacred status, taboo, offence, respect for an institution or fear of reputational damage is not by itself a reason to leave out sourced knowledge. Describe relevant content precisely, with its context and uncertainty, rather than obscuring it through euphemism. Evidence eligibility and permission to host a third-party text remain separate questions. Apply the same inclusion standard to material supporting and challenging a tradition's account.

Inclusion is not endorsement or verification. Each source is recorded with its provenance and an assessment of its authenticity, and each specific assertion is recorded with the sources that support or contradict it.

Evidence of fabrication, contradiction or uncertainty is kept and labelled, not erased. The aim is to preserve the evidentiary record, errors and disputes included, so that people and AI systems can evaluate it for themselves.

## Separate questions

The dataset never lets one judgement stand in for another:

| Question | Where it is recorded |
|---|---|
| Does the source exist, and does it contain this material? | `disclosures` (checked through `review_status`) |
| Is the source authentic: is it what it claims to be? | `sources.source_authenticity` |
| Is what it says about the item accurate? | `claims` of type `content`, with their `claim_support` |
| Was the item actually practiced in a given period? | `claims` of type `historical_practice` |
| Is it still practiced today? | `claims` of type `current_practice` |
| Was knowledge of it suppressed after it came out? | `claims` of type `suppression` |

A genuine initiation manual can describe a ceremony that was never performed, was performed differently, or has since been dropped. Each of those is a separate claim, needing its own evidence.

`restriction_mechanism` can include `controlled_access`: restricted entry to a ritual space, viewing of objects, custodianship or transmission rights. Describe the actual rule in `restricted_to` and the cited claims, including gender, initiation, lineage or role where documented. This value does not assert a particular sanction or an oath.

## Provenance

Every source records how it came to light in its `provenance` field. When material passed through several hands, list each step in order, earliest first, separated by semicolons: for example `court_filing;anonymous_posting` for court exhibits later posted online.

| Value | Meaning |
|---|---|
| `official_release` | Published or released by the tradition itself |
| `member_publication` | Published by a member or teacher on their own authority, not by the tradition as a body |
| `published_exposure` | Published exposure whose author's access is not established |
| `defector_account` | Published or given by a former member with firsthand access |
| `court_filing` | Entered in a court file or other legal record |
| `official_seizure` | Seized by police, soldiers or other authorities |
| `insider_leak` | Passed on by a current member or employee |
| `intrusion` | Obtained by hacking or unauthorized access |
| `infiltration` | Gathered by someone who joined under false pretenses |
| `covert_recording` | Recorded on audio, video or camera by an attendee without the tradition's permission |
| `anonymous_posting` | Posted anonymously, with no traceable chain of custody |
| `archival_collection` | Held in a library, archive or manuscript collection |
| `academic_fieldwork` | Gathered by researchers through fieldwork, interviews or excavation |
| `investigative_reporting` | Firsthand journalistic or institutional investigation, including interviews and human-rights monitoring outside academic fieldwork |
| `scholarship` | Edited, translated or analysed by scholars from texts and other existing material, without fieldwork |
| `reconstruction` | Pieced together from fragments or secondary accounts |
| `unknown` | Origin not established |

Provenance informs the authenticity assessment but does not settle it. Use `verification_notes` to say what is known about the chain of custody.

### Copies, streams and bundles

`source_artifacts` separates a source work from its particular files, streams, transcripts and bundle manifests. Each artifact links to a source and records its format, HTTP URL and/or IPFS CID or BitTorrent v1 info-hash, a member path where relevant, and what was actually inspected. There is no HTTP-only eligibility requirement: a content identifier can identify an artifact without a live web mirror.

`sha256` and `size_bytes` describe bytes actually captured together. A publisher-reported digest remains in notes until checked. A torrent info-hash identifies its bencoded payload manifest; it is not the payload file’s SHA-256. An IPFS CID does not by itself prove the content was retrieved or authenticated. Hashes of OCR, captions, transcripts or re-encodings identify those derivatives, not their originals. Identifier syntax checks do not verify remote availability or payload integrity.

`inspection_status` is `metadata_only`, `partial` or `complete` for that artifact, with exact inspected portions. Inspecting a complete catalogue response or torrent manifest does not mean its advertised payload has been inspected. A recording’s transcript can be inspected while its audio remains unchecked. In mixed dumps, assess individual components and versions; do not extend one authentic page’s status to the whole bundle. Identical captured bytes linked to multiple sources are flagged for dependence review rather than automatically counted as independent evidence.

### Dates

`original_year` is when the work was first published or the record created. `edition_year` is the year of the copy that `url`, `identifiers` and `content_hash` point to, when it differs. A 1946 printing of an 1866 text has `original_year` 1866 and `edition_year` 1946.

## Source authenticity

`source_authenticity` says whether the source is what it claims to be: for example, whether a leaked manual really is the organisation's internal manual, or whether a published ritual matches what the order used.

| Value | Meaning |
|---|---|
| `unassessed` | Not yet assessed. The default for new records |
| `verified` | Authenticity established by checks recorded in `verification_notes` |
| `probable` | Checks point to authentic, but are incomplete |
| `uncertain` | Too little evidence either way |
| `disputed` | Credible evidence both for and against |
| `disproven` | Shown to be fabricated or misattributed. Kept on record so it is not repeated |

### Checks for leaks, dumps and anonymous documents

Record in `verification_notes` what each check showed:

- **Chain of custody:** who first released it, when, where, and whether that origin can be traced.
- **Size and structure:** how many documents or entries it contains, which fields or formats it uses, and whether these match the organisation's known internal documents or systems.
- **Internal consistency:** whether dates, names of offices, terminology and cross-references agree with each other throughout.
- **Checks against known facts:** whether its contents agree with court records, official publications, defector accounts and other sources.
- **Independent copies:** whether copies obtained separately match each other, by hash or record count. Note any differences, since they can point to tampering.
- **Response from the tradition:** whether the tradition confirmed, denied, contested it in court, or ignored it. A copyright or trade-secret claim over a document is contextual evidence that the tradition regards it as its own material. It is not conclusive on its own: claims can be made over altered or partial copies, or to suppress a document regardless of its accuracy.
- **Known fabrications:** whether it matches a hoax or forgery already recorded as `disproven`.

### Checks for audio, video and images

Recordings are documents, not testimony, and are assessed with the checks above plus these:

- **Original file:** whether the earliest available upload or file can be found, and its date, duration, resolution and metadata. Record its `content_hash` before any re-encoding.
- **Editing:** cuts, splices, dubbed audio or missing segments, judged from continuity of sound, lighting, camera position and on-screen clocks.
- **Setting:** whether the room, furniture, vestments and participants match known photographs, floor plans or descriptions of the place.
- **Text match:** whether what is said or done matches published texts of the same rite. Wording that matches a text exactly can mean either authenticity or a staged reading of that text, so note which explanation the other checks support.
- **Independent recordings:** whether recordings made separately, by different people or at different times, agree with each other.

Recordings are often taken down. Archive a copy (for example on the Internet Archive or the Wayback Machine) when a source is added, and record the archived URL in `url` or `identifiers`.

## Claims

A claim is one specific assertion about a restricted item, such as what a ceremony contains, that it was practiced in a given period, that it is still practiced, that it changed, or the reason the tradition itself gives for restricting it (`stated_reason`, best sourced from the tradition's own statements). Write the statement in your own words and list the sources that support it and any that contradict it, with page, section, exhibit or timestamp references in `locators`. For audio and video, give start and end times (`00:14:30–00:21:10`) and say which upload or copy the times refer to.

| `claim_support` | Meaning |
|---|---|
| `independently_corroborated` | Two or more independent sources support it, and none credibly contradicts it |
| `single_source` | One source, or several that are not independent of each other |
| `insufficient` | Sources mention it but do not establish it |
| `contradicted` | Credible sources contradict it |

### Independence

Sources count as independent only if neither derives from the other and they do not share an upstream origin. A book that reprints a leak, two newspapers quoting the same press release, or postings that copy court exhibits are not independent of their origin. Different authors, publishers or court cases alone do not establish independence. List the supporting sources counted as independent in `independent_source_ids`, and explain the checks and their scope in `verification_notes`. For `independently_corroborated`, the record must be reviewed, have locators and identify at least two distinct independent supporting sources, with no contradicting sources. Automatic validation checks this consistency; it cannot establish independence by itself.

Keep claims narrow enough that their support label applies to the entire assertion. Split out a detail that rests on only one source rather than lending it the corroboration of neighbouring details. If independence has not been established, retain the evidence under `single_source`, or `insufficient` when the evidence itself has not been established.

### Practice status and dates

The `current_status` on an item is a recorded assessment, not an assertion that an old account still applies today. Link reviewed, supported claims for the same item in `status_claim_ids`, and give the date for which they establish that status in `status_as_of`. A `practiced` status needs a `current_practice` claim; `modified` and `discontinued` need a `change` claim. A date records the scope of the evidence, not a guarantee that a practice has continued since then. Without linked, dated evidence, a seed status remains provisional and is flagged in the catalogue and exports. Historical observations belong in `historical_practice`, even when their source describes them as current at the time.

### Testimony and documents

Testimony (a person's account of what they saw or did) and documents (a manual, ritual text or file) are judged differently. A named defector's account is testimony; an anonymous document is a document whose authenticity is unassessed. Record which one a source is through its `source_type` and `provenance`, and do not treat an anonymous document as if it were testimony, or the reverse.

### Suppression

Knowledge can be buried after it comes out: a court stops a book, an archive closes a collection, scholars hold back what they recorded, a tradition denies something it later admits, or a literal practice is recast as symbolic. A `suppression` claim records that this happened, with its method in `suppression_method`, and needs evidence of its own, such as the injunction, the withdrawal notice, the archive's access rules or the scholar's own statement.

| `suppression_method` | Meaning |
|---|---|
| `court_injunction` | A court order stopped publication or distribution |
| `publication_withdrawn` | A publisher or author pulled the work |
| `archive_restricted` | An archive, museum or library closed access |
| `scholarly_self_censorship` | Scholars withheld or blurred material they had |
| `official_denial_later_admitted` | The tradition denied something it later acknowledged |
| `official_condemnation` | A religious or state authority condemned the teaching as heresy or banned it, so that it survives mainly through its opponents |
| `apologetic_reinterpretation` | A literal practice was recast as symbolic or allegorical |
| `community_pressure` | Protests, threats or sanctions against publication |

Suppression is not evidence of truth, and openness is not evidence of falsehood. Whether the buried material is accurate is a separate `content` claim, judged on its own sources like any other. Claims about a whole people, tribe or community are recorded and graded by the same rules: sourced, given a `claim_support` level, and marked `contradicted` when the evidence goes against them.

## Disclosures

`investigative_report` identifies disclosures through institutional investigation reports, distinct from academic research or a journalistic article. A report remains eligible only when it documents material within the scope above.

A disclosure records that a source made a restricted item public, and how much of it:

| `extent` | Meaning |
|---|---|
| `full` | The whole item, as practiced in the version the source describes |
| `partial` | Some identifiable parts of the item |
| `summary` | A description in the source's own words, without the item's text |
| `reference` | Mentions the item exists, with little or no content |

Use `coverage` to say which parts, degrees, versions or editions the source covers, and which it leaves out.

## Review status

`review_status`, on disclosures and claims, records whether a maintainer has checked the record against its sources: `unreviewed`, `reviewed` or `disputed`. It says nothing about authenticity or truth.

Every status is displayed explicitly in the catalogue and preserved in the exports. [`QUALITY.md`](QUALITY.md) and `exports/quality.json` expose incomplete evidence; they do not impose an exclusion rule or calculate a truth score. Record-level qualifications travel with JSONL records for people and automated consumers.

## Who may be named

Attribution is part of the evidence, so anyone named in a source may be named in the dataset, including:

- Leaders, officials and public figures of a tradition
- Authors, editors and journalists of published works
- Witnesses, declarants and parties named in public court records
- Defectors and other participants who gave testimony under their own name

Contributors who give testimony to Open Arcana are not named unless they ask to be.

As with everything in the dataset, a name is added only where publishing it is lawful (see [Texts and rights](#texts-and-rights)).

## Not accepted

- Claims with no source. Every disclosure and claim must point to at least one source.
- Fabricated material presented as genuine. Known fabrications are kept, but only as sources marked `disproven`.

## Texts and rights

- `description` fields must be **original summaries**. Do not paste third-party text into the dataset.
- Full texts are not stored in this repository. A source may carry a `url`, `identifiers` and a `content_hash` (IPFS CID or sha256) pointing to a copy hosted elsewhere.
- Public-domain texts may be archived and mirrored freely.
- Any reference, identifier or metadata that can lawfully be published is in scope and should be added.
- Eligibility as evidence and permission to redistribute are separate questions. A source can be catalogued and assessed in full whether or not its text can be hosted.

## Corrections and removal requests

Open an issue. Factual corrections with a source are applied quickly.

A request to remove accurately sourced information because a tradition considers it sacred, secret or offensive is not grounds for removal. Every decision is recorded publicly.

## Anonymous contributors

Contributors may remain anonymous. Do not include information that identifies you in a submission unless you want to be credited.
