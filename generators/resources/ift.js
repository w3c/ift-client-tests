// Native IFT is the default. Add ?wasm=1 to opt into the polyfill.
const useWasm = new URLSearchParams(window.location.search).get('wasm') === '1';
let wasmClient;
const states = new Map();

async function init_wasm() {
  const { default: init, IftState } = await import('./rust-client/pkg/rust_client.js');
  await new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = new URL('./cc-client/brotli.js', import.meta.url).href;
    script.onload = resolve;
    script.onerror = () => reject(new Error('Failed to load the WASM WOFF2 decoder'));
    document.head.appendChild(script);
  });
  const [module, decoder] = await Promise.all([init(), window.createModule()]);
  wasmClient = { IftState, memory: module.memory, Woff2Decoder: decoder.Woff2Decoder };
}

async function load_wasm_font(text, font_url, font_name) {
  if (!states.has(font_url)) {
    states.set(font_url, wasmClient.IftState.new(font_url));
  }
  const state = states.get(font_url);
  const codepoints = [...new Set(Array.from(text, character => character.codePointAt(0)))];
  state.add_to_target_subset_definition(codepoints);
  const subset = await state.current_font_subset({
    unwoff2: encoded => new wasmClient.Woff2Decoder(encoded).data(),
  });
  const data = new Uint8Array(wasmClient.memory.buffer, subset.data(), subset.len());
  return new FontFace(font_name, data).load();
}

async function update_all_wasm_fonts() {
  const resultElements = document.getElementsByClassName('result');
  for (const el of resultElements) {
    const test_name = el.id.replace(/^[^-]+-/, '');
    console.log('Processing test:', test_name);
    const font_format = el.getAttribute('data-format');
    const rndNum = Math.floor(Math.random() * 100000);
    const font_url = `${test_name}/${font_format}/myfont-mod.ift.woff2?v=${rndNum}`;
    const font_name = `${font_format}-${test_name}-IFT-Font`;
    const test = document.getElementById(test_name);
    el.style.fontFamily = `${font_name}, RobotoFallback`;
    // Keep extra test text associated with this format's font.
    for (const target of test.querySelectorAll(`[data-ift-format="${font_format}"]`)) {
      target.style.fontFamily = el.style.fontFamily;
    }
    try {
      document.fonts.add(await load_wasm_font(test.innerText, font_url, font_name));
    } catch (error) {
      console.error(`Error updating font for ${test_name} (${font_format}):`, error);
    }
  }
}

window.addEventListener('DOMContentLoaded', async () => {
  try {
    if (useWasm) {
      await init_wasm();
      await update_all_wasm_fonts();
    } else {
      // CSS handles native font loading, font matching, and patch requests.
      const stylesheet = document.createElement('link');
      stylesheet.rel = 'stylesheet';
      stylesheet.href = new URL('./native-ift.css', import.meta.url).href;
      document.head.appendChild(stylesheet);
    }
    console.log(`IFT loader: ${useWasm ? 'WASM polyfill' : 'native browser'}`);
  } catch (error) {
    console.error('Failed to initialize the IFT loader:', error);
  }
});
