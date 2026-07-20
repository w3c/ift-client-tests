"""
Pluggable assertion registry for IFT client tests.

Frozen item schema:
  {"assert": "<type_id>", "value": ..., "scope": "delta"|"cumulative"|None, "config": {...}}

value/scope are always top-level; config holds type-specific extras only.
"""

import json
import re
import html as html_module

BUILTIN_ASSERTIONS = {}

PATCH_ASSERT_TYPES = frozenset({"patches_loaded", "patches_not_loaded"})
_PATCH_REGEX_VALUE = re.compile(r"^/(.+)/([a-z]*)$", re.DOTALL)


def serialize_assert_span(type_id, test_id, font_format, value, scope=None, config=None):
    """Emit a single .assert-result span with frozen data-* attributes."""
    value_json = html_module.escape(json.dumps(value, separators=(",", ":")))
    attrs = [
        'class="assert-result pending"',
        'data-assert="%s"' % html_module.escape(type_id),
        'data-assert-value="%s"' % value_json,
        'data-test-id="%s"' % html_module.escape(test_id),
        'data-format="%s"' % html_module.escape(font_format),
    ]
    if scope is not None:
        attrs.append('data-scope="%s"' % html_module.escape(scope))
    if config:
        cfg = html_module.escape(json.dumps(config, separators=(",", ":")))
        attrs.append('data-assert-config="%s"' % cfg)
    return "<span " + " ".join(attrs) + ">...</span>"


def register_assertion(spec_class):
    instance = spec_class()
    BUILTIN_ASSERTIONS[instance.type_id] = instance
    return spec_class


class AssertionSpec(object):
    type_id = None

    def validate(self, value, scope, config):
        pass

    def emit_html(self, test_id, font_format, value, scope, config):
        return serialize_assert_span(
            self.type_id,
            test_id,
            font_format,
            value=value,
            scope=scope,
            config=config or None,
        )

    def label(self, value, scope):
        return self.type_id


def _validate_patch_regex_value(name, param_name):
    """Validate a /pattern/flags patch assertion value and that the pattern compiles."""
    match = _PATCH_REGEX_VALUE.match(name)
    if not match:
        raise AssertionError(
            "%s: regex patch value must look like /pattern/flags, got %r"
            % (param_name, name)
        )
    pattern, flags = match.group(1), match.group(2)
    re_flags = 0
    for ch in flags:
        if ch == "i":
            re_flags |= re.IGNORECASE
        elif ch == "m":
            re_flags |= re.MULTILINE
        elif ch == "s":
            re_flags |= re.DOTALL
        else:
            raise AssertionError(
                "%s: unsupported regex flag %r in %r (allowed: i, m, s)"
                % (param_name, ch, name)
            )
    try:
        re.compile(pattern, re_flags)
    except re.error as exc:
        raise AssertionError(
            "%s: invalid regex %r: %s" % (param_name, name, exc)
        )


def _validate_patch_names(names, param_name):
    if not isinstance(names, (list, tuple)):
        raise TypeError("%s list value must be a list of patch filenames" % param_name)
    for name in names:
        if not isinstance(name, str):
            raise AssertionError(
                "%s: patch name must be a string, got %r" % (param_name, name)
            )
        # Literals never start with '/'; regex values use /pattern/flags.
        if name.startswith("/"):
            _validate_patch_regex_value(name, param_name)
            continue
        if not name.endswith((".ift_tk", ".ift_gk")):
            raise AssertionError(
                "%s: patch name must end with .ift_tk or .ift_gk "
                "(or be a /pattern/flags regex), got %r"
                % (param_name, name)
            )


