"""Promptfoo evaluation export adapter (definition-only contract version 1)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from evalrepro.adapters.base import SnapshotSource
from evalrepro.errors import AdapterError
from evalrepro.hashing import digest
from evalrepro.runtime import runtime_versions

ADAPTER_NAME = "promptfoo-export"
ADAPTER_CONTRACT_VERSION = 1
RECORD_ID_DOMAIN = "evalrepro.promptfoo-export.record-id.v1"
EVAL_ID_DOMAIN = "evalrepro.promptfoo-export.eval-id.v1"
PINNED_PROMPTFOO_COMMIT = "ab84555c1b0ff74eca6b03abb7936ac9a0149242"

_TOP_LEVEL_KEYS = frozenset(
    {
        "evalId",
        "results",
        "config",
        "shareableUrl",
        "metadata",
        "vars",
        "runtimeOptions",
        "traces",
        "blobAssets",
    }
)
_SUMMARY_V2_KEYS = frozenset({"version", "timestamp", "results", "table", "stats"})
_SUMMARY_V3_KEYS = frozenset({"version", "timestamp", "results", "prompts", "stats"})
_RESULT_KEYS = frozenset(
    {
        "id",
        "description",
        "promptIdx",
        "testIdx",
        "testCase",
        "promptId",
        "provider",
        "prompt",
        "vars",
        "response",
        "error",
        "failureReason",
        "success",
        "score",
        "latencyMs",
        "gradingResult",
        "namedScores",
        "cost",
        "metadata",
        "tokenUsage",
        "evaluationId",
        "traceId",
    }
)
_PROMPT_KNOWN_KEYS = frozenset({"id", "raw", "template", "display", "label", "config"})
_PROVIDER_SEMANTIC_KEYS = (
    "id",
    "label",
    "config",
    "prompts",
    "transform",
    "delay",
    "env",
)
_PROVIDER_KNOWN_KEYS = frozenset(_PROVIDER_SEMANTIC_KEYS)
_TEST_CASE_KNOWN_KEYS = frozenset(
    {
        "description",
        "vars",
        "provider",
        "providers",
        "prompts",
        "providerOutput",
        "assert",
        "assertScoringFunction",
        "options",
        "threshold",
        "metadata",
    }
)
_TEST_OPTION_TRANSFORM_KEYS = ("postprocess", "transform", "transformVars", "storeOutputAs")
_TEST_OPTION_GRADER_KEYS = ("rubricPrompt", "provider", "factuality")
_TEST_OPTION_PROMPT_KEYS = (
    "prefix",
    "suffix",
    "disableVarExpansion",
    "disableConversationVar",
    "disableDefaultAsserts",
    "runSerially",
    "repeat",
)
_TEST_OPTION_KNOWN_KEYS = frozenset(
    _TEST_OPTION_TRANSFORM_KEYS + _TEST_OPTION_GRADER_KEYS + _TEST_OPTION_PROMPT_KEYS
)
_ASSERTION_KNOWN_KEYS = frozenset(
    {
        "type",
        "value",
        "config",
        "threshold",
        "weight",
        "provider",
        "rubricPrompt",
        "metric",
        "transform",
        "contextTransform",
    }
)
_ASSERTION_SET_KNOWN_KEYS = frozenset({"type", "assert", "weight", "metric", "threshold", "config"})
_CONFIG_NON_SEMANTIC_KEYS = frozenset(
    {
        "description",
        "outputPath",
        "sharing",
        "writeLatestResults",
        "tracing",
        "metadata",
        "providers",
        "targets",
        "prompts",
        "tests",
        "defaultTest",
        "evaluateOptions",
        "commandLineOptions",
    }
)
_CONFIG_KNOWN_SEMANTIC_KEYS = (
    "providerPromptMap",
    "nunjucksFilters",
    "env",
    "derivedMetrics",
    "extensions",
    "redteam",
    "scenarios",
    "tags",
)
_EVALUATE_OPTION_SEMANTIC_KEYS = ("repeat", "filterRange", "isRedteam")
_CLI_SEMANTIC_KEYS = (
    "promptPrefix",
    "promptSuffix",
    "repeat",
    "grader",
    "var",
    "filterErrorsOnly",
    "filterFailing",
    "filterFailingOnly",
    "filterFirstN",
    "filterMetadata",
    "filterPattern",
    "filterPrompts",
    "filterProviders",
    "filterRange",
    "filterSample",
    "filterSampleSeed",
    "filterTargets",
)
_RUNTIME_OPTION_SEMANTIC_KEYS = ("repeat", "filterRange", "isRedteam", "providerFilter")
_METADATA_KEYS = frozenset(
    {
        "promptfooVersion",
        "nodeVersion",
        "platform",
        "arch",
        "exportedAt",
        "evaluationCreatedAt",
        "author",
    }
)


def _reject_non_finite(constant: str) -> Any:
    raise AdapterError(
        f"Promptfoo export contains non-finite numeric constant {constant} at JSON parse time."
    )


def _file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
    except OSError as exc:
        raise AdapterError("Cannot read Promptfoo export file.") from exc
    return hasher.hexdigest()


def _read_json_export(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AdapterError("Cannot decode Promptfoo export file as UTF-8.") from exc
    except OSError as exc:
        raise AdapterError("Cannot read Promptfoo export file.") from exc

    try:
        value = json.loads(raw, parse_constant=_reject_non_finite)
    except json.JSONDecodeError as exc:
        raise AdapterError(
            f"Invalid JSON in Promptfoo export at line {exc.lineno}, column {exc.colno}."
        ) from exc

    if not isinstance(value, dict):
        raise AdapterError("$: Promptfoo export root must be a JSON object.")
    return value


def _require_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AdapterError(f"{path}: expected a JSON object.")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise AdapterError(f"{path}: expected a JSON array.")
    return value


def _require_str(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise AdapterError(f"{path}: expected a string.")
    if not allow_empty and not value.strip():
        raise AdapterError(f"{path}: expected a non-empty string.")
    return value


def _optional_str(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AdapterError(f"{path}: expected a string or null.")
    return value


def _require_non_negative_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AdapterError(f"{path}: expected a non-negative integer.")
    return value


def _optional_number(value: Any, path: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdapterError(f"{path}: expected a number or null.")
    return value


def _validate_inert_json(value: Any, path: str, *, allow_null: bool = True) -> Any:
    if value is None:
        if not allow_null:
            raise AdapterError(f"{path}: null is not permitted here.")
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[Function") and stripped.endswith("]"):
            raise AdapterError(f"{path}: opaque serialized function value is not supported.")
        return value
    if isinstance(value, list):
        return [
            _validate_inert_json(item, f"{path}[{idx}]", allow_null=allow_null)
            for idx, item in enumerate(value)
        ]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise AdapterError(f"{path}: object keys must be strings.")
            if key in {"function", "callApi"}:
                raise AdapterError(f"{path}.{key}: executable definition field is not supported.")
            out[key] = _validate_inert_json(item, f"{path}.{key}", allow_null=allow_null)
        return out
    raise AdapterError(f"{path}: unsupported JSON value type.")


def _validate_vars(value: Any, path: str) -> dict[str, Any]:
    if value is None:
        return {}
    mapping = _require_dict(value, path)
    return {
        key: _validate_inert_json(item, f"{path}.{key}", allow_null=True)
        for key, item in mapping.items()
    }


def _normalise_provider_entry(entry: Any, path: str) -> dict[str, Any]:
    if isinstance(entry, str):
        provider_id = _require_str(entry, path)
        return {
            "id": provider_id,
            "label": None,
            "config": {},
            "prompts": None,
            "transform": None,
            "delay": None,
            "env": None,
            "extra": {},
        }
    mapping = _require_dict(entry, path)
    if "id" in mapping:
        provider_id = _require_str(mapping.get("id"), f"{path}.id")
        body = mapping
        body_path = path
    elif len(mapping) == 1:
        raw_id, raw_body = next(iter(mapping.items()))
        provider_id = _require_str(raw_id, path)
        body = _require_dict(raw_body, f"{path}.{raw_id}")
        body_path = f"{path}.{raw_id}"
    else:
        raise AdapterError(
            f"{path}: provider entry must have an 'id' string or be a single-keyed provider map."
        )

    _validate_inert_json(body, body_path)
    label = _optional_str(body.get("label"), f"{body_path}.label")
    raw_config = body.get("config")
    config = _require_dict(raw_config, f"{body_path}.config") if raw_config is not None else {}
    prompts = body.get("prompts")
    if prompts is not None:
        prompts_list = _require_list(prompts, f"{body_path}.prompts")
        for idx, item in enumerate(prompts_list):
            _require_str(item, f"{body_path}.prompts[{idx}]")
    transform = _optional_str(body.get("transform"), f"{body_path}.transform")
    delay = _optional_number(body.get("delay"), f"{body_path}.delay")
    env = body.get("env")
    if env is not None:
        _require_dict(env, f"{body_path}.env")
    extra = {k: v for k, v in body.items() if k not in _PROVIDER_KNOWN_KEYS}
    return {
        "id": provider_id,
        "label": label,
        "config": config,
        "prompts": prompts,
        "transform": transform,
        "delay": delay,
        "env": env,
        "extra": extra,
    }


def _parse_config_providers(config: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    has_providers = "providers" in config
    has_targets = "targets" in config
    if has_providers and has_targets:
        raise AdapterError("$.config: cannot specify both 'providers' and 'targets'.")
    key = "targets" if has_targets else "providers"
    if key not in config or config[key] is None:
        return False, []
    raw = config[key]
    path = f"$.config.{key}"
    if isinstance(raw, str):
        return True, [_normalise_provider_entry(raw, path)]
    if isinstance(raw, list):
        return True, [
            _normalise_provider_entry(item, f"{path}[{idx}]") for idx, item in enumerate(raw)
        ]
    if isinstance(raw, dict):
        if "id" in raw:
            return True, [_normalise_provider_entry(raw, path)]
        return True, [_normalise_provider_entry({k: v}, f"{path}.{k}") for k, v in raw.items()]
    raise AdapterError(f"{path}: unsupported providers schema shape.")


def _merge_provider_definitions(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged_config = {**base["config"], **override["config"]}
    merged_extra = {**base["extra"], **override["extra"]}
    return {
        "id": override["id"] or base["id"],
        "label": override["label"] if override["label"] is not None else base["label"],
        "config": merged_config,
        "prompts": override["prompts"] if override["prompts"] is not None else base["prompts"],
        "transform": (
            override["transform"] if override["transform"] is not None else base["transform"]
        ),
        "delay": override["delay"] if override["delay"] is not None else base["delay"],
        "env": override["env"] if override["env"] is not None else base["env"],
        "extra": merged_extra,
    }


def _resolve_provider(
    provider_stub: Any,
    test_provider_override: Any,
    has_config_providers: bool,
    config_providers: list[dict[str, Any]],
    result_path: str,
) -> dict[str, Any]:
    stub_path = f"{result_path}.provider"
    if isinstance(provider_stub, str):
        stub_id = _require_str(provider_stub, stub_path)
        stub_label: str | None = None
        stub_norm = _normalise_provider_entry(provider_stub, stub_path)
    else:
        stub_dict = _require_dict(provider_stub, stub_path)
        stub_id = _require_str(stub_dict.get("id"), f"{stub_path}.id")
        stub_label = _optional_str(stub_dict.get("label"), f"{stub_path}.label")
        stub_norm = _normalise_provider_entry(stub_dict, stub_path)

    override_norm: dict[str, Any] | None = None
    if test_provider_override is not None:
        override_norm = _normalise_provider_entry(
            test_provider_override, f"{result_path}.testCase.provider"
        )

    matched_base: dict[str, Any] | None = None
    if has_config_providers:
        exact_matches = [
            p
            for p in config_providers
            if p["id"] == stub_id and (stub_label is None or p["label"] == stub_label)
        ]
        if not exact_matches and stub_label is not None:
            id_matches = [p for p in config_providers if p["id"] == stub_id and p["label"] is None]
            if len(id_matches) == 1:
                exact_matches = id_matches
        if len(exact_matches) == 1:
            matched_base = exact_matches[0]
        elif len(exact_matches) > 1:
            unique_defs = {digest(p): p for p in exact_matches}
            if len(unique_defs) > 1:
                raise AdapterError(f"{stub_path}: ambiguous provider match in $.config.providers.")
            matched_base = exact_matches[0]
        elif override_norm is None:
            raise AdapterError(f"{stub_path}: provider not found in $.config.providers.")

    effective = matched_base or stub_norm
    effective = _merge_provider_definitions(effective, stub_norm)
    if override_norm is not None:
        effective = _merge_provider_definitions(effective, override_norm)
    return effective


def _normalise_assertion(item: Any, path: str) -> dict[str, Any]:
    mapping = _require_dict(item, path)
    _validate_inert_json(mapping, path)
    assertion_type = _require_str(mapping.get("type"), f"{path}.type")
    if assertion_type == "assert-set":
        sub_asserts = _require_list(mapping.get("assert"), f"{path}.assert")
        threshold = _optional_number(mapping.get("threshold"), f"{path}.threshold")
        weight = _optional_number(mapping.get("weight"), f"{path}.weight")
        metric = _optional_str(mapping.get("metric"), f"{path}.metric")
        raw_cfg = mapping.get("config")
        cfg = _require_dict(raw_cfg, f"{path}.config") if raw_cfg is not None else None
        extra = {k: v for k, v in mapping.items() if k not in _ASSERTION_SET_KNOWN_KEYS}
        return {
            "type": "assert-set",
            "assert": [
                _normalise_assertion(sub, f"{path}.assert[{idx}]")
                for idx, sub in enumerate(sub_asserts)
            ],
            "threshold": threshold,
            "weight": weight,
            "metric": metric,
            "config": cfg,
            "extra": extra,
        }

    threshold = _optional_number(mapping.get("threshold"), f"{path}.threshold")
    weight = _optional_number(mapping.get("weight"), f"{path}.weight")
    metric = _optional_str(mapping.get("metric"), f"{path}.metric")
    transform = _optional_str(mapping.get("transform"), f"{path}.transform")
    context_transform = _optional_str(mapping.get("contextTransform"), f"{path}.contextTransform")
    raw_cfg = mapping.get("config")
    cfg = _require_dict(raw_cfg, f"{path}.config") if raw_cfg is not None else None
    extra = {k: v for k, v in mapping.items() if k not in _ASSERTION_KNOWN_KEYS}
    return {
        "type": assertion_type,
        "value": mapping.get("value"),
        "config": cfg,
        "threshold": threshold,
        "weight": weight,
        "provider": mapping.get("provider"),
        "rubricPrompt": mapping.get("rubricPrompt"),
        "metric": metric,
        "transform": transform,
        "contextTransform": context_transform,
        "extra": extra,
    }


def _normalise_prompt(
    prompt_obj: Any,
    summary_prompt: dict[str, Any] | None,
    path: str,
) -> dict[str, Any]:
    mapping = _require_dict(prompt_obj, path)
    _validate_inert_json(mapping, path)
    raw = _require_str(mapping.get("raw"), f"{path}.raw", allow_empty=True)
    label = _require_str(mapping.get("label"), f"{path}.label", allow_empty=True)
    prompt_id = _optional_str(mapping.get("id"), f"{path}.id")
    template = _optional_str(mapping.get("template"), f"{path}.template")
    display = _optional_str(mapping.get("display"), f"{path}.display")
    raw_cfg = mapping.get("config")
    cfg = _require_dict(raw_cfg, f"{path}.config") if raw_cfg is not None else None
    extra = {k: v for k, v in mapping.items() if k not in _PROMPT_KNOWN_KEYS}

    summary_template: dict[str, Any] | None = None
    if summary_prompt is not None:
        summary_template = {
            "id": summary_prompt.get("id"),
            "raw": summary_prompt.get("raw"),
            "label": summary_prompt.get("label"),
            "config": summary_prompt.get("config"),
            "extra": summary_prompt.get("extra", {}),
        }

    return {
        "id": prompt_id,
        "raw": raw,
        "template": template,
        "display": display,
        "label": label,
        "config": cfg,
        "summary_prompt": summary_template,
        "extra": extra,
    }


def _validate_summary_prompts(
    summary: dict[str, Any], summary_version: int
) -> list[dict[str, Any]]:
    if summary_version == 2:
        table = _require_dict(summary.get("table"), "$.results.table")
        head = _require_dict(table.get("head"), "$.results.table.head")
        _require_list(table.get("body"), "$.results.table.body")
        vars_list = _require_list(head.get("vars"), "$.results.table.head.vars")
        for idx, var_name in enumerate(vars_list):
            _require_str(var_name, f"$.results.table.head.vars[{idx}]", allow_empty=True)
        raw_prompts = _require_list(head.get("prompts"), "$.results.table.head.prompts")
        base_path = "$.results.table.head.prompts"
    else:
        raw_prompts = _require_list(summary.get("prompts"), "$.results.prompts")
        base_path = "$.results.prompts"

    normalised: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_prompts):
        item_path = f"{base_path}[{idx}]"
        mapping = _require_dict(item, item_path)
        _validate_inert_json(mapping, item_path)
        raw = _require_str(mapping.get("raw"), f"{item_path}.raw", allow_empty=True)
        label = _require_str(mapping.get("label"), f"{item_path}.label", allow_empty=True)
        prompt_id = _optional_str(mapping.get("id"), f"{item_path}.id")
        raw_cfg = mapping.get("config")
        cfg = _require_dict(raw_cfg, f"{item_path}.config") if raw_cfg is not None else None
        extra = {
            k: v
            for k, v in mapping.items()
            if k not in (_PROMPT_KNOWN_KEYS | {"provider", "metrics"})
        }
        normalised.append(
            {
                "id": prompt_id,
                "raw": raw,
                "label": label,
                "config": cfg,
                "extra": extra,
            }
        )
    return normalised


def _extract_suite_semantics(
    config: dict[str, Any],
    runtime_options: dict[str, Any] | None,
) -> dict[str, Any]:
    _validate_inert_json(config, "$.config")
    known: dict[str, Any] = {}
    for key in _CONFIG_KNOWN_SEMANTIC_KEYS:
        if key in config and config[key] is not None:
            known[key] = config[key]

    eval_opts = config.get("evaluateOptions")
    if eval_opts is not None:
        eval_opts_dict = _require_dict(eval_opts, "$.config.evaluateOptions")
        filtered_eval = {
            k: eval_opts_dict[k]
            for k in _EVALUATE_OPTION_SEMANTIC_KEYS
            if k in eval_opts_dict and eval_opts_dict[k] is not None
        }
        if filtered_eval:
            known["evaluateOptions"] = filtered_eval

    cli_opts = config.get("commandLineOptions")
    if cli_opts is not None:
        cli_opts_dict = _require_dict(cli_opts, "$.config.commandLineOptions")
        filtered_cli = {
            k: cli_opts_dict[k]
            for k in _CLI_SEMANTIC_KEYS
            if k in cli_opts_dict and cli_opts_dict[k] is not None
        }
        if filtered_cli:
            known["commandLineOptions"] = filtered_cli

    if runtime_options is not None:
        _validate_inert_json(runtime_options, "$.runtimeOptions")
        filtered_runtime = {
            k: runtime_options[k]
            for k in _RUNTIME_OPTION_SEMANTIC_KEYS
            if k in runtime_options and runtime_options[k] is not None
        }
        if filtered_runtime:
            known["runtimeOptions"] = filtered_runtime

    extra = {
        k: v
        for k, v in config.items()
        if k not in _CONFIG_NON_SEMANTIC_KEYS and k not in _CONFIG_KNOWN_SEMANTIC_KEYS
    }
    return {"config": known, "extra": extra}


def _build_record(
    raw_result: Any,
    index: int,
    summary_prompts: list[dict[str, Any]],
    suite_semantics: dict[str, Any],
    has_config_providers: bool,
    config_providers: list[dict[str, Any]],
) -> dict[str, Any]:
    path = f"$.results.results[{index}]"
    result_map = _require_dict(raw_result, path)
    unknown_result_keys = set(result_map) - _RESULT_KEYS
    if unknown_result_keys:
        first_key = sorted(unknown_result_keys)[0]
        raise AdapterError(f"{path}.{first_key}: unsupported result field.")

    prompt_idx = _require_non_negative_int(result_map.get("promptIdx"), f"{path}.promptIdx")
    _require_non_negative_int(result_map.get("testIdx"), f"{path}.testIdx")
    prompt_id = _require_str(result_map.get("promptId"), f"{path}.promptId")

    if prompt_idx >= len(summary_prompts):
        raise AdapterError(f"{path}.promptIdx: index out of bounds for summary prompts.")
    summary_prompt = summary_prompts[prompt_idx]

    if summary_prompt.get("id") is not None and summary_prompt["id"] != prompt_id:
        raise AdapterError(f"{path}.promptId: inconsistent with referenced summary prompt.")

    prompt_def = _normalise_prompt(result_map.get("prompt"), summary_prompt, f"{path}.prompt")

    if prompt_def.get("id") is not None and prompt_def["id"] != prompt_id:
        raise AdapterError(f"{path}.prompt.id: inconsistent with result promptId.")

    test_path = f"{path}.testCase"
    test_case = _require_dict(result_map.get("testCase"), test_path)
    _validate_inert_json(test_case, test_path)

    provider_def = _resolve_provider(
        result_map.get("provider"),
        test_case.get("provider"),
        has_config_providers,
        config_providers,
        path,
    )

    test_vars = _validate_vars(test_case.get("vars"), f"{test_path}.vars")
    result_vars = _validate_vars(result_map.get("vars"), f"{path}.vars")
    effective_vars = {**test_vars, **result_vars}

    test_options_raw = test_case.get("options")
    test_options = (
        _require_dict(test_options_raw, f"{test_path}.options")
        if test_options_raw is not None
        else {}
    )
    if "repeat" in test_options:
        rep = test_options["repeat"]
        if isinstance(rep, bool) or not isinstance(rep, int) or rep <= 0:
            raise AdapterError(f"{test_path}.options.repeat: expected a positive integer.")

    test_asserts_raw = test_case.get("assert")
    effective_assertions = (
        [
            _normalise_assertion(item, f"{test_path}.assert[{idx}]")
            for idx, item in enumerate(_require_list(test_asserts_raw, f"{test_path}.assert"))
        ]
        if test_asserts_raw is not None
        else []
    )

    transforms: dict[str, Any] = {}
    for key in _TEST_OPTION_TRANSFORM_KEYS:
        if key in test_options and test_options[key] is not None:
            transforms[key] = _require_str(test_options[key], f"{test_path}.options.{key}")
    if provider_def["transform"] is not None:
        transforms["providerTransform"] = provider_def["transform"]

    grader_config: dict[str, Any] = {}
    for key in ("rubricPrompt", "provider"):
        if key in test_options and test_options[key] is not None:
            val = test_options[key]
            if key == "rubricPrompt" and not isinstance(val, str):
                raise AdapterError(f"{test_path}.options.{key}: expected a string.")
            if key == "provider" and not isinstance(val, (str, dict)):
                raise AdapterError(f"{test_path}.options.{key}: expected a string or object.")
            grader_config[key] = val

    if "factuality" in test_options and test_options["factuality"] is not None:
        grader_config["factuality"] = _require_dict(
            test_options["factuality"], f"{test_path}.options.factuality"
        )

    scoring_fn = test_case.get("assertScoringFunction")
    if scoring_fn is not None:
        grader_config["assertScoringFunction"] = _require_str(
            scoring_fn, f"{test_path}.assertScoringFunction"
        )

    effective_test_options: dict[str, Any] = {}
    for key in ("prefix", "suffix"):
        if key in test_options and test_options[key] is not None:
            effective_test_options[key] = _require_str(
                test_options[key], f"{test_path}.options.{key}"
            )

    for key in (
        "disableVarExpansion",
        "disableConversationVar",
        "disableDefaultAsserts",
        "runSerially",
    ):
        if key in test_options and test_options[key] is not None:
            val = test_options[key]
            if not isinstance(val, bool):
                raise AdapterError(f"{test_path}.options.{key}: expected a boolean.")
            effective_test_options[key] = val

    if "repeat" in test_options and test_options["repeat"] is not None:
        rep = test_options["repeat"]
        if isinstance(rep, bool) or not isinstance(rep, int) or rep <= 0:
            raise AdapterError(f"{test_path}.options.repeat: expected a positive integer.")
        effective_test_options["repeat"] = rep

    options_extra = {k: v for k, v in test_options.items() if k not in _TEST_OPTION_KNOWN_KEYS}
    if options_extra:
        effective_test_options["extra"] = options_extra

    for filter_key in ("providers", "prompts"):
        val = test_case.get(filter_key)
        if val is not None:
            items = _require_list(val, f"{test_path}.{filter_key}")
            for idx, item in enumerate(items):
                _require_str(item, f"{test_path}.{filter_key}[{idx}]")
            effective_test_options[filter_key] = items

    threshold = _optional_number(test_case.get("threshold"), f"{test_path}.threshold")
    assertion_thresholds = {
        str(idx): item["threshold"]
        for idx, item in enumerate(effective_assertions)
        if item.get("threshold") is not None
    }
    thresholds = {
        "test": threshold,
        "assertions": assertion_thresholds,
    }

    has_provider_output = "providerOutput" in test_case
    provider_output_val: Any = None
    if has_provider_output:
        provider_output_val = test_case["providerOutput"]
        if not isinstance(provider_output_val, (str, dict)):
            raise AdapterError(
                f"{test_path}.providerOutput: expected a string or object, not null."
            )

    test_meta_raw = test_case.get("metadata")
    effective_test_meta = (
        _require_dict(test_meta_raw, f"{test_path}.metadata") if test_meta_raw is not None else {}
    )

    description = _optional_str(test_case.get("description"), f"{test_path}.description")
    if description is None:
        description = _optional_str(result_map.get("description"), f"{path}.description")

    definition_extra = {k: v for k, v in test_case.items() if k not in _TEST_CASE_KNOWN_KEYS}
    if suite_semantics["config"] or suite_semantics["extra"]:
        definition_extra["suite"] = suite_semantics

    input_payload: dict[str, Any] = {
        "prompt_id": prompt_id,
        "prompt": prompt_def,
        "vars": effective_vars,
        "provider": provider_def,
    }

    if transforms:
        input_payload["transform"] = transforms
    else:
        input_payload["transform"] = None

    if has_provider_output:
        input_payload["provider_output"] = provider_output_val

    target_payload: dict[str, Any] = {
        "assertions": effective_assertions,
        "thresholds": thresholds,
        "grader_configuration": grader_config,
    }

    metadata_payload: dict[str, Any] = {
        "test_description": description,
        "test_metadata": effective_test_meta,
        "test_options": effective_test_options,
        "definition_extra": definition_extra,
    }

    record_id = digest(
        {
            "domain": RECORD_ID_DOMAIN,
            "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
            "prompt_id": prompt_id,
            "prompt": prompt_def,
            "provider": provider_def,
            "input": input_payload,
            "target": target_payload,
            "metadata": metadata_payload,
        }
    )

    return {
        "id": record_id,
        "input": input_payload,
        "target": target_payload,
        "choices": None,
        "metadata": metadata_payload,
    }


def promptfoo_source(
    path: Path,
    *,
    name: str,
    mode: str = "definition",
) -> SnapshotSource:
    """Load a stored Promptfoo evaluation export in definition-only mode."""
    if not isinstance(name, str) or not name.strip():
        raise AdapterError("Promptfoo evaluation name must be a non-empty string.")
    if mode != "definition":
        raise AdapterError("Promptfoo adapter contract version 1 supports only mode='definition'.")

    try:
        resolved = path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise AdapterError("Promptfoo export path does not exist or cannot be resolved.") from exc
    if not resolved.is_file():
        raise AdapterError("Promptfoo export path is not a regular file.")

    export_data = _read_json_export(resolved)
    unknown_top = set(export_data) - _TOP_LEVEL_KEYS
    if unknown_top:
        first_top = sorted(unknown_top)[0]
        raise AdapterError(f"$.{first_top}: unsupported top-level export field.")

    eval_id = _optional_str(export_data.get("evalId"), "$.evalId")
    _optional_str(export_data.get("shareableUrl"), "$.shareableUrl")

    if "vars" in export_data and export_data["vars"] is not None:
        top_vars = _require_list(export_data["vars"], "$.vars")
        for idx, item in enumerate(top_vars):
            _require_str(item, f"$.vars[{idx}]", allow_empty=True)

    traces_present = False
    if "traces" in export_data and export_data["traces"] is not None:
        traces_list = _require_list(export_data["traces"], "$.traces")
        traces_present = len(traces_list) > 0

    blob_assets = export_data.get("blobAssets")
    if blob_assets is not None:
        blob_list = _require_list(blob_assets, "$.blobAssets")
        if len(blob_list) > 0:
            raise AdapterError(
                "$.blobAssets: Promptfoo contract version 1 rejects non-empty embedded media."
            )

    results_summary = _require_dict(export_data.get("results"), "$.results")
    summary_version = results_summary.get("version")
    if isinstance(summary_version, bool) or summary_version not in {2, 3}:
        raise AdapterError("$.results.version: unsupported summary version; expected 2 or 3.")

    allowed_summary_keys = _SUMMARY_V2_KEYS if summary_version == 2 else _SUMMARY_V3_KEYS
    unknown_summary = set(results_summary) - allowed_summary_keys
    if unknown_summary:
        first_summary = sorted(unknown_summary)[0]
        raise AdapterError(f"$.results.{first_summary}: unsupported summary field.")

    summary_timestamp = _optional_str(results_summary.get("timestamp"), "$.results.timestamp")
    if "stats" in results_summary and results_summary["stats"] is not None:
        _require_dict(results_summary["stats"], "$.results.stats")

    summary_prompts = _validate_summary_prompts(results_summary, summary_version)
    results_list = _require_list(results_summary.get("results"), "$.results.results")

    raw_config = export_data.get("config")
    if raw_config is None:
        raise AdapterError("$.config: missing required top-level object.")
    config = _require_dict(raw_config, "$.config")

    raw_runtime_options = export_data.get("runtimeOptions")
    runtime_options = (
        _require_dict(raw_runtime_options, "$.runtimeOptions")
        if raw_runtime_options is not None
        else None
    )

    has_config_providers, config_providers = _parse_config_providers(config)
    suite_semantics = _extract_suite_semantics(config, runtime_options)

    records = [
        _build_record(
            raw_result,
            index,
            summary_prompts,
            suite_semantics,
            has_config_providers,
            config_providers,
        )
        for index, raw_result in enumerate(results_list)
    ]

    raw_metadata = export_data.get("metadata")
    metadata = _require_dict(raw_metadata, "$.metadata") if raw_metadata is not None else {}
    unknown_meta = set(metadata) - _METADATA_KEYS
    if unknown_meta:
        first_meta = sorted(unknown_meta)[0]
        raise AdapterError(f"$.metadata.{first_meta}: unsupported export metadata field.")

    promptfoo_version = _optional_str(
        metadata.get("promptfooVersion"), "$.metadata.promptfooVersion"
    )
    node_version = _optional_str(metadata.get("nodeVersion"), "$.metadata.nodeVersion")
    meta_platform = _optional_str(metadata.get("platform"), "$.metadata.platform")
    meta_arch = _optional_str(metadata.get("arch"), "$.metadata.arch")
    exported_at = _optional_str(metadata.get("exportedAt"), "$.metadata.exportedAt")
    evaluation_created_at = _optional_str(
        metadata.get("evaluationCreatedAt"), "$.metadata.evaluationCreatedAt"
    )
    _optional_str(metadata.get("author"), "$.metadata.author")

    eval_id_digest = (
        digest({"domain": EVAL_ID_DOMAIN, "eval_id": eval_id}) if eval_id is not None else None
    )

    return SnapshotSource(
        adapter=ADAPTER_NAME,
        identity={
            "name": name.strip(),
            "mode": mode,
        },
        parameters={
            "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
            "record_identity_policy": RECORD_ID_DOMAIN,
            "definition_extra_policy": "included",
            "media_policy": "reject_blob_assets",
        },
        records=records,
        declared_count=len(records),
        fields=("input", "target", "choices", "metadata"),
        id_field="id",
        runtime={
            **runtime_versions(),
            "promptfooVersion": promptfoo_version,
            "nodeVersion": node_version,
            "exportPlatform": meta_platform,
            "exportArch": meta_arch,
        },
        provenance={
            "source_sha256": _file_digest(resolved),
            "eval_id_sha256": eval_id_digest,
            "summary_version": summary_version,
            "summary_timestamp": summary_timestamp,
            "exported_at": exported_at,
            "evaluation_created_at": evaluation_created_at,
            "traces_present": traces_present,
            "blob_assets_present": False,
            "pinned_upstream_commit": PINNED_PROMPTFOO_COMMIT,
        },
    )
