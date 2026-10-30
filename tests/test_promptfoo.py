"""Offline unit and mutation tests for the Promptfoo export adapter."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from evalrepro.adapters import promptfoo_source
from evalrepro.compare import Verdict, compare_manifest_data
from evalrepro.errors import AdapterError
from evalrepro.manifest import build_manifest


def _base_result() -> dict[str, Any]:
    return {
        "id": "res-uuid-1",
        "description": "Fallback result description",
        "promptIdx": 0,
        "testIdx": 0,
        "promptId": "prompt-sha-1",
        "prompt": {
            "id": "prompt-sha-1",
            "raw": "Translate Hello to Spanish",
            "template": "Translate {{word}} to {{lang}}",
            "display": "Translate prompt",
            "label": "translator",
            "config": {"temperature": 0.2},
            "customPromptField": "inert",
        },
        "provider": {"id": "openai:gpt-4o", "label": "GPT-4o"},
        "vars": {"word": "Hello", "lang": "Spanish"},
        "testCase": {
            "description": "Greeting translation test",
            "vars": {"word": "Hello", "lang": "Spanish", "default_var": "d1"},
            "assert": [
                {"type": "is-json"},
                {
                    "type": "contains",
                    "value": "Hola",
                    "threshold": 0.8,
                    "weight": 1.0,
                    "metric": "accuracy",
                    "transform": "output.trim()",
                    "contextTransform": "context.trim()",
                    "config": {"caseSensitive": False},
                    "extraAssertField": "kept",
                },
                {
                    "type": "assert-set",
                    "threshold": 0.9,
                    "weight": 2.0,
                    "metric": "bundle",
                    "config": {"strict": True},
                    "extraSetField": "kept",
                    "assert": [
                        {
                            "type": "llm-rubric",
                            "value": "Polite Spanish greeting",
                            "provider": "openai:gpt-4o-mini",
                            "rubricPrompt": "Grade politeness",
                        }
                    ],
                },
            ],
            "assertScoringFunction": "file://score.py:score_fn",
            "options": {
                "prefix": "default:",
                "suffix": ":end",
                "postprocess": "output.strip()",
                "transform": "output.lower()",
                "transformVars": "vars",
                "storeOutputAs": "saved_greeting",
                "rubricPrompt": "default rubric",
                "provider": "openai:gpt-4o-mini",
                "factuality": {"subset": 1.0},
                "disableVarExpansion": False,
                "disableConversationVar": True,
                "disableDefaultAsserts": False,
                "runSerially": True,
                "repeat": 1,
                "customOption": "opt-val",
            },
            "threshold": 0.75,
            "providers": ["openai:gpt-4o"],
            "prompts": ["translator"],
            "metadata": {"category": "i18n"},
            "customTestField": "inert-test-extra",
        },
        "response": {"output": "Hola", "cached": False},
        "error": None,
        "failureReason": 0,
        "success": True,
        "score": 1.0,
        "latencyMs": 320,
        "gradingResult": {"pass": True, "score": 1.0, "reason": "Matched"},
        "namedScores": {"accuracy": 1.0},
        "cost": 0.0012,
        "metadata": {"traceSpan": "abc"},
        "tokenUsage": {"total": 20, "prompt": 12, "completion": 8},
        "evaluationId": "eval-run-123",
        "traceId": "trace-xyz-1",
    }


def _v2_payload() -> dict[str, Any]:
    return {
        "evalId": "eval-v2-secret-id",
        "shareableUrl": "https://app.promptfoo.dev/eval/eval-v2-secret-id",
        "vars": ["word", "lang"],
        "runtimeOptions": {"repeat": 1, "filterRange": "0:10", "isRedteam": False},
        "traces": [{"traceId": "t1", "spans": []}],
        "blobAssets": [],
        "results": {
            "version": 2,
            "timestamp": "2026-08-10T12:00:00.000Z",
            "stats": {"successes": 1, "failures": 0, "errors": 0},
            "table": {
                "head": {
                    "vars": ["word", "lang"],
                    "prompts": [
                        {
                            "id": "prompt-sha-1",
                            "raw": "Translate {{word}} to {{lang}}",
                            "label": "translator",
                            "provider": "openai:gpt-4o",
                            "config": {"temperature": 0.2},
                            "extraPromptMeta": "v",
                        }
                    ],
                },
                "body": [],
            },
            "results": [_base_result()],
        },
        "config": {
            "description": "Suite description",
            "tags": {"env": "ci"},
            "providers": [
                {
                    "id": "openai:gpt-4o",
                    "label": "GPT-4o",
                    "config": {"temperature": 0.7, "max_tokens": 128},
                    "prompts": ["translator"],
                    "transform": "provider_transform()",
                    "delay": 10,
                    "env": {"OPENAI_ORGANIZATION": "org-1"},
                    "customProviderField": "p-extra",
                }
            ],
            "defaultTest": {
                "vars": {"default_var": "d1"},
                "assert": [{"type": "is-json"}],
                "options": {"prefix": "default:"},
                "metadata": {"suite_meta": "m1"},
                "defaultExtra": "d-extra",
            },
            "providerPromptMap": {"openai:gpt-4o": ["translator"]},
            "nunjucksFilters": {"upper": "file://filters.js:upper"},
            "env": {"API_HOST": "https://api.example.com"},
            "derivedMetrics": [{"name": "f1", "value": "2 * p * r / (p + r)"}],
            "extensions": ["file://ext.py:hook"],
            "redteam": {"plugins": ["pii"]},
            "scenarios": [{"description": "scen", "config": [], "tests": []}],
            "evaluateOptions": {"repeat": 1, "filterRange": "0:10", "maxConcurrency": 4},
            "commandLineOptions": {
                "promptPrefix": "cli-pre:",
                "promptSuffix": ":cli-suf",
                "verbose": True,
            },
            "unknownSuiteField": "suite-extra",
        },
        "metadata": {
            "promptfooVersion": "0.100.0",
            "nodeVersion": "v22.1.0",
            "platform": "linux",
            "arch": "x64",
            "exportedAt": "2026-08-10T12:05:00.000Z",
            "evaluationCreatedAt": "2026-08-10T12:00:00.000Z",
            "author": "alice@example.com",
        },
    }


def _v3_payload() -> dict[str, Any]:
    payload = copy.deepcopy(_v2_payload())
    payload["evalId"] = "eval-v3-secret-id"
    prompts = payload["results"]["table"]["head"]["prompts"]
    del payload["results"]["table"]
    payload["results"]["version"] = 3
    payload["results"]["prompts"] = prompts
    return payload


def _write_json(path: Path, data: Any) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _manifest_for(
    tmp_path: Path, filename: str, data: dict[str, Any], name: str = "suite"
) -> dict[str, Any]:
    file_path = _write_json(tmp_path / filename, data)
    return build_manifest(promptfoo_source(file_path, name=name))


def test_v2_and_v3_parity_and_hash_only_privacy(tmp_path: Path) -> None:
    v2_path = _write_json(tmp_path / "secret_v2_path.json", _v2_payload())
    v3_path = _write_json(tmp_path / "secret_v3_path.json", _v3_payload())

    # Record-level exact-once assertion for defaultTest
    source = promptfoo_source(v2_path, name="regression-suite")
    assert source.declared_count == 1
    is_json_asserts = [
        a for a in source.records[0]["target"]["assertions"] if a["type"] == "is-json"
    ]
    assert len(is_json_asserts) == 1, "Default is-json assertion must be emitted exactly once."

    m_v2 = build_manifest(source)
    m_v3 = build_manifest(promptfoo_source(v3_path, name="regression-suite"))

    comparison = compare_manifest_data(m_v2, m_v3)
    assert comparison.verdict is Verdict.REPRODUCIBLE

    dumped = json.dumps(m_v2)
    for sensitive in (
        "Translate Hello to Spanish",
        "Hola",
        "secret_v2_path.json",
        "eval-v2-secret-id",
        "alice@example.com",
        "https://app.promptfoo.dev",
    ):
        assert sensitive not in dumped

    no_preview = build_manifest(
        promptfoo_source(v2_path, name="regression-suite"),
        include_id_preview=False,
    )
    assert no_preview["samples"]["id_preview"] == {"first": [], "last": []}
    assert no_preview["samples"]["ordered_hashes"] == m_v2["samples"]["ordered_hashes"]


def test_non_semantic_outcome_runtime_and_provenance_invariance(tmp_path: Path) -> None:
    baseline = _v2_payload()
    candidate = copy.deepcopy(baseline)
    candidate["evalId"] = None
    candidate["shareableUrl"] = None
    candidate["traces"] = []
    candidate["results"]["timestamp"] = "2029-01-01T00:00:00.000Z"
    candidate["results"]["stats"] = {"successes": 0, "failures": 1, "errors": 1}
    candidate["metadata"] = {
        "promptfooVersion": "0.200.0",
        "nodeVersion": "v24.0.0",
        "platform": "darwin",
        "arch": "arm64",
        "exportedAt": "2029-01-02T00:00:00.000Z",
        "evaluationCreatedAt": "2029-01-01T00:00:00.000Z",
        "author": "bob@example.com",
    }
    res = candidate["results"]["results"][0]
    res["id"] = "different-row-id"
    res["testIdx"] = 99
    res["response"] = {"output": "Completely different LLM output"}
    res["error"] = "Provider timeout"
    res["failureReason"] = 2
    res["success"] = False
    res["score"] = 0.0
    res["latencyMs"] = 99999
    res["gradingResult"] = {"pass": False, "score": 0.0, "reason": "Failed"}
    res["namedScores"] = {"accuracy": 0.0}
    res["cost"] = 99.9
    res["tokenUsage"] = {"total": 999, "prompt": 500, "completion": 499}
    res["evaluationId"] = "other-eval"
    res["traceId"] = "other-trace"

    m_base = _manifest_for(tmp_path, "base.json", baseline)
    m_cand = _manifest_for(tmp_path, "cand.json", candidate)

    assert compare_manifest_data(m_base, m_cand).verdict is Verdict.REPRODUCIBLE


def test_provider_output_is_semantic_definition_input(tmp_path: Path) -> None:
    base = _v3_payload()
    with_provider_output = copy.deepcopy(base)
    with_provider_output["results"]["results"][0]["testCase"]["providerOutput"] = "Canned output A"

    changed_provider_output = copy.deepcopy(with_provider_output)
    changed_provider_output["results"]["results"][0]["testCase"]["providerOutput"] = {
        "structured": "Canned output B"
    }

    changed_response_only = copy.deepcopy(with_provider_output)
    changed_response_only["results"]["results"][0]["response"] = {"output": "Runtime output X"}

    m_base = _manifest_for(tmp_path, "base.json", base)
    m_po_a = _manifest_for(tmp_path, "po_a.json", with_provider_output)
    m_po_b = _manifest_for(tmp_path, "po_b.json", changed_provider_output)
    m_resp = _manifest_for(tmp_path, "resp.json", changed_response_only)

    assert compare_manifest_data(m_base, m_po_a).verdict is Verdict.SEMANTIC_DRIFT
    assert compare_manifest_data(m_po_a, m_po_b).verdict is Verdict.SEMANTIC_DRIFT
    assert compare_manifest_data(m_po_a, m_resp).verdict is Verdict.REPRODUCIBLE


def test_semantic_mutations_produce_semantic_drift(tmp_path: Path) -> None:
    base = _v2_payload()
    m_base = _manifest_for(tmp_path, "base.json", base)

    mutations: list[tuple[str, Any]] = []

    p1 = copy.deepcopy(base)
    p1["results"]["results"][0]["prompt"]["raw"] = "Changed prompt"
    mutations.append(("prompt_raw", p1))

    p2 = copy.deepcopy(base)
    p2["results"]["results"][0]["promptId"] = "prompt-sha-2"
    p2["results"]["results"][0]["prompt"]["id"] = "prompt-sha-2"
    p2["results"]["table"]["head"]["prompts"][0]["id"] = "prompt-sha-2"
    mutations.append(("prompt_id", p2))

    p3 = copy.deepcopy(base)
    p3["results"]["results"][0]["vars"]["lang"] = "French"
    mutations.append(("vars", p3))

    p4 = copy.deepcopy(base)
    p4["config"]["providers"][0]["config"]["temperature"] = 0.9
    mutations.append(("provider_config", p4))

    p5 = copy.deepcopy(base)
    p5["results"]["results"][0]["testCase"]["assert"][0]["value"] = "Bonjour"
    mutations.append(("assertion_val", p5))

    p6 = copy.deepcopy(base)
    p6["results"]["results"][0]["testCase"]["threshold"] = 0.95
    mutations.append(("threshold", p6))

    p7 = copy.deepcopy(base)
    p7["results"]["results"][0]["testCase"]["options"]["transform"] = "output.upper()"
    mutations.append(("transform", p7))

    p8 = copy.deepcopy(base)
    p8["results"]["results"][0]["testCase"]["assertScoringFunction"] = "file://other.py:fn"
    mutations.append(("grader_fn", p8))

    p9 = copy.deepcopy(base)
    p9["results"]["results"][0]["testCase"]["metadata"]["category"] = "changed"
    mutations.append(("test_metadata", p9))

    p10 = copy.deepcopy(base)
    p10["results"]["results"][0]["testCase"]["unknownNewField"] = {"inert": 42}
    mutations.append(("unknown_test_field", p10))

    p11 = copy.deepcopy(base)
    p11["config"]["commandLineOptions"]["promptPrefix"] = "different-prefix:"
    mutations.append(("cli_prefix", p11))

    p12 = copy.deepcopy(base)
    p12["results"]["results"][0]["testCase"]["options"]["disableDefaultAsserts"] = True
    mutations.append(("disable_default_asserts", p12))

    for label, mutated in mutations:
        m_mut = _manifest_for(tmp_path, f"mut_{label}.json", mutated)
        assert compare_manifest_data(m_base, m_mut).verdict is Verdict.SEMANTIC_DRIFT


def test_ordering_multiplicity_coverage_and_scope(tmp_path: Path) -> None:
    row_a = _base_result()
    row_b = copy.deepcopy(row_a)
    row_b["vars"] = {"word": "Goodbye", "lang": "Spanish"}
    row_b["testCase"]["vars"] = {"word": "Goodbye", "lang": "Spanish"}
    row_c = copy.deepcopy(row_a)
    row_c["vars"] = {"word": "Thanks", "lang": "Spanish"}
    row_c["testCase"]["vars"] = {"word": "Thanks", "lang": "Spanish"}

    two_ab = _v3_payload()
    two_ab["results"]["results"] = [row_a, row_b]

    two_ba = _v3_payload()
    two_ba["results"]["results"] = [row_b, row_a]

    two_ac = _v3_payload()
    two_ac["results"]["results"] = [row_a, row_c]

    repeat_aa = _v3_payload()
    repeat_aa["results"]["results"] = [row_a, copy.deepcopy(row_a)]

    repeat_aaa = _v3_payload()
    repeat_aaa["results"]["results"] = [row_a, copy.deepcopy(row_a), copy.deepcopy(row_a)]

    m_ab = _manifest_for(tmp_path, "ab.json", two_ab)
    m_ba = _manifest_for(tmp_path, "ba.json", two_ba)
    m_ac = _manifest_for(tmp_path, "ac.json", two_ac)
    m_aa = _manifest_for(tmp_path, "aa.json", repeat_aa)
    m_aa_copy = _manifest_for(tmp_path, "aa_copy.json", repeat_aa)
    m_aaa = _manifest_for(tmp_path, "aaa.json", repeat_aaa)

    assert compare_manifest_data(m_ab, m_ba).verdict is Verdict.ORDER_DRIFT
    assert compare_manifest_data(m_ab, m_ac).verdict is Verdict.SEMANTIC_DRIFT
    assert compare_manifest_data(m_aa, m_aa_copy).verdict is Verdict.REPRODUCIBLE
    assert len(m_aa["samples"]["ordered_hashes"]) == 2
    assert m_aa["samples"]["ordered_hashes"][0] == m_aa["samples"]["ordered_hashes"][1]
    assert compare_manifest_data(m_aa, m_aaa).verdict is Verdict.COVERAGE_MISMATCH

    ab_path = _write_json(tmp_path / "ab_partial.json", two_ab)
    m_partial = build_manifest(promptfoo_source(ab_path, name="suite"), sample_limit=1)
    assert compare_manifest_data(m_ab, m_partial).verdict is Verdict.COVERAGE_MISMATCH

    m_other_name = _manifest_for(tmp_path, "ab_other.json", two_ab, name="different-suite")
    assert compare_manifest_data(m_ab, m_other_name).verdict is Verdict.SCOPE_MISMATCH


def test_provider_schema_forms_and_resolution(tmp_path: Path) -> None:
    # 1. String provider in config.providers and string result.provider
    p_str = _v3_payload()
    p_str["config"]["providers"] = ["openai:gpt-4o"]
    p_str["results"]["results"][0]["provider"] = "openai:gpt-4o"
    del p_str["results"]["results"][0]["testCase"]["description"]
    m_str = _manifest_for(tmp_path, "p_str.json", p_str)
    assert m_str["coverage"]["processed_count"] == 1

    # 2. Keyed object inside config.providers array + targets alias
    p_keyed = _v3_payload()
    del p_keyed["config"]["providers"]
    p_keyed["config"]["targets"] = [{"openai:gpt-4o": {"config": {"temperature": 0.5}}}]
    p_keyed["config"]["defaultTest"] = "file://default_test.yaml"
    m_keyed = _manifest_for(tmp_path, "p_keyed.json", p_keyed)
    assert m_keyed["coverage"]["processed_count"] == 1

    # 3. Dict mapping in config.providers + single provider object in config.providers
    p_dict_map = _v3_payload()
    p_dict_map["config"]["providers"] = {"openai:gpt-4o": {"config": {"temperature": 0.5}}}
    m_dict_map = _manifest_for(tmp_path, "p_dict_map.json", p_dict_map)
    assert compare_manifest_data(m_keyed, m_dict_map).verdict is Verdict.REPRODUCIBLE

    p_single_obj = _v3_payload()
    p_single_obj["config"]["providers"] = {"id": "openai:gpt-4o", "config": {"temperature": 0.1}}
    p_single_obj["config"][" runtime_extra"] = 1
    p_single_obj["results"]["results"][0]["testCase"]["provider"] = {
        "id": "openai:gpt-4o",
        "config": {"top_p": 0.9},
    }
    m_single_obj = _manifest_for(tmp_path, "p_single_obj.json", p_single_obj)
    assert m_single_obj["coverage"]["processed_count"] == 1

    # 5. Missing config.providers but testCase.provider present + duplicate identical provider defs
    p_dup_identical = _v3_payload()
    entry = {"id": "openai:gpt-4o", "label": "GPT-4o", "config": {"temperature": 0.7}}
    p_dup_identical["config"]["providers"] = [entry, copy.deepcopy(entry)]
    m_dup_identical = _manifest_for(tmp_path, "p_dup.json", p_dup_identical)
    assert m_dup_identical["coverage"]["processed_count"] == 1


def test_validation_and_error_branches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    valid_path = _write_json(tmp_path / "valid.json", _v3_payload())

    with pytest.raises(AdapterError, match="non-empty string"):
        promptfoo_source(valid_path, name="   ")

    with pytest.raises(AdapterError, match="mode='definition'"):
        promptfoo_source(valid_path, name="x", mode="results")

    with pytest.raises(AdapterError, match="does not exist"):
        promptfoo_source(tmp_path / "missing.json", name="x")

    with pytest.raises(AdapterError, match="not a regular file"):
        promptfoo_source(tmp_path, name="x")

    bad_utf8 = tmp_path / "bad_utf8.json"
    bad_utf8.write_bytes(b"\xff\xfe")
    with pytest.raises(AdapterError, match="UTF-8"):
        promptfoo_source(bad_utf8, name="x")

    bad_json = tmp_path / "bad_json.json"
    bad_json.write_text("{unclosed", encoding="utf-8")
    with pytest.raises(AdapterError, match="Invalid JSON"):
        promptfoo_source(bad_json, name="x")

    non_obj = _write_json(tmp_path / "non_obj.json", [1, 2, 3])
    with pytest.raises(AdapterError, match="root must be a JSON object"):
        promptfoo_source(non_obj, name="x")

    nan_file = tmp_path / "nan.json"
    nan_file.write_text(
        '{"results": {"version": 3, "prompts": [], "results": [NaN]}}', encoding="utf-8"
    )
    with pytest.raises(AdapterError, match="non-finite numeric constant"):
        promptfoo_source(nan_file, name="x")

    # Invalid mutations table
    cases: list[tuple[str, Any, str]] = []

    c_top = _v3_payload()
    c_top["extraTop"] = 1
    cases.append(("top_key", c_top, r"\$\.extraTop"))

    c_blob_type = _v3_payload()
    c_blob_type["blobAssets"] = "bad"
    cases.append(("blob_type", c_blob_type, r"\$\.blobAssets: expected a JSON array"))

    c_blob_nonempty = _v3_payload()
    c_blob_nonempty["blobAssets"] = [
        {"hash": "h", "mimeType": "image/png", "sizeBytes": 1, "data": "a"}
    ]
    cases.append(("blob_nonempty", c_blob_nonempty, "rejects non-empty embedded media"))

    c_ver = _v3_payload()
    c_ver["results"]["version"] = 1
    cases.append(("ver_1", c_ver, "unsupported summary version"))

    c_ver_bool = _v3_payload()
    c_ver_bool["results"]["version"] = True
    cases.append(("ver_bool", c_ver_bool, "unsupported summary version"))

    c_sum_extra = _v3_payload()
    c_sum_extra["results"]["table"] = {}
    cases.append(("v3_with_table", c_sum_extra, r"\$\.results\.table: unsupported summary field"))

    c_meta_extra = _v3_payload()
    c_meta_extra["metadata"]["secretKey"] = "x"
    cases.append(("meta_extra", c_meta_extra, r"\$\.metadata\.secretKey"))

    c_both_prov = _v3_payload()
    c_both_prov["config"]["targets"] = ["openai:gpt-4o"]
    cases.append(("both_prov_targets", c_both_prov, "cannot specify both"))

    c_bad_prov_shape = _v3_payload()
    c_bad_prov_shape["config"]["providers"] = 123
    cases.append(("bad_prov_shape", c_bad_prov_shape, r"\$\.config\.providers: unsupported"))

    c_bad_prov_entry = _v3_payload()
    c_bad_prov_entry["config"]["providers"] = [{"a": 1, "b": 2}]
    cases.append(("bad_prov_entry", c_bad_prov_entry, "single-keyed provider map"))

    c_unmatched_prov = _v3_payload()
    c_unmatched_prov["config"]["providers"] = ["anthropic:claude-3"]
    cases.append(("unmatched_prov", c_unmatched_prov, "provider not found"))

    c_ambig_prov = _v3_payload()
    c_ambig_prov["config"]["providers"] = [
        {"id": "openai:gpt-4o", "label": "GPT-4o", "config": {"temperature": 0.1}},
        {"id": "openai:gpt-4o", "label": "GPT-4o", "config": {"temperature": 0.9}},
    ]
    cases.append(("ambig_prov", c_ambig_prov, "ambiguous provider match"))

    c_res_extra = _v3_payload()
    c_res_extra["results"]["results"][0]["unknownResultKey"] = 1
    cases.append(("res_extra", c_res_extra, "unsupported result field"))

    c_neg_idx = _v3_payload()
    c_neg_idx["results"]["results"][0]["promptIdx"] = -1
    cases.append(("neg_idx", c_neg_idx, "non-negative integer"))

    c_empty_str = _v3_payload()
    c_empty_str["results"]["results"][0]["promptId"] = "  "
    cases.append(("empty_prompt_id", c_empty_str, "non-empty string"))

    c_bad_opt_str = _v3_payload()
    c_bad_opt_str["evalId"] = 123
    cases.append(("bad_opt_str", c_bad_opt_str, "expected a string or null"))

    c_bad_num = _v3_payload()
    c_bad_num["results"]["results"][0]["testCase"]["threshold"] = True
    cases.append(("bad_num", c_bad_num, "expected a number or null"))

    c_fn_marker = _v3_payload()
    c_fn_marker["results"]["results"][0]["testCase"]["vars"]["fn"] = "[Function: myCustomFn]"
    cases.append(("fn_marker", c_fn_marker, "opaque serialized function"))

    c_exec_key = _v3_payload()
    c_exec_key["results"]["results"][0]["prompt"]["function"] = "inline"
    cases.append(("exec_key", c_exec_key, "executable definition field"))

    c_bad_po = _v3_payload()
    c_bad_po["results"]["results"][0]["testCase"]["providerOutput"] = 123
    cases.append(("bad_po", c_bad_po, "providerOutput: expected a string or object"))

    c_no_config = _v3_payload()
    del c_no_config["config"]
    cases.append(("no_config", c_no_config, r"\$\.config: missing required top-level"))

    c_null_po = _v3_payload()
    c_null_po["results"]["results"][0]["testCase"]["providerOutput"] = None
    cases.append(("null_po", c_null_po, "providerOutput: expected a string or object"))

    c_bad_repeat = _v3_payload()
    c_bad_repeat["results"]["results"][0]["testCase"]["options"]["repeat"] = "many"
    cases.append(("bad_repeat", c_bad_repeat, "options.repeat: expected a positive integer"))

    c_bad_prompt_idx = _v3_payload()
    c_bad_prompt_idx["results"]["results"][0]["promptIdx"] = 5
    cases.append(("bad_prompt_idx", c_bad_prompt_idx, "promptIdx: index out of bounds"))

    c_bad_prompt_id = _v3_payload()
    c_bad_prompt_id["results"]["results"][0]["promptId"] = "mismatch-id"
    cases.append(
        ("bad_prompt_id", c_bad_prompt_id, "promptId: inconsistent with referenced summary prompt")
    )

    c_bad_res_prompt_id = _v3_payload()
    c_bad_res_prompt_id["results"]["results"][0]["prompt"]["id"] = "wrong-id"
    cases.append(
        ("bad_res_prompt_id", c_bad_res_prompt_id, "prompt.id: inconsistent with result promptId")
    )

    c_bad_opt_bool = _v3_payload()
    c_bad_opt_bool["results"]["results"][0]["testCase"]["options"]["disableVarExpansion"] = "false"
    cases.append(("bad_opt_bool", c_bad_opt_bool, "disableVarExpansion: expected a boolean"))

    c_bad_opt_str = _v3_payload()
    c_bad_opt_str["results"]["results"][0]["testCase"]["options"]["prefix"] = 123
    cases.append(("bad_opt_str", c_bad_opt_str, "prefix: expected a string"))

    c_bad_opt_dict = _v3_payload()
    c_bad_opt_dict["results"]["results"][0]["testCase"]["options"]["factuality"] = "bad"
    cases.append(("bad_opt_dict", c_bad_opt_dict, "factuality: expected a JSON object"))

    for name, payload, pattern in cases:
        p = _write_json(tmp_path / f"err_{name}.json", payload)
        with pytest.raises(AdapterError, match=pattern):
            promptfoo_source(p, name="x")

    # Test unreadable file OS error handling
    orig_read_text = Path.read_text

    def fail_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == valid_path:
            raise OSError("disk error")
        return orig_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_read_text)
    with pytest.raises(AdapterError, match="Cannot read Promptfoo export file"):
        promptfoo_source(valid_path, name="x")
