# Leaks, recordings and distributed copies

Research date: 4 November 2026. Language inspected: English. Scope: restricted practices, instructions and ritual material, including sources outside conventional academic publication. This is a focused batch, not an exhaustive archive crawl.

## Audit and selection

Before this batch the collection had 93 sources: 33 books, 20 academic sources, one audio source, one video source and one broadcast, among other formats. The audio and video entries had not been directly reviewed. No source used the `insider_leak` provenance value, although some existing material had been disclosed without authorization through exposures, court files and anonymous postings. These counts establish a discovery and inspection gap; they do not establish why the gap arose or the reliability of any category.

The batch adds three items, four sources, six disclosures, 15 claims and eight artifact records. Two existing source records gain actual access links and inspection notes. It applies no academic, public-domain, institutional, medium or acquisition-route gate. Unknown or disputed origins stay recorded. Rights and provenance do not become truth labels.

## Searches and routes

- Public searches included `site.wikileaks.org Scientology OT documents 2008 secret bibles torrent`, `site.archive.org Mormon temple endowment NewNameNoah audio video transcript`, `site.xenu.net "Class VIII" audio`, and searches for Francis King’s *The Secret Rituals of the O.T.O.* in shadow-library catalogues.
- The WikiLeaks release page supplied direct PDF and torrent-metadata links. Both were retrieved; no torrent swarm transfer was initiated. The CMU OT III page supplied a short audio file and its accompanying transcription.
- Mormonism Research Ministry’s temple index supplied the specific NewNameNoah video and the Internet Archive ceremony lead. Its theological commentary was not used to authenticate either recording.
- A browser search at `annasarchive.io` for `The Secret Rituals of the O.T.O.` returned an item attributing a 1973, 3.1 MB PDF to Francis King, with a `nexusstc/zlib` collection label. The item page was read. Its viewer returned a general home/search page rather than readable book pages, so no payload or edition fidelity was established. The advertised fiction category and author/collection metadata were not adopted uncritically. Operator identity was not independently verified. This lead is ARTF-0008, not a new independent source or a content verification.
- Anna’s Archive dataset documentation for Z-Library and LibGen and the Nexus/STC project README were inspected as discovery infrastructure. Direct Z-Library/LibGen sessions, STC corpus queries, IPFS payload retrieval and bulk metadata dumps were not completed. No claim that a specific file is retrievable through those routes follows from documentation alone.
- A public hosted transcription of King’s exposed collection was inspected directly. A museum source was read to assess a false ritual allegation embedded in that text.

## Inspected artifacts and findings

| Artifact/source | Inspection | Evidentiary result and limits |
|---|---|---|
| **ARTF-0001 / SRC-0097**, [leaked OT PDF](https://file.wikileaks.org/file/scientology-ot-levels.pdf) | Complete 17,788,660-byte file captured; 612 pages identified. Contents and selected OT III/NOTs sheets read, including pp. 247, 373, 399–400 and 410; New OT VIII pp. 523–527 read, with the p. 523 image checked | Restricted auditing content is available beyond summaries of the cosmology. Its copy hash matches the release page. That does not authenticate the whole compilation. The New OT VIII section explicitly identifies itself as a memory reconstruction and must retain that qualification. |
| **ARTF-0002 / SRC-0097**, [torrent metainfo](https://file.wikileaks.org/torrent/scientology-ot-levels.pdf.torrent) | Bencoded metadata parsed; exact `info` dictionary hashed; filename, declared payload size and piece length read | Demonstrates a concrete torrent discovery route. Info-hash `4bc8f8fbf0bb7f7c674ae4fb21d67aed6778b6a4` identifies its manifest. Metainfo SHA-256 differs from PDF SHA-256. No swarm use or independent authenticity follows. |
| **ARTF-0003–0004 / SRC-0098**, [veil-instruction video](https://www.youtube.com/watch?v=Xg2bxBHbsIU) | Uploader page and 20 August 2012 upload date checked; selected frames inspected, including 01:40 and 04:26. Complete English automatic-caption export read, 00:12–05:28 | Captions describe marks, token names and a veil exchange. The data states that these are automatic-caption content claims; exact words, the whole soundtrack, setting and editing were not authenticated. The clip does not provide the final token’s exact name in its captions. The transcript hash is not a video hash. |
| **ARTF-0005 / SRC-0039**, [lecture excerpt](https://www.cs.cmu.edu/~dst/OTIII/xemu0.wav) | 169,125-byte WAV captured; 15.336-second mono-file metadata measured; host’s separate transcription read | The audio was not listened to and the full lecture was not retrieved. The new claim identifies its textual basis explicitly. Clip position within the lecture, speaker identity and editing remain unchecked. |
| **ARTF-0006 / SRC-0099**, [Archive metadata](https://archive.org/metadata/MormonTempleCeremony) | Complete metadata response and file list read | Advertises a ceremony recording added in September 2012. Payload coverage is unreviewed. The creator field was not accepted as recording authorship and the item was not assumed to be a Norton recording. |
| **ARTF-0007 / SRC-0009**, [exposed O.T.O. transcription](https://publicism.info/magic/full/thelema/oto/index.html) | *De Homunculo Epistola*, *De Nuptiis Secretis* section II and Appendix A read | Adds the proposed spirit-incarnation scheme and restrictions on a pregnant participant’s surroundings, together with the text’s initial willingness requirement. No performance or efficacy is established. Appendix A describes manuscripts/typescripts and some conjectural restorations; the web copy was not collated against print. |
| **SRC-0100**, [USHMM, Blood Libel](https://encyclopedia.ushmm.org/content/en/article/blood-libel) | Opening definition and discussion of prohibitions on murder and blood consumption read | Supplies counterevidence to the ritual-blood allegation reproduced in the exposed text. The allegation is preserved with `contradicted` support, under the accusing text’s item; it does not create an authenticated Jewish ritual record. |

Each captured artifact’s exact byte count and computed SHA-256 are in [`data/source_artifacts.csv`](../data/source_artifacts.csv). Full third-party payloads are not committed to the repository. The inherited `sources.content_hash` remains compatible; artifact records specify which bytes, stream or derivative were actually checked.

## Unresolved work

- Listen to the captured lecture excerpt and locate the full recording with its own time base; compare the host transcription rather than treating it as authoritative audio.
- Review the video’s original English audio and fuller footage, check captions and identify the recording date, temple and editing history. Inspect the separate Archive payload before making ceremony-content claims from it.
- Collate the exposed ritual text with a stable edition and its manuscripts; identify which historical teachings were performed and when.
- Retrieve and inspect specific shadow-library/IPFS candidates before asserting their content, hash or independence. Keep metadata-only leads visible rather than silently upgrading them.
- Extend discovery to additional traditions, languages and formats based on relevance and evidence gaps. Neither this batch nor its provider list represents all restricted knowledge.
