SHELL=/bin/bash
SHELLOPTS=braceexpand:emacs:hashall:histexpand:history:interactive-comments:monitor
BAZEL_OPTS = -c opt --copt=-DABSL_MIN_LOG_LEVEL=absl::LogSeverity::kInfo

all: fonts

fonts: fonts/roboto/Roboto-IFT.woff2 

always:


fonts/roboto/Roboto-IFT.woff2: build/Roboto-Preprocessed.ttf config/roboto_segmentation_plan.txtpb
	mkdir -p fonts/roboto
	bazel run $(BAZEL_OPTS) @ift_encoder//util:font2ift -- \
		--input_font=$(CURDIR)/build/Roboto-Preprocessed.ttf \
		--plan=$(CURDIR)/config/roboto_segmentation_plan.txtpb \
		--output_path=$(CURDIR)/fonts/roboto \
		--output_font="Roboto-IFT.woff2"

build/Roboto-Preprocessed.ttf: original_fonts/Roboto[wdth,wght].ttf
	bazel run $(BAZEL_OPTS) @harfbuzz//:hb-subset -- $(CURDIR)/original_fonts/Roboto[wdth,wght].ttf \
		--keep-everything \
		--no-hinting \
		-o $(CURDIR)/build/Roboto-Preprocessed.ttf

config/roboto_segmentation_plan.txtpb: build/Roboto-Preprocessed.ttf config/roboto_segmentation_config.txtpb
	bazel run $(BAZEL_OPTS) @ift_encoder//util:closure_glyph_keyed_segmenter_util -- \
	      --input_font=$(CURDIR)/build/Roboto-Preprocessed.ttf \
	      --config=$(CURDIR)/config/roboto_segmentation_config.txtpb \
	      --nooutput_segmentation_analysis \
	      --include_initial_codepoints_in_config \
	      --output_segmentation_plan > $(CURDIR)/config/roboto_segmentation_plan.txtpb

clean: 
	rm -f build/*
	rm -rf fonts/*
