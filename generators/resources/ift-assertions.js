/**
 * IFT assertion registry — built-in handlers and serialize/deserialize helpers.
 * Import from ift.js. Add new types here with registerAssertion + matching Python AssertionSpec.
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

function patchesMatchAllow(loadedBasenames, value) {
  if (value === true) return loadedBasenames.size > 0;
  if (value === false) return loadedBasenames.size === 0;
  if (!Array.isArray(value) || value.length === 0) return false;
  return value.every((name) => loadedBasenames.has(name));
}

function patchesMatchDeny(loadedBasenames, value) {
  if (value === true) return loadedBasenames.size === 0;
  if (!Array.isArray(value) || value.length === 0) return true;
  return value.every((name) => !loadedBasenames.has(name));
}

function scopedPatches(ctx, item) {
  const scope = item.scope || 'delta';
  return scope === 'delta' ? ctx.patchesDelta : ctx.patchesCumulative;
}

registerAssertion('patches_loaded', (ctx, item) => {
  return patchesMatchAllow(scopedPatches(ctx, item), item.value);
});

registerAssertion('patches_not_loaded', (ctx, item) => {
  return patchesMatchDeny(scopedPatches(ctx, item), item.value);
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

  const passed = handler(ctx, item);
  span.textContent = passed ? 'PASS' : 'FAIL';
  span.classList.remove('pending');
  span.classList.add(passed ? 'pass' : 'fail');

  const scope = item.scope || 'delta';
  const loaded = scopedPatches(ctx, item);
  span.title = [
    `Assert: ${item.assert}`,
    `Scope: ${scope}`,
    `Value: ${JSON.stringify(item.value)}`,
    Object.keys(item.config || {}).length
      ? `Config: ${JSON.stringify(item.config)}`
      : null,
    `Loaded: ${[...loaded].join(', ') || 'none'}`,
  ]
    .filter(Boolean)
    .join('\n');
}
