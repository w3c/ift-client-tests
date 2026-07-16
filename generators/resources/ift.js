import init, { IftState } from './rust-client/pkg/rust_client.js';
import { runAssertion } from './ift-assertions.js';

const RENDER_BARRIER_TIMEOUT_MS = 5000;
const OBSERVER_QUIET_MS = 150;

let states = {};
const patchLoadsByTest = new Map(); // key: "testId|format" -> Set of basenames
const resourceEntriesByTest = new Map(); // key: "testId|format" -> PerformanceResourceTiming[]
let patchObserver = null;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function patchKey(testId, format) {
  return `${testId}|${format}`;
}

function isPatchUrl(url) {
  return /\.(ift_tk|ift_gk)(?:[?#]|$)/.test(url);
}

function attributePatchEntry(entry) {
  if (!isPatchUrl(entry.name)) return null;
  if (!(entry.decodedBodySize > 0 || entry.transferSize > 0)) return null;
  const match = entry.name.match(/\/([^/]+)\/(GLYF|CFF)\/([^/?#]+\.(?:ift_tk|ift_gk))(?:[?#]|$)/);
  if (!match) return null;
  return {
    testId: match[1],
    format: match[2],
    basename: match[3],
    entry,
  };
}

function ingestResourceEntry(entry) {
  const attributed = attributePatchEntry(entry);
  if (!attributed) return;
  const key = patchKey(attributed.testId, attributed.format);
  if (!patchLoadsByTest.has(key)) {
    patchLoadsByTest.set(key, new Set());
  }
  patchLoadsByTest.get(key).add(attributed.basename);
  if (!resourceEntriesByTest.has(key)) {
    resourceEntriesByTest.set(key, []);
  }
  // Avoid duplicate entries for the same URL
  const list = resourceEntriesByTest.get(key);
  if (!list.some((e) => e.name === entry.name)) {
    list.push(entry);
  }
}

function initPatchObserver() {
  if (patchObserver) return;
  patchObserver = new PerformanceObserver((list) => {
    list.getEntries().forEach(ingestResourceEntry);
  });
  patchObserver.observe({ type: 'resource', buffered: true });
  if (performance.setResourceTimingBufferSize) {
    performance.setResourceTimingBufferSize(500);
  }
}

function drainObserverRecords() {
  if (!patchObserver) return;
  for (const entry of patchObserver.takeRecords()) {
    ingestResourceEntry(entry);
  }
}

async function awaitRenderBarrier(testId, format) {
  const key = patchKey(testId, format);
  const deadline = performance.now() + RENDER_BARRIER_TIMEOUT_MS;

  drainObserverRecords();
  let lastCount = (patchLoadsByTest.get(key) || new Set()).size;
  let quietSince = performance.now();

  while (performance.now() < deadline) {
    await sleep(50);
    drainObserverRecords();
    const nowCount = (patchLoadsByTest.get(key) || new Set()).size;
    if (nowCount !== lastCount) {
      lastCount = nowCount;
      quietSince = performance.now();
      continue;
    }
    if (performance.now() - quietSince >= OBSERVER_QUIET_MS) {
      return { ok: true, timedOut: false };
    }
  }

  drainObserverRecords();
  return { ok: false, timedOut: true };
}

function codepointsFrom(text) {
  const cps = new Set();
  for (let i = 0; text.codePointAt(i); i++) {
    const cp = text.codePointAt(i);
    cps.add(cp);
    if (cp > 0xffff) i++;
  }
  return [...cps];
}

function newCodepoints(prevText, cumulativeText) {
  const prev = new Set(codepointsFrom(prevText || ''));
  return codepointsFrom(cumulativeText).filter((cp) => !prev.has(cp));
}

const woff2_decoder = {
  unwoff2: (encoded) => {
    let decoder = new window.Woff2Decoder(encoded);
    return decoder.data();
  },
};

function patch_codepoints(font_id, font_face, cps, features, axes) {
  if (!states[font_id]) {
    states[font_id] = IftState.new(font_id);
  }
  let state = states[font_id];

  for (const [tag, point] of axes) {
    state.add_design_space_to_target_subset_definition(tag, point, point);
  }

  for (const tag of features) {
    state.add_feature_to_target_subset_definition(tag);
  }

  state.add_to_target_subset_definition(cps);
  return state.current_font_subset(woff2_decoder).then((font) => {
    const font_data = new Uint8Array(
      window.ift_memory.buffer,
      font.data(),
      font.len()
    );
    font = new FontFace(font_face, font_data, {});
    return font.load();
  });
}

function update_fonts(text, font_id, font_face, features, ds) {
  let cps = new Set();
  for (let i = 0; text.codePointAt(i); i++) {
    cps.add(text.codePointAt(i));
  }

  let cps_array = [];
  for (let cp of cps) {
    cps_array.push(cp);
  }

  let axes = new Map();
  for (let [tag, value] of Object.entries(ds)) {
    axes.set(tag, value);
  }

  return patch_codepoints(font_id, font_face, cps_array, features, axes);
}

/** Stable font URL per sequence case so IftState stays incremental across renders. */
const sequenceFontUrls = new Map();

function extendSubset(testId, format, fontName, cumulativeText, prevText) {
  const key = patchKey(testId, format);
  if (!sequenceFontUrls.has(key)) {
    const rndNum = Math.floor(Math.random() * 100000);
    sequenceFontUrls.set(
      key,
      `${testId}/${format}/myfont-mod.ift.woff2?v=${rndNum}`
    );
  }
  const fontUrl = sequenceFontUrls.get(key);
  // First render: request all codepoints in cumulative text.
  // Later renders: only add newly introduced codepoints (IftState is incremental).
  const cps =
    prevText === ''
      ? codepointsFrom(cumulativeText)
      : newCodepoints(prevText, cumulativeText);
  // Always include at least the cumulative set on first call; if delta is empty
  // (same text), still call with empty array — add_* returns false, subset unchanged.
  return patch_codepoints(fontUrl, fontName, cps, [], new Map());
}

function applyFontToSequenceRenders(testId, format, fontName) {
  const testCase = document.getElementById(testId);
  if (!testCase || !testCase.classList.contains('sequence')) return;
  const details = testCase.querySelector(
    `.testCaseDetails[data-format="${format}"]`
  );
  if (!details) return;
  const fallback = 'RobotoFallback';
  for (const el of details.querySelectorAll('.render-text')) {
    el.style.fontFamily = `${fontName}, ${fallback}`;
  }
}

/**
 * Load the subsetted ligature IFT font into a dedicated FontFace for .result.
 * Uses {testId}/{format}/visual/ so it does not share state or patches with
 * the sequence font.
 */
async function loadSequenceLigatureResult(testId, format) {
  const testCase = document.getElementById(testId);
  if (!testCase || !testCase.classList.contains('sequence')) return;
  const details = testCase.querySelector(
    `.testCaseDetails[data-format="${format}"]`
  );
  if (!details) return;
  const resultEl = details.querySelector('.result');
  if (!resultEl) return;

  const visualFontName = `${format}-${testId}-Visual-IFT-Font`;
  const fallback = 'RobotoFallback';
  resultEl.style.fontFamily = `${visualFontName}, ${fallback}`;

  const sample = resultEl.textContent.trim() === 'F' ? 'FAIL' : 'PASS';
  const rndNum = Math.floor(Math.random() * 100000);
  const fontUrl = `${testId}/${format}/visual/myfont-mod.ift.woff2?v=${rndNum}`;
  try {
    const font = await update_fonts(sample, fontUrl, visualFontName, [], {});
    document.fonts.add(font);
  } catch (e) {
    console.error(
      `Visual ligature font failed for ${testId}/${format}:`,
      e
    );
  }
}

function buildAssertionContext(state) {
  const key = patchKey(state.testId, state.format);
  return {
    testId: state.testId,
    format: state.format,
    renderText: state.prevText,
    patchesCumulative: new Set(patchLoadsByTest.get(key) || []),
    patchesDelta: new Set(state.lastRender?.patchesDelta || []),
    fontFaceName: state.fontName,
    fontLoaded: !!state.lastRender?.fontLoaded,
    timedOut: !!state.lastRender?.timedOut,
    resourceEntries: [...(resourceEntriesByTest.get(key) || [])],
  };
}

/** Legacy single-shot tests only — skip sequence cases to avoid double-fetch. */
async function update_legacy_result_tests() {
  const resultElements = document.querySelectorAll(
    '.testCase:not(.sequence) .result'
  );
  for (let el of resultElements) {
    let test_name = el.id.replace(/^[^-]+-/, '');
    console.log('Processing test:', test_name);
    let font_format = el.getAttribute('data-format');
    let rndNum = Math.floor(Math.random() * 100000);
    let title_font = `${test_name}/${font_format}/myfont-mod.ift.woff2?v=${rndNum}`;
    let title_text = document.getElementById(test_name).innerText;
    let font_name = font_format + '-' + test_name + '-IFT-Font';
    let fallback_font_name = 'RobotoFallback';
    el.style.fontFamily = `${font_name}, ${fallback_font_name}`;

    const testCase = document.getElementById(test_name);
    const assertSpans = testCase
      ? testCase.querySelectorAll(
          `.assert-result[data-test-id="${test_name}"][data-format="${font_format}"]`
        )
      : [];

    const key = patchKey(test_name, font_format);
    let snapshotBefore = new Set();
    if (assertSpans.length > 0) {
      initPatchObserver();
      drainObserverRecords();
      snapshotBefore = new Set(patchLoadsByTest.get(key) || []);
    }

    let fontLoaded = false;
    try {
      let f1 = await update_fonts(title_text, title_font, font_name, [], {});
      document.fonts.add(f1);
      fontLoaded = true;
    } catch (e) {
      console.error(`Error updating font for ${test_name} (${font_format}):`, e);
    }

    if (assertSpans.length > 0) {
      const barrier = await awaitRenderBarrier(test_name, font_format);
      const loadedNow = patchLoadsByTest.get(key) || new Set();
      const delta = new Set([...loadedNow].filter((p) => !snapshotBefore.has(p)));
      const state = {
        testId: test_name,
        format: font_format,
        fontName: font_name,
        prevText: title_text,
        lastRender: {
          fontLoaded,
          timedOut: barrier.timedOut,
          patchesDelta: delta,
          patchesLoaded: loadedNow,
          snapshotBefore,
        },
      };
      const ctx = buildAssertionContext(state);
      for (const span of assertSpans) {
        runAssertion(span, ctx);
      }
    }
  }
}

async function runRenderAction(item, state) {
  const { testId, format, fontName } = state;
  const key = patchKey(testId, format);

  drainObserverRecords();
  const snapshotBefore = new Set(patchLoadsByTest.get(key) || []);

  let fontLoaded = false;
  let loadError = null;
  try {
    const font = await extendSubset(
      testId,
      format,
      fontName,
      item.text,
      state.prevText
    );
    document.fonts.add(font);
    applyFontToSequenceRenders(testId, format, fontName);
    fontLoaded = true;
  } catch (e) {
    loadError = e;
    console.error(`Render failed for ${testId}/${format}:`, e);
  }

  const barrier = await awaitRenderBarrier(testId, format);

  const loadedNow = patchLoadsByTest.get(key) || new Set();
  const delta = new Set([...loadedNow].filter((p) => !snapshotBefore.has(p)));

  state.prevText = item.text;
  state.lastRender = {
    fontLoaded,
    loadError,
    timedOut: barrier.timedOut,
    patchesLoaded: loadedNow,
    patchesDelta: delta,
    snapshotBefore,
  };

  return state.lastRender;
}

async function run_sequence_tests() {
  const sequenceCases = document.querySelectorAll('.testCase.sequence');
  if (sequenceCases.length === 0) return;

  initPatchObserver();

  for (const testCase of sequenceCases) {
    const testId = testCase.id;
    const detailsBlocks = testCase.querySelectorAll('.testCaseDetails[data-format]');

    for (const details of detailsBlocks) {
      const format = details.getAttribute('data-format');
      const fontName = `${format}-${testId}-IFT-Font`;
      const state = {
        testId,
        format,
        fontName,
        prevText: '',
        lastRender: null,
      };

      // Ligature P/F check uses the subsetted visual font (separate FontFace).
      await loadSequenceLigatureResult(testId, format);

      const items = [
        ...details.querySelectorAll('.sequence-item'),
      ].sort(
        (a, b) =>
          Number(a.getAttribute('data-seq-index')) -
          Number(b.getAttribute('data-seq-index'))
      );

      for (const itemEl of items) {
        if (itemEl.classList.contains('sequence-render')) {
          const textEl = itemEl.querySelector('.render-text');
          const text = textEl ? textEl.textContent : '';
          await runRenderAction({ text }, state);
        } else if (itemEl.classList.contains('sequence-assert')) {
          const span = itemEl.querySelector('.assert-result');
          if (!span) continue;
          const ctx = buildAssertionContext(state);
          runAssertion(span, ctx);
        }
      }
    }
  }
}

window.addEventListener('DOMContentLoaded', function () {
  init().then(async function (Module) {
    window.ift_memory = Module.memory;
    const hasPatchAsserts =
      document.getElementsByClassName('assert-result').length > 0;
    if (hasPatchAsserts) {
      initPatchObserver();
    }
    await update_legacy_result_tests();
    await run_sequence_tests();
  });
});
