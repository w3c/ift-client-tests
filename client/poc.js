import init, { IftState } from './rust-client/pkg/rust_client.js';

let states = {};

async function update_all_fonts() {
  let title_font = "fonts/roboto/myfont.ift.ttf";
  let title_text = document.getElementById("title_ur").innerText;
  let p1 = update_fonts(title_text,
    title_font,
    "Roboto IFT Font",
    [],
    {});
  let f1 = await p1;
  // document.fonts.clear();
  document.fonts.add(f1);
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
