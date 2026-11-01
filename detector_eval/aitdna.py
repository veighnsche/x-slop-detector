"""Pinned public process-provenance pilot, not a representative X corpus.

No upstream code or LLM-derived intent/content annotations are executed or used.
Both conflicting advertised licenses allow private analysis; redistribution and
deployment rights remain unresolved. Keep corpus/weights outside public artifacts.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import urllib.request

from .data import Corpus, Example, Source, digest, split_corpus, text_hash, write_json

REVISION = "21d77f7d44833507750c0da309295c4147c1bda5"
FILE_SHA = "0641d20f9326522061bee792cad5f8963faf26bf37268e491f901cb7c2ce5cfb"
URL = f"https://huggingface.co/datasets/UKPLab/AITDNA/resolve/{REVISION}/span/test-00000-of-00001.parquet"
# Exact, process-level curation instructions, not detection/style heuristics.
# "Polish this text" is intentionally NOT assumed substantive: remains unknown.
SUBSTANTIVE_INSTRUCTIONS = frozenset({
    "Continue this text:\n",
    "Make the text sound more confident",
    "expand on this text and bullet points and provide a coherent narrative. make sure you do not lose out on any information. ",
})
POLICY = "aitdna-conservative-verbatim-and-retained-v1"
LIMITATIONS = [
    "Private research only: dataset metadata CC-BY-SA-4.0 conflicts with prose GPL-2.0; resolve before redistribution/deployment.",
    "Controlled English argumentative/creative/explanatory writing, not naturally short social posts or a sample of X.",
    "Short passages are derived from longer originals, not independently authored short posts.",
    "Source-reported genesis/human-only labels, not independent forensic proof of participant compliance.",
    "Substantive instruction subset only; ambiguous polish/mechanical assistance remains unknown, not human.",
    "No independently reviewed human-edited/translated/ideas-only control coverage.",
    "Topic/prompt/event independence unverified: source lacks reliable topic/prompt group identifiers.",
    "Base-detector training overlap unknown; held-out means unseen to this combiner only.",
    "No defensible deployment prevalence or transport assumptions; benchmark calibration cannot enable feed percentages.",
]


def family(model):
    return next((name for name in ("gemini", "gpt", "deepseek", "qwen", "llama") if name in model.lower()), None)


def bucket(text):
    n = len(text)
    return "1-80" if n <= 80 else "81-160" if n <= 160 else "161-280" if n <= 280 else ">280"


def passages(text):
    """Exact substrings. Regex English sentence boundaries are a documented limit."""
    out = [(0, len(text), "whole")]
    for match in re.finditer(r"\S[\s\S]*?(?:[.!?](?=\s|$)|$)", text):
        if match.group().strip():
            out.append((match.start(), match.end(), "sentence-derived"))
    # A bounded sample per root/length bucket, independent of detector outputs.
    choices = {}
    for start, end, kind in out[1:]:
        key = bucket(text[start:end])
        candidate = (text_hash(text[start:end]), start, end, kind)
        if key not in choices or candidate < choices[key]:
            choices[key] = candidate
    return out[:1] + [(a, b, kind) for _, a, b, kind in sorted(choices.values())]


def import_rows(rows, acquired_at):
    examples = []
    seen = set()
    human_sources = {
        r["metadata"]["author"]: (i, "".join(s["text"] for s in r["data"]))
        for i, r in enumerate(rows) if r["metadata"]["human_only"]
    }
    for index, row in enumerate(rows):
        meta, spans = row["metadata"], row["data"]
        author = "author-" + text_hash(meta["author"])[:24]
        root = f"aitdna-document-{index}"
        model = family(meta["model"])
        whole = "".join(s["text"] for s in spans)
        human_only = meta["human_only"]
        if type(human_only) is not bool:
            raise ValueError("invalid_source_human_only")
        if human_only and any(s["author"] != "User" for s in spans):
            raise ValueError("source_human_only_conflicts_with_genesis")
        for span in spans:
            if span["author"] not in ("User", "Bot"):
                raise ValueError("unknown_source_span_author")
        eligible = [
            (j, s) for j, s in enumerate(spans)
            if s["author"] == "Bot" and s["queries"] and set(s["queries"]) <= SUBSTANTIVE_INSTRUCTIONS
        ]

        def add(text, locator, label, cohort, derivation, basis, extra_groups=()):
            if not text.strip():
                return
            key = (root, text_hash(text), label, cohort)
            if key in seen:
                return
            seen.add(key)
            examples.append(Example(
                id="item-" + digest(key)[:32], text=text, text_sha256=text_hash(text),
                source_id="aitdna-span", source_locator=f"row:{index};{locator}",
                acquired_at=acquired_at, author_id=author, root_id=root,
                extra_groups=list(extra_groups),
                unverified_group_axes=["prompt", "topic", "event"], language="en",
                generator_family=None if human_only else model, cohort=cohort,
                derivation=derivation, label=label, label_basis=basis,
            ))

        if human_only:
            for a, b, kind in passages(whole):
                add(whole[a:b], f"document:{a}:{b}", 0, "unaided_human",
                    kind, "Source human_only=true and every retained span is User; participant-study provenance.")
        else:
            # Unknowns stay in denominators but never acquire a binary training label.
            add(whole, "document", None, "assisted_target_unreviewed", "whole",
                "AI involvement alone cannot establish substantive retained wording or mechanical-only assistance.")
            # Bounded across the complete document, not one quota per tiny diff span.
            selected = {}
            for j, span in eligible:
                for a, b, kind in passages(span["text"]):
                    text = span["text"][a:b]
                    key = bucket(text)
                    candidate = (text_hash(text), j, a, b, kind)
                    if key not in selected or candidate < selected[key]:
                        selected[key] = candidate
            for _, j, a, b, kind in selected.values():
                add(spans[j]["text"][a:b], f"span:{j}:{a}:{b}", 1,
                    "recorded_generation_or_style_rewrite", kind,
                    f"Verbatim Bot span under explicitly composing/style-rewriting instruction; policy {POLICY}.")
            # Controlled retained mixtures, NOT automatic labels for ambiguous
            # natural human editing. Join intact human and model passages whose
            # process origins are known, keep both roots in the same partition.
            human = human_sources.get(meta["author"])
            if human:
                human_index, human_text = human
                human_units = [(a, b) for a, b, _ in passages(human_text)
                               if len(human_text[a:b]) <= 280]
                if human_units:
                    a, b = min(human_units, key=lambda pair: text_hash(human_text[slice(*pair)]))
                    for j, span in eligible:
                        # Acquisition scope: complete retained passages, not a
                        # word-count threshold defining "substantive" authorship.
                        if span["text"].strip().endswith((".", "!", "?")):
                            mixed = human_text[a:b] + "\n\n" + span["text"]
                            add(mixed, f"controlled-concat:human-row:{human_index}:{a}:{b};bot-span:{j}",
                                1, "controlled_retained_mixture", "controlled-concatenation",
                                "Intact process-recorded model passage deliberately retained alongside an unaided human passage; not natural human editing.",
                                extra_groups=(f"root:aitdna-document-{human_index}",))
                            break
    return Corpus(
        population="AITDNA conservative English process-recorded pilot; constructed passage mixture, unknown deployment prior",
        sources=[Source(
            id="aitdna-span", url=URL, revision=REVISION, content_sha256=FILE_SHA,
            license="CONFLICT: metadata CC-BY-SA-4.0; prose GPL-2.0",
            permission_record="Pinned publisher card; both advertised licenses permit private evaluation; no redistribution or production entitlement claimed.",
            private_evaluation_allowed=True, redistribution_allowed=False, limitations=LIMITATIONS,
        )],
        examples=examples, limitations=[*LIMITATIONS, "Regex English sentence segmentation may split abbreviations; derived input is not original-post extraction."],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-file", required=True)
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    source = Path(args.source_file)
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = response.read(2_000_001)
        if len(data) > 2_000_000 or hashlib.sha256(data).hexdigest() != FILE_SHA:
            raise ValueError("source_download_hash_mismatch")
        source.write_bytes(data)
    if hashlib.sha256(source.read_bytes()).hexdigest() != FILE_SHA:
        raise ValueError("source_file_hash_mismatch")
    import pyarrow.parquet as pq
    corpus = import_rows(pq.read_table(source).to_pylist(), datetime.now(timezone.utc).isoformat())
    write_json(out / "corpus.json", corpus.model_dump(mode="json"))
    split = split_corpus(corpus, seed=20261101, reserved_family="gemini")
    write_json(out / "splits.json", split)
    from collections import Counter
    print({
        "examples": len(corpus.examples), "known_labels": dict(Counter(e.label for e in corpus.examples)),
        "partitions": dict(Counter(r["partition"] for r in split["rows"])),
        "release": "blocked; research pilot only",
    })


if __name__ == "__main__":
    main()
