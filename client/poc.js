import init, { IftState } from './rust-client/pkg/rust_client.js';

let states = {};

async function update_all_fonts() {
  /* TODO: 
  get all result elements by class name
  for each element in result elements
    grab the test name from the element id or class or a data atribute.
    get font path from test name
    get font family name from test name
    create new FontFace object with path and font family name
    add "style" attribute to element referencing the font family name
  */
  // Get all elements with class 'result'
  const resultElements = document.getElementsByClassName('result');
  for (let el of resultElements) {
    let test_name = el.id; // "conform-format1-valid-format-number";
    let title_font = `fonts/ift/${test_name}/myfont-mod.ift.otf`;
    let title_text = document.getElementById(test_name).innerText;
    let font_name = test_name + " IFT Font";
    el.style.fontFamily = `${font_name}, "RobotoFallbackPass"`;
    let p1 = update_fonts(title_text,
      title_font,
      font_name,
      [],
      {});
    let f1 = await p1;
    document.fonts.add(f1);
    console.log('Found result element:', el);
  }
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

const woff2_decoder = {
  unwoff2: (encoded) => {
    let decoder = new window.Woff2Decoder(encoded);
    return decoder.data();
  }
}

function patch_codepoints(font_id, font_face, cps, features, axes) {
  if (!states[font_id]) {
    states[font_id] = IftState.new(font_id);
  }
  let state = states[font_id];

  // TODO(garretrieger): check return values of add_* methods and don't update the font
  //                     if no changes are made.

  for (const [tag, point] of axes) {
    state.add_design_space_to_target_subset_definition(tag, point, point);
  }

  for (const tag of features) {
    state.add_feature_to_target_subset_definition(tag);
  }

  state.add_to_target_subset_definition(cps);
  return state.current_font_subset(woff2_decoder).then(font => {
    const font_data = new Uint8Array(window.ift_memory.buffer, font.data(), font.len());
    let descriptor = {};
    if (font_id.includes("Roboto")) {
      descriptor = {
        weight: "100 900",
        stretch: "75% 100%"
      };
    } else if (font_id.includes("NotoSerif")) {
      descriptor = {
        weight: "900",
      };
    } else if (font_id.includes("NotoSans")) {
      descriptor = {
        weight: "100 900",
      };
    }
    font = new FontFace(font_face, font_data, descriptor);
    return font.load();
  })
}


window.addEventListener('DOMContentLoaded', function () {
  init().then(function (Module) {
    window.ift_memory = Module.memory;
    update_all_fonts();
  });
});