def _validate_patch_assert_value(value, type_id):
    if isinstance(value, bool):
        if type_id == "patches_not_loaded" and value is False:
            raise ValueError(
                "patches_not_loaded=False is invalid; use True or a list of filenames"
            )
        return
    # Per-format maps: {"GLYF": [...], "CFF": [...]} (or a subset of formats).
    if isinstance(value, dict):
        if not value:
            raise ValueError("%s format map must not be empty" % type_id)
        for fmt, names in value.items():
            if not isinstance(fmt, str):
                raise TypeError("%s format keys must be strings, got %r" % (type_id, fmt))
            _validate_patch_names(names, "%s[%s]" % (type_id, fmt))
        return
    _validate_patch_names(value, type_id)


def _patch_value_label(value):
    if isinstance(value, dict):
        parts = []
        for fmt in sorted(value.keys()):
            parts.append("%s=%s" % (fmt, ", ".join(value[fmt])))
        return "; ".join(parts)
    return ", ".join(value)


@register_assertion
class PatchesLoadedAssertion(AssertionSpec):
    type_id = "patches_loaded"

    def validate(self, value, scope, config):
        if scope is not None and scope not in ("delta", "cumulative"):
            raise ValueError("scope must be 'delta' or 'cumulative', got %r" % scope)
        _validate_patch_assert_value(value, self.type_id)

    def label(self, value, scope):
        if value is True:
            return "Should Load Patches"
        if value is False:
            return "Should Not Load Patches"
        return "Should Load Patches: " + _patch_value_label(value)


@register_assertion
class PatchesNotLoadedAssertion(AssertionSpec):
    type_id = "patches_not_loaded"

    def validate(self, value, scope, config):
        if scope is not None and scope not in ("delta", "cumulative"):
            raise ValueError("scope must be 'delta' or 'cumulative', got %r" % scope)
        _validate_patch_assert_value(value, self.type_id)

    def label(self, value, scope):
        if value is True:
            return "Should Not Load Patches"
        return "Should Not Load Patches: " + _patch_value_label(value)


def normalize_assertion_item(item, default_scope=None):
    """
    Validate and normalize an assertion dict to the frozen schema.
    Returns a new dict with keys: assert, value, scope, config.
    """
    if not isinstance(item, dict):
        raise TypeError("Assertion item must be a dict, got %r" % type(item))
    if "assert" not in item:
        raise ValueError("Assertion item missing 'assert' type id: %r" % item)
    if "action" in item:
        raise ValueError("Assertion item must not contain 'action': %r" % item)

    type_id = item["assert"]
    if type_id not in BUILTIN_ASSERTIONS:
        raise ValueError(
            "Unknown assertion type %r. Registered: %s"
            % (type_id, sorted(BUILTIN_ASSERTIONS.keys()))
        )

    config = item.get("config") or {}
    if not isinstance(config, dict):
        raise TypeError("config must be a dict, got %r" % type(config))
    if "value" in config or "scope" in config:
        raise ValueError(
            "value/scope must be top-level fields, not inside config: %r" % item
        )

    if "value" not in item:
        raise ValueError("Assertion item missing 'value': %r" % item)

    value = item["value"]
    scope = item.get("scope", default_scope)

    if type_id in PATCH_ASSERT_TYPES and scope is None:
        scope = default_scope

    spec = BUILTIN_ASSERTIONS[type_id]
    spec.validate(value, scope, config if config else None)

    return {
        "assert": type_id,
        "value": value,
        "scope": scope,
        "config": dict(config) if config else {},
    }


def normalize_sequence_item(item, default_scope="delta"):
    """Normalize a sequence item (action or assertion)."""
    if not isinstance(item, dict):
        raise TypeError("Sequence item must be a dict, got %r" % type(item))

    if "action" in item:
        if "assert" in item:
            raise ValueError("Sequence item cannot have both action and assert: %r" % item)
        action = item["action"]
        if action != "render":
            raise ValueError("Unknown action %r (only 'render' is supported)" % action)
        if "text" not in item:
            raise ValueError("render action requires 'text': %r" % item)
        return {"action": "render", "text": item["text"]}

    if "assert" in item:
        return normalize_assertion_item(item, default_scope=default_scope)

    raise ValueError("Sequence item must have 'action' or 'assert': %r" % item)
