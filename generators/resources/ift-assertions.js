/**
 * IFT assertion registry — built-in handlers and serialize/deserialize helpers.
 * Add new types here with registerAssertion + matching Python AssertionSpec.
 */

export const assertionHandlers = {};

export function registerAssertion(typeId, handler) {
  assertionHandlers[typeId] = handler;
}

export function deserializeAssertSpan(span) {
  const typeId = span.getAttribute('data-assert');
  const valueRaw = span.getAttribute('data-assert-value');
  const scope = span.getAttribute('data-scope'); // null if absent
  const configRaw = span.getAttribute('data-assert-config');

  return {
    assert: typeId,
    value: valueRaw === null ? null : JSON.parse(valueRaw),
    scope: scope,
    config: configRaw ? JSON.parse(configRaw) : {},
    testId: span.getAttribute('data-test-id'),
    format: span.getAttribute('data-format'),
  };
}

function resolveAssertValue(item) {
  const value = item.value;
  if (
    value &&
    typeof value === 'object' &&
    !Array.isArray(value) &&
    (Object.prototype.hasOwnProperty.call(value, 'GLYF') ||
      Object.prototype.hasOwnProperty.call(value, 'CFF'))
  ) {
    const format = item.format;
    if (!Object.prototype.hasOwnProperty.call(value, format)) {
      return undefined;
    }
    return value[format];
  }
  return value;
}

/** Parse /pattern/flags into a RegExp, or null if not a regex value. */
function parsePatchRegex(value) {
  if (typeof value !== 'string' || value.length < 2 || value[0] !== '/') {
    return null;
  }
  const lastSlash = value.lastIndexOf('/');
  if (lastSlash <= 0) return null;
  const pattern = value.slice(1, lastSlash);
  const flags = value.slice(lastSlash + 1);
  if (!/^[ims]*$/.test(flags)) return null;
  try {
    return new RegExp(pattern, flags);
  } catch (_) {
    return null;
  }
}

function patchNameMatches(loadedNames, expected) {
  const re = parsePatchRegex(expected);
  if (re) {
    for (const name of loadedNames) {
      if (re.test(name)) return true;
    }
    return false;
  }
  return loadedNames.has(expected);
}

function patchNameAbsent(loadedNames, expected) {
  const re = parsePatchRegex(expected);
  if (re) {
    for (const name of loadedNames) {
      if (re.test(name)) return false;
    }
    return true;
  }
  return !loadedNames.has(expected);
}

function patchesMatchAllow(loadedBasenames, value) {
  if (value === undefined) return false;
  if (value === true) return loadedBasenames.size > 0;
  if (value === false) return loadedBasenames.size === 0;
  if (!Array.isArray(value) || value.length === 0) return false;
  return value.every((name) => patchNameMatches(loadedBasenames, name));
}

function patchesMatchDeny(loadedBasenames, value) {
  if (value === undefined) return false;
  if (value === true) return loadedBasenames.size === 0;
  if (!Array.isArray(value) || value.length === 0) return true;
  return value.every((name) => patchNameAbsent(loadedBasenames, name));
}

function scopedPatches(ctx, item) {
  const scope = item.scope || 'delta';
  return scope === 'delta' ? ctx.patchesDelta : ctx.patchesCumulative;
}

registerAssertion('patches_loaded', (ctx, item) => {
  return patchesMatchAllow(scopedPatches(ctx, item), resolveAssertValue(item));
});

registerAssertion('patches_not_loaded', (ctx, item) => {
  return patchesMatchDeny(scopedPatches(ctx, item), resolveAssertValue(item));
});

export function runAssertion(span, ctx) {
  const item = deserializeAssertSpan(span);
  const handler = assertionHandlers[item.assert];
  if (!handler) {
    span.textContent = 'ERROR';
    span.classList.remove('pending');
    span.classList.add('fail');
    span.title = `No handler for assertion: ${item.assert}`;
    return;
  }

  if (
    ctx.timedOut &&
    (item.assert === 'patches_loaded' || item.assert === 'patches_not_loaded')
  ) {
    span.textContent = 'FAIL';
    span.classList.remove('pending');
    span.classList.add('fail');
    span.title =
      'Render barrier timed out; patch observation incomplete.\n' +
      `Loaded so far: ${[...(ctx.patchesDelta || [])].join(', ') || 'none'}`;
    return;
  }

  const resolvedValue = resolveAssertValue(item);
  const passed = handler(ctx, item);
  span.textContent = passed ? 'PASS' : 'FAIL';
  span.classList.remove('pending');
  span.classList.add(passed ? 'pass' : 'fail');

  const scope = item.scope || 'delta';
  const loaded = scopedPatches(ctx, item);
  span.title = [
    `Assert: ${item.assert}`,
    `Scope: ${scope}`,
    `Value: ${JSON.stringify(resolvedValue)}`,
    Object.keys(item.config || {}).length
      ? `Config: ${JSON.stringify(item.config)}`
      : null,
    `Loaded: ${[...loaded].join(', ') || 'none'}`,
  ]
    .filter(Boolean)
    .join('\n');
}
