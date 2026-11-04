# Source policy

Open Arcana is a truth-seeking directory. It records what traditions keep secret, how that became known, and how reliable the evidence is. It is not there to protect secrets or to expose particular groups.

## Impartiality

- **One standard for every tradition.** Country, region, tribe, size, age and number of followers make no difference. A world religion, a small sect, an indigenous tradition and a magical order are all held to the same rules.
- **No special status.** Calling something sacred, secret or taboo does not exempt it from being recorded. Calling something heretical or dangerous does not make it a target.
- **Past and present.** Current practices are in scope as much as historical ones. Record whether an item is still practiced, modified or abandoned.
- **Describe, don't judge.** The tradition's own account and stated reasons are recorded next to those of critics and outsiders. The dataset does not decide which is true. That is left to the evidence and to whoever uses it.

## Accepted

- Published books, periodicals, newspapers and exposures, of any age
- Court records and other public legal filings
- Academic research and fieldwork
- Archival and manuscript collections
- Material released by the tradition itself
- Testimony from current or former participants
- Leaked, hacked or otherwise unofficially obtained material, and material from infiltration
- Material already circulating publicly (forum posts, archived websites, dumps)

How material was obtained is not grounds for rejecting it. It is recorded as provenance and used to judge how reliable the material is.

## Provenance

Every source records how it came to light in its `provenance` field:

| Value | Meaning |
|---|---|
| `official_release` | Published or released by the tradition itself |
| `published_exposure` | Published exposure whose author's access is not established |
| `defector_account` | Published or given by a former member with firsthand access |
| `court_filing` | Entered in a court file or other legal record |
| `insider_leak` | Passed on by a current member or employee |
| `intrusion` | Obtained by hacking or unauthorized access |
| `infiltration` | Gathered by someone who joined under false pretenses |
| `anonymous_posting` | Posted anonymously, with no traceable chain of custody |
| `archival_collection` | Held in a library, archive or manuscript collection |
| `academic_fieldwork` | Gathered by researchers through fieldwork or interviews |
| `reconstruction` | Pieced together from fragments or secondary accounts |
| `unknown` | Origin not established |

Use the notes to say what is known about the chain of custody. Provenance feeds the evidence level.

## Evidence levels

| Level | Meaning |
|---|---|
| `documented` | The source exists and says what the record claims |
| `corroborated` | Two or more independent sources agree |
| `single_testimony` | One firsthand account, not yet corroborated |
| `contested` | Sources conflict, or authenticity is disputed |
| `fabricated` | Shown to be fake; kept on record so it is not repeated |

For example, a dump whose origin can be traced and whose contents match independent copies can be `corroborated`. An anonymous document with no chain of custody stays `single_testimony` or `contested` until it is confirmed.

### Judging leaks and dumps

Record in the source's notes what each check showed:

- **Chain of custody:** who first released it, when, where, and whether that origin can be traced.
- **Size and structure:** how many documents or entries it contains, which fields or formats it uses, and whether these match the organisation's known internal documents or systems.
- **Internal consistency:** whether dates, names of offices, terminology and cross-references agree with each other throughout.
- **Checks against known facts:** whether its contents agree with court records, official publications, defector accounts and other verified sources.
- **Independent copies:** whether copies obtained separately match each other, by hash or record count. Note any differences, since they can point to tampering.
- **Response from the tradition:** whether the tradition confirmed, denied, contested it in court, or ignored it. A copyright or trade-secret claim over a document is strong evidence that it is authentic.
- **Known fabrications:** whether it matches a hoax or forgery that has already been recorded as `fabricated`.

Separately, `review_status` records whether a maintainer has checked the record against its source (`unreviewed`, `reviewed`, `disputed`).

## Who may be named

Attribution is part of the evidence, so anyone whose public role makes them a source may be named:

- Leaders, officials and public figures of a tradition
- Authors, editors and journalists of published works
- Witnesses, declarants and parties named in public court records
- Defectors and other participants who gave testimony under their own name

Contributors who give testimony to Open Arcana are not named unless they ask to be.

## Not accepted

- Fabricated or unsourced claims presented as fact. Contested material is accepted but labelled `contested`.

## Texts and rights

- `description` fields must be **original summaries**. Do not paste third-party text into the dataset.
- Full texts are not stored in this repository. A source may carry a `url`, `identifiers` and a `content_hash` (IPFS CID or sha256) pointing to a copy hosted elsewhere.
- Public-domain texts may be archived and mirrored freely.
- Any reference, identifier or metadata that can lawfully be published is in scope and should be added.

## Corrections and removal requests

Open an issue. Factual corrections with a source are applied quickly.

A request to remove accurately sourced information because a tradition considers it sacred, secret or offensive is not grounds for removal. Every decision is recorded publicly.

## Anonymous contributors

Contributors may remain anonymous. Do not include information that identifies you in a submission unless you want to be credited.
