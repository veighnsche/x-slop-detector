# Contributor study — proposed paid pilot, not launched

For a self-contained document to forward to Finance, use the [funding proposal](finance-proposal.md). This document retains the technical preparation and operational detail.

**Subsequent financial challenge:** the Finance proposal now documents the decision history, assistant-introduced cost assumptions, alternatives and rejection reasons. Its revised recommendation is to hold paid commitments pending bounded due diligence—not automatically release the $1,000 pilot or treat the full forecast as necessary. The original proposal/calculator below is preserved, not a supplier quote or optimized study design.

The user approved pursuing the recommended contributor study. That authorizes this preparation, **not an unspecified spend, acceptance of platform/legal terms, publication of recruitment, or public exposure of the existing GPU service**.

**Recommendation:** approve a separately capped **30-person collection-method pilot**, evaluate its collection/review feasibility, and only then decide whether to fund the full benchmark. No participant has been contacted or recruited, no account/study has been created, and no payment has been made.

## What is prepared

- An [offline study-pack compiler](../detector_eval/study.py#L1): cost estimates, unassigned pilot/main collection slots, plan fingerprints and explicit launch blockers. It has no recruitment, payment, networking or publishing implementation.
- [Preassigned intake](../detector_eval/intake.py#L247): collected pseudonymous authors can bind to preregistered slots instead of the older equal-sized folds. Shared sources/duplicates across partitions are rejected, not relabeled independent.
- Participant information/consent **draft**, collection script, review rubric, payment/withdrawal/security checklist and a cost model below.

**Not prepared for public use:** a participant collection website, payment/completion integration, identity registry, deletion/withdrawal implementation, privacy-reviewed public hosting, or final legal documents. Existing intake validates supplied artifacts; it does not collect browser writing events. No human or accuracy study has started.

## 1. Paid pilot: 30 adults, estimated 20 minutes each

Purpose: measure whether people understand the tasks/consent, whether process records are sufficient, how long writing and review take, and how many records/groups survive provenance/duplicate/support checks. **Not** to claim a 0.5% false-positive rate, calibrate a production percentage or select a final detector.

- Recruit adults who write short online messages in English, including consenting self-described non-native English writers. Initial English is a study staging choice, not an English-only product decision.
- Do not collect names, handles, X accounts, emails, employer, exact birth date, identity documents, race, health information, or political/religious affiliation.
- Use Prolific's permitted pre-screeners where available. Any custom screening must be paid/approved under platform rules; its cost is not assumed free.
- One real contributor = one stable pseudonymous author across visits/variants. Exclude pilot contributors from the main study using the platform exclusion mechanism and private identity registry. Never rename them to make fresh independent groups.
- Pilot slots are **development-only**. Its observations may change the protocol; they cannot later become untouched final evidence.

### Session script

| Step | Proposed task / record |
| --- | --- |
| Consent and practice | Explain the AI-detection purpose, scoped editor history and data use; obtain affirmative timestamped consent **before** saving task text or participant ID. Run an original practice example. |
| Four unaided originals | Author new everyday scenarios and own-post responses: a very short reply; a joke/observation; an argument or nonconfidential technical explanation; an emoji/link/quotation-capable post. Rotate character buckets and styles rather than making all humans informal and all AI outputs polished. |
| Declared assistance control | Assign a mechanical-only or ideas-only workflow. Retain the original, exact assistance/tool record, what changed/discarded and final wording; unknown if its scope cannot be established. |
| Recorded AI-edit workflow | After unaided writing is complete, present a model draft from an authorized controlled route, then retain all human revisions and final wording. If no working authorized generation route exists, do not pretend this task was performed. |
| Debrief and completion | Confirm actual tools used and any accidental personal/third-party content. Allow withdrawal/reporting of technical issues. Validate the completion/payment route without using detector outputs to judge effort or payment. |

Timing is an **estimate** to test, not a 20-minute forced cutoff or a justification for underpayment. Adjust rewards upward if measured completion time exceeds the planned rate. Do not reject or withhold pay because a detector says “AI”, because a participant admits assistance, or because a useful sample remains unknown.

The four unaided texts plus assisted variants are related records, **not six independent people**. A generic instruction template can be shared, but actual reused scenarios/prompts/events and duplicate inputs must retain their real links. Common tiny strings can connect contributors; measure that loss rather than breaking groups to pass quotas. Predeclare how linked groups crossing reserved slots are quarantined/replaced, keep an acquisition log, and do not silently discard the very-short cohort.

## 2. Proposed budget — no spend authorized

Checked [Prolific's official pricing](https://researcher-help.prolific.com/en/articles/445239-what-is-your-pricing) and [pay guidance](https://researcher-help.prolific.com/en/articles/445266-how-much-should-i-pay-participants) on **1 November 2026**:

- Published platform fee: **42.857%** of rewards for corporate accounts; **33⅓%** for qualifying academic/non-profit accounts. A personal email does not establish eligibility for the discount.
- Platform absolute minimum: $8/hour; recommendation at least $12/hour. **This proposal uses $15/hour** for writing.
- VAT may apply to the **platform fee**, depending on the actual account/jurisdiction.

Use the higher corporate fee for planning until the actual account quote is known. Budget fees conservatively on reviewer/training rewards too; if reviewers are internal/contracted outside Prolific, the actual fee/tax treatment will differ. Reviewer pay/duration is an assumption, not a vendor quote.

| Pilot line item | Assumption | USD estimate |
| --- | --- | ---: |
| Writing | 30 × 20 minutes at $15/hour = $5 each | $150.00 |
| Two independent process reviewers | 30 contributor blocks × 10 minutes × 2 reviewers at $25/hour | $250.00 |
| Reviewer training | Two reviewers × 2 hours each at $25/hour | $100.00 |
| Platform fees on all three lines | 42.857% | $214.29 |
| Subtotal before VAT/reserve | | $714.29 |
| With 20% contingency, before VAT | | **$857.14** |
| With illustrative 20% VAT on the platform fee, then contingency | VAT rate is not yet established | **$908.57** |

**Proposed pilot spending cap: $1,000 USD total.** This is a request for approval, not an already authorized charge or a guaranteed all-inclusive quote. Account quote, taxes, hosting, any screening, generation and other costs must fit within the cap; pause and ask before exceeding it. Do not commission fixed-price obligations that exceed the remaining cap.

### Full study: important scale/cost warning

The existing adequacy policy needs 50/50/600/600/50 independent negative groups across development/calibration/operating/holdout/challenge. A roughly even five-fold split would need far more total recruitment to fill the two large partitions. Instead, the proposed initial slots are:

| Partition | Main collection slots | Minimum qualifying negative groups |
| --- | ---: | ---: |
| Development | 75 | 50 |
| Calibration | 75 | 50 |
| Operating point | 750 | 600 |
| Main holdout | 750 | 600 |
| Family challenge | 75 | 50 |
| **Total** | **1,725** | **1,350** |

Slots allow for some loss, but do **not** guarantee 1,350 independent usable groups. Positive counterparts require at least 50 qualified independent groups per partition and suitable generator/cohort coverage. Review disagreements, duplicates, withdrawals and unsupported inputs may require replacements.

Under the same paid-review assumptions, the full main study—not including the separate pilot—estimates:

- Writing rewards: **$8,625**.
- Review work: **575 hours**, **$14,375**, plus **$100** reviewer training.
- Conservative platform fees on all rewards: **$9,899.97**.
- Total with 20% contingency, before VAT: **$39,599.96**.
- With illustrative 20% VAT on platform fees and contingency: **$41,975.95**.

**Do not approve or commission this full amount on the strength of the pilot proposal.** First measure actual review effort, recruitment yield, support and source independence. Internal/volunteer review can reduce cash expenditure, but not erase the required work. Volunteer contributors must use a separate consenting route; unpaid recruitment on Prolific is not allowed. If the cost is unacceptable, explicitly reconsider the evidence target, collection strategy or supported claims—not fake independence or silently weaken the false-positive guarantee.

These budgets do not establish representative X prevalence, fill every language/length cell, or guarantee detector success. The current policy floors are engineering safeguards, not proof this is the statistically optimal sample design.

## 3. Participant information and consent — draft only

**Do not present this draft to participants yet.** Complete the controller/contact/jurisdiction/legal-basis fields, get appropriate privacy/legal/ethics review, approve the exact copyright/derived-model permissions, and implement/test every stated protection before launch. No institutional/IRB approval is claimed.

### Information to provide before consent

> **Study:** How people and writing tools produce short online messages.
>
> **Who is responsible:** [CONTROLLER LEGAL NAME], [STUDY CONTACT / PLATFORM MESSAGING CONTACT], [JURISDICTION AND APPLICABLE LEGAL BASIS].
>
> We are developing and evaluating software that estimates whether text contains substantively AI-generated or rewritten wording. We want to understand when these methods fail, including false accusations of human writing. Your writing is not being tested for honesty, quality or political views.
>
> You will write new short messages in a dedicated editor and complete clearly identified assisted-writing tasks. Please use invented/non-sensitive situations and no identifying information about yourself or anyone else. Do not paste private conversations, confidential work or someone else's writing.
>
> With your permission, we will record the text you enter **inside the task editor**, revisions including text you later delete there, task-event times, assigned instructions, declared tool use, final texts and consent/completion records. We will not record typing elsewhere on your computer, your browsing history, passwords, clipboard contents outside the task, camera, microphone or screen. The final implementation must actually match this description.
>
> Your Prolific ID is needed for payment, duplicate-participation checks and withdrawal. It will be kept in a restricted registry linked to a pseudonymous study ID, not in model inputs or reviewer packets. Transport necessarily involves network metadata; the collector/proxy must not retain IP/User-Agent/query logs for analytics or data labeling.
>
> Authorized study staff and two independent process reviewers can inspect pseudonymized task records. With separate, explicit permission below, we will create model-generated/revised variants of your originals on controlled machines and fit/evaluate text-detection models. This is not permission to train a general-purpose text generator on your writing.
>
> Proposed use is private study and development of the X Slop Detector, including its detector/combiner models for that application. You keep copyright. The final permission must state a non-exclusive, appropriately scoped right to use the original contributions and agreed derivatives for that purpose, including any intended commercial/product use. Public raw-text release, general dataset redistribution and third-party hosted processing are **not included**.
>
> **Proposed retention, awaiting approval:** process logs and text up to 180 days after the final collection session; identity/payment linkage up to 90 days after final payment or longer only where an applicable financial/legal obligation requires it; aggregate nonidentifying metrics may be retained. Backups must expire within 30 days of deletion. Longer retention or a new purpose requires an approved lawful basis and updated information/permission as applicable.
>
> You may stop before submission. Contact us through the stated study channel with your study/Prolific ID to request withdrawal or deletion. We propose a 30-day period after your session before first model fitting, so withdrawal can remove the linked block before fitting. That operational window does not extinguish applicable privacy rights afterward. Deleting source records is not the same as automatically removing their influence from a fitted model; the controller must explain the real remediation process and legal obligations, not promise magical unlearning.
>
> Expected writing time is 20 minutes, with a $5 reward under this proposal. Actual pay/time and partial-completion/technical-failure handling must match the approved platform study. Choosing not to consent returns you through the platform's non-consent route; it does not permit keeping your task data.

### Separate affirmative actions to record

No prechecked boxes, names/signatures or outside contact details:

1. I am at least 18, have read the information, and consent to this task-scoped collection and stated study use.
2. I permit the specified model-generated/revised variants and detector/combiner development from my original contributions under the approved scoped permission.
3. I understand that raw writing/process data will not be publicly released or sent to outside model providers under this consent.

Record exact information/consent version and hash, choices, timestamp and private participant linkage. A refusal must not proceed or be quietly converted into consent. The controller/legal reviewer must decide whether derivative permission is a condition of this particular task or whether a separate human-only route is offered; do not silently bundle unrelated purposes.

## 4. Process-review rubric

Recruit/train two distinct human reviewers, blinded to detector scores and later performance. Review a contributor/source block so related outputs are coherent, but enter a separate per-record decision referencing all artifacts required by intake.

1. **Permission/scope:** correct consent version, permitted study/derivative use, no apparent identifying or third-party content. Escalate rights/privacy issues to the controller.
2. **Workflow evidence:** exact editor/task record, original/final hashes and declarations; model/config/prompt/raw-output records where applicable. Do not infer “human” from casual language or “AI” from polished language.
3. **Target mapping:** unaided/mechanical-only/ideas-only negative; substantive generated/rewritten/translated or retained AI wording positive; missing or genuinely ambiguous evidence unknown.
4. **Consistency:** unchanged generated outputs must match final bytes; edited outputs must use the edited workflow and retain the edit record. Original short posts are not cropped long passages.
5. **Lineage:** preserve shared authors, source prompts, events, duplicates, machine drafts and edits. Flag cross-slot connections rather than renaming or moving them to improve results.
6. **Independence:** each reviewer records their decision before seeing the other's. Disagreement remains unknown unless an auditable reconciliation establishes a decision; never use a detector/LLM judge as the tiebreaker.

Paste events, focus changes or detector scores are not proof of misconduct. Keep benchmark exclusion separate from participant payment; follow the platform's fair-rejection rules and pay for legitimate work even if its provenance cannot be used as a binary label.

Report review minutes, disagreements, unknowns, consent/lineage failures, class/length coverage and independent group yield. Measure rather than assume the budgeted ten minutes per reviewer/block.

## 5. Collection/hosting/security work before commissioning

The current private `slop-detection.dimensionlab.net` endpoint cannot serve public Prolific contributors as-is. **Do not make the GPU inference service public to solve this.**

Required separate collection interface:

- Publicly reachable, approved HTTPS **collection-only** endpoint, isolated from inference/admin/model controls and secrets. Hosting/domain/account/access choices require approval.
- Consent-first participant flow, scoped editor history only, no analytics, no unnecessary IP/device/query logging, explicit tool declarations and non-consent/withdrawal/completion paths.
- Restricted Prolific-ID/payment/withdrawal registry; reviewers get pseudonyms and task/process records only. Never put raw IDs in a public dataset, collection-slot plan or detector request.
- Encrypted transport and approved encrypted-at-rest storage/backup policy, access controls, deletion/withdrawal execution and breach-response contact. Existing private intake's 0700 directory mode alone is not all of this.
- Server-side study/task assignment and submit-once checks, provenance exports compatible with intake, hashes/versions, bounded input, retry/idempotency and tested recoverability. A browser history log is evidence to audit, not tamper-proof proof of human authorship.
- Validate payment completion URLs/codes without publishing them in source; retain participant IDs only after informed consent in the controlled registry.
- Run technical rehearsal without outside participants, then the paid collection-method pilot. Do not silently turn the pilot into a final detector evaluation.

Platform basis: [consent](https://researcher-help.prolific.com/en/articles/445265-getting-consent), [ID/data security](https://researcher-help.prolific.com/en/articles/445263-prolific-ids-data-collection-and-security), [external study collection](https://researcher-help.prolific.com/en/articles/445127-data-collection), [PII restrictions](https://researcher-help.prolific.com/en/articles/445117-can-i-ask-participants-for-their-personal-information-identifiers), [unsuitable studies](https://researcher-help.prolific.com/en/articles/445105-are-there-types-of-studies-that-aren-t-suitable-for-prolific). Access/approval for this exact study has not been obtained.

## 6. Generate the private preparation pack

```sh
.venv/bin/python -m detector_eval.study \
  --output .cache/evaluation/contributor-study-proposal-v1
```

This writes draft `plan.json`, `budget.json`, `pilot-allocation.json`, `main-allocation.json` and `launch-blockers.json` into a new 0700 directory. Existing output is never overwritten. Collection slots are **not recruited people**. Main-family choice and controller/quote/hosting/consent/spend approval fields deliberately remain unresolved.

For a later **main** import, after the actual generator-family plan and slots are frozen and consented authors are mapped:

```sh
.venv-evaluation/bin/python -m detector_eval.intake import \
  --bundle PRIVATE_BUNDLE.json --artifacts PRIVATE_ARTIFACT_DIRECTORY \
  --output .cache/evaluation/NEW_STUDY_DIRECTORY \
  --reserved-family ACTUAL_PREREGISTERED_FAMILY \
  --allocation PRIVATE_MAIN_ALLOCATION.json \
  --author-slots PRIVATE_AUTHOR_TO_SLOT_MAP.json
```

The author-slot map contains **study pseudonyms, not Prolific IDs**. Author/root/source/duplicate grouping is recomputed; cross-partition links fail closed. Allocation/author-map fingerprints enter the split manifest. A slot assignment is an auditable operator record, not cryptographic proof it was preregistered.

A collection-pilot import can use its development-only allocation with reserved-family sentinel `not-applicable-collection-pilot`; all adequacy requirements remain active, so it exits inadequate rather than authorizing calibration or a final test. The older equal-fold route remains for historical/supplementary exploration, not the proposed unequal-quota main collection.

## 7. Exact decisions still needed

1. Approve or revise the **$1,000 pilot-only cap**, $5/20-minute writing reward and conservative paid-review assumptions. Actual account quote/tax must fit; main funding remains unapproved.
2. Supply the controller's legal identity, jurisdiction/legal-basis review and study contact, then approve the final consent/permissions/retention/withdrawal terms. Do not infer these from a chat handle.
3. Approve a recruitment account and separate public collection hosting plan before account actions, external terms, recruitment or deployment. Never paste credentials into this thread or commit them.

After those decisions, the next implementation is the consent-first collector and payment/withdrawal/export rehearsal. Only after that should the pilot be commissioned. General agreement to pursue a contributor study has not been treated as a blank cheque.

## Verification

The private preparation CLI ran and produced the five draft files with `may_launch: false`; no participant/payment record was created. Tests cover exact budget arithmetic, missing/underpaid budgets, unequal quotas, development-only pilot assignment, reserved-family isolation, shared-source conflicts, private output/no overwrite, and an actual synthetic preassigned-intake CLI import that remains inadequate rather than consuming a holdout.

Full local checks: **108 Python tests discovered; 104 passed / four optional inference skips** with evaluation dependencies; **97 passed / eleven optional skips** in the lightweight environment. **30 Node client tests passed.** Wheel construction/source-content and documentation checks also passed. These are software checks, not actual people, platform approval, an ethics/legal review, production collector testing, or accuracy evidence. No new tests were run on the GPU host.
