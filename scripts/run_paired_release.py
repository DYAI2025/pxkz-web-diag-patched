#!/usr/bin/env python3
"""Run the installed Pixelkiez Website Diagnosis -> Voice Architect v1.3 paired release proof."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(step_id: str, argv: list[str], cwd: Path) -> dict[str, Any]:
    print(f"RUN {step_id}", file=sys.stderr, flush=True)
    try:
        proc = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired as exc:
        print(f"TIMEOUT {step_id}", file=sys.stderr, flush=True)
        return {"id":step_id,"status":"FAIL","exit_code":124,"stdout_sha256":sha256_bytes((exc.stdout or "").encode("utf-8") if isinstance(exc.stdout,str) else (exc.stdout or b"")),"stderr_sha256":sha256_bytes((exc.stderr or "").encode("utf-8") if isinstance(exc.stderr,str) else (exc.stderr or b"")),"stderr_tail":"SUBPROCESS_TIMEOUT_60S"}
    result = {
        "id": step_id,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "exit_code": proc.returncode,
        "stdout_sha256": sha256_bytes(proc.stdout.encode("utf-8")),
        "stderr_sha256": sha256_bytes(proc.stderr.encode("utf-8")),
    }
    if proc.returncode != 0:
        result["stderr_tail"] = proc.stderr[-1200:]
        result["stdout_tail"] = proc.stdout[-1200:]
    print(f"DONE {step_id} {result['status']}", file=sys.stderr, flush=True)
    return result


def write_report(report: dict[str, Any], website: Path, voice: Path) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    for root in (website, voice):
        (root / "reports").mkdir(parents=True, exist_ok=True)
        (root / "reports/paired-release-report.json").write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--consumer-skill-dir", required=True)
    ap.add_argument("--reuse-current-harness", action="store_true", help="Reuse only an existing complete 27/27 PASS harness report; still validate its contents.")
    args = ap.parse_args()
    website = Path(__file__).resolve().parents[1]
    voice = Path(args.consumer_skill_dir).resolve()
    py = sys.executable
    steps: list[dict[str, Any]] = []
    provider_e2e = "NOT_RUN"
    truth_e2e = "NOT_RUN"
    try:
        wp = website / "contracts/pixelkiez-elevenlabs-batch-contract-v1.3.json"
        vp = voice / "contracts/pixelkiez-elevenlabs-batch-contract-v1.3.json"
        wc, vc = json.loads(wp.read_text(encoding="utf-8")), json.loads(vp.read_text(encoding="utf-8"))
        wd, vd = sha256_file(wp), sha256_file(vp)
        if wp.read_bytes() != vp.read_bytes():
            raise ValueError(f"producer/consumer contract bytes differ: {wd} != {vd}")
        if wc.get("version") != "1.3.0" or wc.get("field_count") != 96 or wc.get("custom_dynamic_variable_count") != 95:
            raise ValueError("producer v1.3 metadata invalid")
        if vc.get("version") != wc.get("version") or vc.get("field_count") != 96:
            raise ValueError("consumer v1.3 metadata invalid")

        command_specs = [
            ("website_contract", [py, str(website / "scripts/validate_batch_contract.py"), str(website)], website),
            ("website_truth", [py, str(website / "scripts/run_truth_discipline_evals.py"), str(website)], website),
            ("website_batch_evals", [py, str(website / "scripts/run_batch_contract_evals.py"), str(website)], website),
            ("cross_skill_contract", [py, str(website / "scripts/validate_cross_skill_batch_contract.py"), str(voice)], website),
            ("voice_contract_package", [py, str(voice / "scripts/validate_batch_contract_package.py"), str(voice)], voice),
            ("voice_schemas", [py, str(voice / "scripts/validate_schemas.py"), str(voice)], voice),
            ("voice_evals", [py, str(voice / "scripts/validate_evals.py"), str(voice)], voice),
        ]
        for step_id, cmd, cwd in command_specs:
            result = run(step_id, cmd, cwd); steps.append(result)
            if result["status"] != "PASS":
                raise RuntimeError(f"{step_id} failed")

        with tempfile.TemporaryDirectory(prefix="pxk-paired-v13-") as td:
            temp = Path(td)
            scored = temp / "scored.json"
            packet = temp / "website-audit-packet.json"
            result = run("score_fixture", [py, str(website / "scripts/compute_score.py"), str(website / "evals/fixtures/synthetic-report.json"), str(scored)], website); steps.append(result)
            if result["status"] != "PASS": raise RuntimeError("score fixture failed")
            result = run("build_provider_packet", [py, str(website / "scripts/build_website_audit_packet.py"), str(scored), str(packet)], website); steps.append(result)
            if result["status"] != "PASS": raise RuntimeError("provider packet build failed")
            pdata = json.loads(packet.read_text(encoding="utf-8"))
            cfg = json.loads((voice / "examples/agent-build-config.example.json").read_text(encoding="utf-8"))
            cfg["prospect"]["company"] = pdata["company"]
            cfg["prospect"]["website"] = pdata["website"]
            cfg_path = temp / "provider-config.json"
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            compiled = temp / "provider-compiled"
            for step_id, cmd in [
                ("voice_validate_provider_packet", [py, str(voice / "scripts/validate_audit_packet.py"), str(packet)]),
                ("voice_compile_provider_packet", [py, str(voice / "scripts/compile_agent_package.py"), "--config", str(cfg_path), "--industry", str(voice / "examples/industry-context.example.json"), "--audit", str(packet), "--out", str(compiled)]),
                ("voice_validate_provider_compile", [py, str(voice / "scripts/validate_agent_package.py"), str(compiled)]),
            ]:
                result=run(step_id,cmd,voice); steps.append(result)
                if result["status"]!="PASS": raise RuntimeError(f"{step_id} failed")
            dyn=json.loads((compiled/"dynamic-variables.json").read_text(encoding="utf-8"))
            if dyn["contract"]["sha256"] != wd or dyn["contract"]["field_count"] != 96 or dyn["contract"]["custom_dynamic_variable_count"] != 95:
                raise RuntimeError("provider-neutral compile did not bind exact v1.3 contract")
            provider_e2e="PASS"

            attack_packet=temp/"truth-attack-packet.json"
            result=run("build_truth_attack_packet",[py,str(website/"scripts/build_website_audit_packet.py"),str(website/"evals/fixtures/truth-discipline-inferred-risk.json"),str(attack_packet)],website); steps.append(result)
            if result["status"]!="PASS": raise RuntimeError("truth attack packet build failed")
            adata=json.loads(attack_packet.read_text(encoding="utf-8"))
            acfg=dict(cfg); acfg["prospect"]=dict(cfg["prospect"]); acfg["prospect"]["company"]=adata["company"]; acfg["prospect"]["website"]=adata["website"]
            acfg_path=temp/"truth-config.json"; acfg_path.write_text(json.dumps(acfg,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            acomp=temp/"truth-compiled"
            for step_id,cmd in [
                ("voice_validate_truth_packet",[py,str(voice/"scripts/validate_audit_packet.py"),str(attack_packet)]),
                ("voice_compile_truth_packet",[py,str(voice/"scripts/compile_agent_package.py"),"--config",str(acfg_path),"--industry",str(voice/"examples/industry-context.example.json"),"--audit",str(attack_packet),"--out",str(acomp)]),
            ]:
                result=run(step_id,cmd,voice); steps.append(result)
                if result["status"]!="PASS": raise RuntimeError(f"{step_id} failed")
            runtime=json.loads((acomp/"audit-runtime-packet.json").read_text(encoding="utf-8"))
            adyn=json.loads((acomp/"dynamic-variables.json").read_text(encoding="utf-8"))
            if any(h.get("evidence_class")=="VERIFIED_FACT" for h in runtime.get("selected_hooks",[])):
                raise RuntimeError("truth attack upgraded to VERIFIED_FACT in consumer")
            if adyn.get("dynamic_variables_template",{}).get("verified_finding") != "Kein verifizierter Befund für das Gespräch freigegeben.":
                raise RuntimeError("truth attack leaked into verified_finding")
            truth_e2e="PASS"

        harness_path=voice/"reports/release-harness-eval-results.json"
        if args.reuse_current_harness:
            if not harness_path.exists():
                raise RuntimeError("requested harness reuse but report is missing")
            harness=json.loads(harness_path.read_text(encoding="utf-8"))
            steps.append({"id":"voice_release_harness","status":"PASS" if harness.get("status")=="PASS" and harness.get("failed")==0 and harness.get("passed",0)>=27 else "FAIL","exit_code":0,"mode":"REUSED_COMPLETE_REPORT"})
        else:
            harness_step=run("voice_release_harness",[py,str(voice/"scripts/run_release_harness_evals.py"),str(voice)],voice); steps.append(harness_step)
            if harness_step["status"]!="PASS": raise RuntimeError("voice release harness failed")
            harness=json.loads(harness_path.read_text(encoding="utf-8"))
        if harness.get("status")!="PASS" or harness.get("failed")!=0 or harness.get("passed",0)<27:
            raise RuntimeError("voice release harness report incomplete")

        report={
            "status":"PASS",
            "paired_release_version":"1.0",
            "website_skill_dir":str(website),
            "consumer_skill_dir":str(voice),
            "website_skill_side_status":"PASS",
            "voice_architect_side_status":"PASS",
            "contract":{"version":"1.3.0","sha256":wd,"field_count":96,"custom_dynamic_variable_count":95},
            "provider_neutral_packet_e2e":provider_e2e,
            "truth_attack_e2e":truth_e2e,
            "voice_release_harness":{"status":"PASS","passed":harness.get("passed"),"failed":harness.get("failed")},
            "live_calling":"NOT_AUTHORIZED_BY_THIS_PROOF",
            "does_not_prove":["ElevenLabs dashboard upload success","legal authorization for a real campaign","live telephony behavior or conversion outcome"],
            "steps":steps,
        }
        write_report(report,website,voice)
        print(json.dumps({k:v for k,v in report.items() if k!="steps"},ensure_ascii=False))
        return 0
    except Exception as exc:
        report={
            "status":"FAIL","paired_release_version":"1.0","website_skill_dir":str(website),"consumer_skill_dir":str(voice),
            "website_skill_side_status":"FAIL","voice_architect_side_status":"FAIL","provider_neutral_packet_e2e":provider_e2e,"truth_attack_e2e":truth_e2e,
            "error":str(exc),"steps":steps,
        }
        write_report(report,website,voice)
        print(f"FAIL: {exc}",file=sys.stderr)
        return 1

if __name__=="__main__": raise SystemExit(main())
