# Replacement short-post benchmark — acquisition not yet complete

**Implemented:** independent-group preflight/fit/evaluation gates and a private writing-process intake CLI. **Not obtained:** a new, sufficiently large, independently sourced short-post corpus or new contributor permissions. These tools and budgets do not themselves constitute a trustworthy benchmark.

The first pilot remains a historical, unsuccessful research run. Its data, frozen profiles, report and holdout receipt are preserved; it is not a source of fresh final-test examples.

**Contributor-study continuation:** the user agreed to pursue the recommended contributor study. A [costed pilot proposal, consent/reviewer drafts and offline collection-slot pack](contributor-study.md) are now prepared. This does not mean recruitment, spend, legal terms, public hosting, or the full-study budget have been approved.

## 1. Executable adequacy policy

The versioned [policy](../detector_eval/adequacy.py#L14) now runs:

- Before the collector reads an SSH credential or opens an HTTP client.
- Before fitting any candidate, calibrator, or operating threshold, and before creating a run directory.
- Before final evaluation reads profiles or creates a holdout-use receipt.
- Inside development cross-validation, checking each training and validation fold separately.

Before collection, counts are explicitly an **upper bound**: supported language/character length and known labels, but no detector evidence yet. After collection, they are recomputed using complete native evidence; unavailable/unsupported checks cannot inflate usable counts.

Only eligible **`native_short` originals** contribute to these acquisition floors. Longer originals, shortened passages and constructed mixtures can remain supplementary evidence, but cannot fill the natural-short budget. Counts also retain all-origin groups to make the distinction visible. “Native short” is a process declaration checked by the operator/reviewers, not something a hash or length check can prove.

| Partition | Minimum negative connected groups | Minimum positive connected groups |
| --- | ---: | ---: |
| Development | 50 | 50 |
| Calibration | 50 | 50 |
| Operating threshold | 600 | 50 |
| Main holdout | 600 | 50 |
| Unseen-family challenge | 50 | 50 |

Each CV training fold needs at least 20 qualifying native-short groups per class; each validation fold needs 10. There is no CLI “allow small study” switch. Synthetic unit tests explicitly patch budgets **inside the test process only**.

**These are conservative initial acquisition floors, not validated statistical sufficiency or a promised accuracy level.** The 50-group floors are engineering safeguards against the previous one/few-positive-group failure, not a power calculation for calibration/recall. The negative budget uses a separate calculation: with zero errors, the independent Bernoulli one-sided 95% bound at 0.5% needs at least **598** observations; 600 is the rounded collection floor. Observed errors, subgroup claims, dependence and nonrepresentative sampling can require substantially more.

The challenge's smaller floor does not establish a 0.5% FPR there. Language/length/cohort coverage and a useful recall/coverage threshold require additional preregistered budgets and acceptance criteria. Passing these checks never sets `deployment_approved`.

Across the disjoint partitions this requires at least 1,350 negative-class group memberships and 250 positive-class group memberships. A group may legitimately contain both a human original and matched generated variants; these are not automatically 1,600 different people. Shared authors, roots, real prompts/topics/events and duplicates still connect records; do not invent new identifiers to meet a quota.

### Audit a study without changing it

```sh
.venv-evaluation/bin/python -m detector_eval.adequacy \
  --study .cache/evaluation/aitdna-pilot-v1
```

Exit 2 means inadequate; exit 0 means the applicable count checks passed, **not scientific/release approval**. `--output NEW_FILE.json` optionally saves an audit without overwriting any earlier file.

The original real pilot fails this policy. Its actual complete-evidence positive groups were 5/1/3/2/12 across development/calibration/operating/holdout/challenge, and none of its derived short passages qualifies as `native_short`. A real refit attempt was rejected before creating a new run directory. This corrects future behavior without rewriting its historical outcome.

## 2. New process-backed collection

The [intake CLI](../detector_eval/intake.py#L1) accepts private JSON plus referenced artifacts, not CSV labels guessed from content.

For each record:

1. Obtain explicit private-evaluation permission, including any intended derivative generation/editing. Record redistribution separately; do not assume it. Keep identity/contact/withdrawal records separately from pseudonymous study IDs.
2. Record the original writing task, exact final text, tool-use declaration and writing/edit history. Human-only means a controlled unaided workflow, not “a public account looks human.”
3. For generation, retain the exact prompt/output plus model family/ID/revision and an execution/configuration record: settings, seed or actual unavailability, tokenizer/template where applicable, route and time. Never put an API key in an artifact.
4. Declare original versus derived/constructed input; `native_short` is at most 280 Unicode code points, **not X's weighted character allowance**. Preserve whitespace, emoji, links and line breaks. Do not truncate a long source and call it an original short post.
5. Give the writing-process evidence to two independent human reviewers, blinded to detector scores. Record pseudonymous reviewer IDs, decisions, evidence references and reasons. No detector or LLM-judge labels. Each review must reference the required permission/final/process/generation artifacts. Disagreement, missing reviews and “unknown” remain **unknown**, not negative.
6. Keep all real author/root/prompt/topic/event/derivative links together. Use specific scenario/event blocks, not the same generic topic ID for every participant. Conversely, do not give genuinely shared prompts different IDs to force independence.

The importer verifies UTF-8 bytes, artifact hashes, bounded files, references/path containment, source permissions as declared, required workflow records, review consistency and original-length declarations. It cannot authenticate a signature, prove someone did not paste AI text, establish that reviewer IDs belong to independent people, or settle legal rights. Those remain operator/recruitment/review responsibilities. A forged but internally consistent bundle is not made genuine by passing a validator.

### Workflow labels

| Recorded workflow | Known label after agreeing process reviews |
| --- | --- |
| Unaided original | Negative |
| Recorded generation, substantive rewrite or translation | Positive |
| Human-edited AI wording or retained mixed human/AI wording | Positive when substantive retention is supported; otherwise unknown |
| Mechanical-only corrections | Negative; even an LLM-assisted correction is not automatically substantive rewriting |
| Ideas only / discarded AI wording | Negative when process evidence supports independent final wording |

For unchanged generation/rewriting/translation workflows, final bytes must equal the recorded generation output. If someone edited it, use an edited workflow and keep the history. Mixed/edited/mechanical/ideas workflows require edit records. A content-style judgment cannot resolve missing provenance.

### Task and coverage worksheet

Use matched tasks/lengths across human and generated cohorts; do not make humans informal and all models polished. Humans write before seeing generated counterparts. Plan disjoint scenario/author blocks before acquisition and freeze a generator-family challenge. Do not hunt random seeds after seeing detector results. The proposed contributor study uses [preassigned unequal-quota slots](contributor-study.md#6-generate-the-private-preparation-pack), not the older equal-fold importer, to avoid buying far more contributors than the operating/holdout quotas need.

| Coverage | Original task pattern, not benchmark text |
| --- | --- |
| Replies and very short replies | Respond to a newly authored everyday scenario; include 1–4-word responses without forcing “AI-like” style. |
| Jokes | Write an original observation about an everyday inconvenience; do not copy an existing joke. |
| Arguments | Agree/disagree with a participant-authored claim; keep the claim and response linked. |
| Technical writing | Explain a nonconfidential problem or workaround from the contributor's experience. |
| Non-native English | Recruit actual consenting contributors; do not ask a model/native writer to imitate non-native identity. |
| Emoji and links | Allow normal usage; retain exact bytes, link rendering and original writing process. |
| Quotations | Use permission-backed quoted material and retain span/context; X embedded quoted posts remain separate from own-post input. |
| Longer posts | Retain original longer writing as a separate cohort, not a substitute for short originals. |
| Rewrites/translations/edits/mixed | Derive from permission-backed originals with recorded model calls and human edit history. |
| Mechanical/ideas controls | Record the actual tool use, what changed, and which generated wording was discarded. |

Collect every workflow across the relevant character buckets (1–80, 81–160, 161–280, >280), styles, languages and multiple generator families/versions. This worksheet is a collection inventory, **not a claim that every cell is already populated**. The intake summary exposes zero workflow/tag counts and length distributions; sparse or absent cells remain unsupported.

### Run the intake

```sh
# Use an ignored, private location. Schema contains no fabricated participants.
mkdir -p .cache/evaluation/short-post-collection-v1
chmod 700 .cache/evaluation/short-post-collection-v1
.venv/bin/python -m detector_eval.intake schema \
  --output .cache/evaluation/short-post-collection-v1/intake.schema.json

# AFTER real permission/process/review records have been assembled:
.venv-evaluation/bin/python -m detector_eval.intake import \
  --bundle .cache/evaluation/short-post-collection-v1/bundle.json \
  --artifacts .cache/evaluation/short-post-collection-v1/artifacts \
  --output .cache/evaluation/short-post-study-v1 \
  --reserved-family FAMILY_ACTUALLY_PRESENT_IN_THE_RECORDS
```

Import writes a **new 0700 directory** with corpus/splits, intake summary, and precollection adequacy audit. An inadequate import exits 2 but retains those preparation artifacts; it does not run detectors. Output directories/files are never overwritten. Preserve raw permission/process/review bundles privately alongside their fingerprints; the corpus is not a replacement for those records.

The existing scoring pipeline currently supports English inputs only; intake accepts other language records and reports their provenance, but they cannot fill its eligible budgets or authorize an English-only product scope. Other-language validation/scoring remains work, not a silently dropped requirement.

## 3. Source investigation, not a substitute for acquisition

Rechecked official sources **1 November 2026**:

| Source | Finding | Role / remaining action |
| --- | --- | --- |
| [MultiSocial official API](https://zenodo.org/api/records/13846152), revision 10 | Restricted access, no downloadable files returned; metadata CC BY 4.0 conflicts with noncommercial-research prose. The authors explicitly warn that older human-source labels may be inaccurate. | Potential supplementary social/multilingual stress set after access/terms clarification; not process-backed primary human gold. No access application submitted. |
| [TweepFake official repository](https://github.com/tizfa/tweepfake_deepfake_text_detection) and [paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0251415) | 25,836 tweets but only 17 human accounts / 23 bots, including older Markov/RNN/LSTM/GPT-2 generation. Account origin is not per-item controlled writing history. Dataset rights were not established from the code repository. | Historical short-text stress candidate, not thousands of independent modern-generator examples or the required false-positive study. No corpus imported. |
| [CoAuthor official page](https://coauthor.stanford.edu/) | Rich keystroke records, but 63 writers / 1,445 longer writing sessions, around 418 words on average, with older GPT-3 instances. No unambiguous dataset-license grant established from the checked page. | Potential assisted-writing process supplement after permission clarification; not natural short-post controls or enough independent human groups. No corpus imported. |
| [EmpatheticDialogues official repository](https://github.com/facebookresearch/EmpatheticDialogues), [license](https://github.com/facebookresearch/EmpatheticDialogues/blob/main/LICENSE) | Original crowdsourced conversations, publicly downloadable, CC BY-NC 4.0. Short dialogue is relevant, but global author/lineage independence, underlying provenance detail and intended-use compatibility have not been established for this study. | Possible noncommercial dialogue stress/control supplement after those checks; not automatically X gold or production-cleared. No corpus imported. |
| [RAID official repository](https://github.com/liamdugan/raid) | Broad generated-text benchmark, but existing detector training exposure and non-social domains remain concerns. | Supplementary regression/adversarial work, not fresh independent final validation. |

No new source corpus was downloaded/imported under this step, and no collected user posts were sent to a provider. Do not confuse reviewing availability with obtaining permissions or evidence.

## 4. Current blocker and verification boundary

The new, adequately sized benchmark **does not yet exist**. The next external input is actual permission-backed writing-process records/contributors, or approval of a concrete recruitment route/budget and its consent/retention terms. Generating more model output alone cannot supply independent human controls or natural human edits.

Software tests use explicit synthetic fixtures: they exercise workflow handling, permission/hash/path checks, disagreement, shared-source counting, missing evidence, CV budgets, and rejection before fitting/holdout consumption. Those tests are not benchmark examples, real consent, human review, or accuracy evidence.

Recorded checks: 100 Python tests discovered, 96 passed / four optional inference skips with evaluation dependencies; 89 passed / eleven optional skips in the lightweight environment. The intake schema CLI and a full synthetic import CLI ran; the import wrote preparation files but exited inadequate without collecting evidence. The real old-pilot refit was rejected without creating a run, and its historical report hash remained unchanged. Thirty Node tests, whitespace checks, and wheel construction/source verification also passed. No new checks were run on the GPU host.

No GPU/service resume, recruitment, paid call, provider application, public-data redistribution, new final evaluation or scoring-profile deployment was performed in this step.
