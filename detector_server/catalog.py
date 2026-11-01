"""Reviewed validation configurations, not an inventory of integrated adapters."""

from .contracts import CheckerRef, CheckerSpec


def classifier(id, artifact, revision, license, role="candidate"):
    return CheckerSpec(
        checker=CheckerRef(id=id, configuration_id=f"{id}-raw-fp32-v1", artifact_revision=revision),
        kind="classifier", role=role, artifact_id=artifact, license=license,
        precision="float32", ai_label_index=1, max_tokens=512, preprocessing="raw_text",
    )


TABULARIS = classifier(
    "tabularis", "tabularisai/ai-text-detection",
    "4bf4a146a66df346e5b54e4b5ebda3fee1a19a86", "MIT",
)
E5 = classifier(
    "e5", "MayZhou/e5-small-lora-ai-generated-detector",
    "483fc4969592dc20e00e5130e7187b5dd25dbcc7", "MIT",
)
FAKESPOT = classifier(
    "fakespot", "fakespot-ai/roberta-base-ai-text-detection-v1",
    "f9cdb14d1f8b105f597d80fa7b56f20c6ea0e9db", "Apache-2.0",
)
TMR = classifier(
    "tmr", "Oxidane/tmr-ai-text-detector",
    "0ceddea903015ef99cbaa040a4d8a216aed9c683", "MIT", role="challenger",
)
NEO = CheckerSpec(
    checker=CheckerRef(
        id="fast_detect_gpt", configuration_id="neo-same-model-raw-fp16-512-v1",
        artifact_revision="e24fa291132763e59f4a5422741b424fb5d59056",
    ),
    kind="statistical", role="candidate", artifact_id="EleutherAI/gpt-neo-2.7B",
    license="MIT", method_revision="971b05202bac2bb504d60c0ac0812fea7a8f7c82",
    precision="float16", max_tokens=512, preprocessing="raw_text",
)

INITIAL_ROSTER = (TABULARIS, E5, FAKESPOT, NEO)
CHECKER_CATALOG = (*INITIAL_ROSTER, TMR)
