"""Resumable, bounded evidence collection. No Load/Unload or service changes."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import time
import urllib.parse

import httpx

from detector_server.contracts import AnalyzeResponse, Capabilities, StatusResponse, validate_check
from .data import Corpus, Evidence, EvidenceSet, ROSTER, digest, read_json, write_json
from .adequacy import InadequateStudy, audit


def deployment_runtime(host):
    """Audit the deployed code/library context without importing model libraries."""
    code = """
import hashlib, importlib.metadata as m, importlib.util, json, pathlib, subprocess, sys
p=pathlib.Path(importlib.util.find_spec('detector_server').origin).parent
h=hashlib.sha256()
for f in sorted(p.rglob('*.py')):
 h.update(str(f.relative_to(p)).encode()+b'\\0'+f.read_bytes())
r={n:m.version(n) for n in ('torch','transformers','safetensors','tokenizers','numpy')}
r['python']=sys.version.split()[0]
r['server_source_sha256']=h.hexdigest()
driver=subprocess.run(['nvidia-smi','--query-gpu=driver_version','--format=csv,noheader'],capture_output=True,text=True)
r['driver']=','.join(sorted(set(driver.stdout.split()))) if driver.returncode==0 else 'not_observed'
print(json.dumps(r,sort_keys=True))
"""
    command = "sudo -n /home/xslop/venv/bin/python -I -c " + shlex.quote(code)
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host, command],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True)
    parser.add_argument("--origin", default="https://slop-detection.dimensionlab.net")
    parser.add_argument("--ssh-host", default="gpu")
    args = parser.parse_args()
    url = urllib.parse.urlsplit(args.origin)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.path or url.query or url.fragment:
        parser.error("use a trusted HTTPS origin")
    study = Path(args.study)
    corpus = Corpus.model_validate(read_json(study / "corpus.json"))
    preflight = audit(
        corpus, read_json(study / "splits.json"),
        [e.language == "en" and len(e.text) <= 10000 for e in corpus.examples],
        basis="precollection_upper_bound_no_native_evidence",
    )
    if not preflight["passed"]:
        raise InadequateStudy(preflight)
    fingerprint = digest(corpus.model_dump(mode="json"))
    token = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", args.ssh_host, "sudo", "-n", "cat",
         "/etc/x-slop-detector/api-token"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    with httpx.Client(
        base_url=args.origin, headers={"Authorization": "Bearer " + token},
        timeout=httpx.Timeout(120, connect=10), follow_redirects=False,
    ) as client:
        def request(path, body=None):
            for attempt in range(7):
                response = client.get(path) if body is None else client.post(path, json=body)
                if response.status_code == 409:
                    error = response.json().get("error", {})
                    if error.get("code") == "manually_paused":
                        raise RuntimeError("operator_manually_paused_service_no_automatic_resume")
                    if error.get("code") == "busy" and attempt < 6:
                        time.sleep(min(2 ** attempt, 8))
                        continue
                if response.status_code != 200:
                    raise RuntimeError(f"collection_http_{response.status_code}")
                return response.json()

        status = StatusResponse.model_validate(request("/v2/status"))
        if status.suite.paused:
            raise SystemExit("Collection blocked: server manually paused. Press Load or ask the operator to resume; this collector never overrides pause.")
        cap = Capabilities.model_validate(request("/v2/capabilities"))
        catalog = {s.checker.id: s for s in cap.checkers}
        specs = [catalog[id] for id in ROSTER]
        if not all(any(c.checker_id == id and c.required for c in status.suite.components) for id in ROSTER):
            raise ValueError("wrong_selected_suite")
        metadata = {
            "schema_version": "1", "corpus_sha256": fingerprint,
            "configuration_id": status.suite.configuration_id,
            "extraction_version": "own-post-text-v1",
            "runtime": deployment_runtime(args.ssh_host),
            "specs": [s.model_dump(mode="json") for s in specs],
        }
        meta_path = study / "evidence-metadata.json"
        if meta_path.exists():
            if read_json(meta_path) != metadata:
                raise ValueError("collection_configuration_changed_cannot_resume")
        else:
            write_json(meta_path, metadata)
        journal = study / "evidence.jsonl"
        rows = {}
        if journal.exists():
            for line in journal.read_text().splitlines():
                row = Evidence.model_validate_json(line)
                if row.example_id in rows:
                    raise ValueError("duplicate_journal_row")
                rows[row.example_id] = row
        valid_ids = {e.id for e in corpus.examples}
        if not set(rows) <= valid_ids:
            raise ValueError("journal_contains_foreign_examples")
        def save(row):
            if row.example_id in rows:
                raise ValueError("duplicate_collected_result")
            with journal.open("a") as f:
                f.write(row.model_dump_json() + "\n")
                f.flush()
            rows[row.example_id] = row

        def batch(examples):
            if not examples:
                return
            body = {
                "schema_version": "2", "extraction_version": metadata["extraction_version"],
                "posts": [{"id": e.id, "text": e.text} for e in examples],
            }
            result = AnalyzeResponse.model_validate(request("/v2/analyze", body))
            if (result.configuration_id != metadata["configuration_id"] or
                    result.extraction_version != metadata["extraction_version"] or
                    [r.id for r in result.results] != [e.id for e in examples]):
                raise ValueError("collection_response_identity_mismatch")
            expected = {c.checker_id for c in status.suite.components}
            for e, r in zip(examples, result.results):
                if {c.checker.id for c in r.checks} != expected:
                    raise ValueError("incomplete_api_response")
                for check in r.checks:
                    validate_check(check, catalog[check.checker.id], len(e.text))
                save(Evidence(
                    example_id=e.id, text_sha256=e.text_sha256,
                    configuration_id=result.configuration_id,
                    extraction_version=result.extraction_version, checks=r.checks,
                ))
            print(json.dumps({"collected": len(rows), "total": len(corpus.examples)}), flush=True)

        pending = []
        byte_count = 512
        for example in corpus.examples:
            if example.id in rows:
                continue
            if len(example.text) > 10000:
                save(Evidence(
                    example_id=example.id, text_sha256=example.text_sha256,
                    configuration_id=metadata["configuration_id"],
                    extraction_version=metadata["extraction_version"], checks=[],
                    collection_reason="input_character_limit",
                ))
                continue
            size = len(json.dumps({"id": example.id, "text": example.text}).encode()) + 64
            if pending and (len(pending) == 4 or byte_count + size > 120000):
                batch(pending); pending = []; byte_count = 512
            pending.append(example); byte_count += size
        batch(pending)
        if deployment_runtime(args.ssh_host) != metadata["runtime"]:
            raise ValueError("runtime_changed_during_collection")
        evidence = EvidenceSet(**metadata, rows=[rows[e.id] for e in corpus.examples])
        from .data import bind_evidence
        bind_evidence(corpus, evidence)
        write_json(study / "evidence.json", evidence.model_dump(mode="json"))
        print(json.dumps({"evidence_complete": len(evidence.rows), "configuration": evidence.configuration_id}))


if __name__ == "__main__":
    main()
