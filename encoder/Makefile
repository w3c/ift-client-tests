SHELL=/bin/bash
SHELLOPTS=braceexpand:emacs:hashall:histexpand:history:interactive-comments:monitor
BAZEL_OPTS = -c opt --copt=-DABSL_MIN_LOG_LEVEL=absl::LogSeverity::kInfo

all: fonts

fonts: glyf-ift cff-ift

always:

# TODO: add subdirectory to IFT directory for each type of font and update "fonts:" to include CFF
glyf-ift: build/glyf-Preprocessed.ttf config/glyf_segmentation_plan.txtpb
	mkdir -p $(CURDIR)/../generators/resources/IFT/GLYF
	bazel run $(BAZEL_OPTS) @ift_encoder//util:font2ift -- \
		--input_font=$(CURDIR)/build/glyf-Preprocessed.ttf \
		--plan=$(CURDIR)/config/glyf_segmentation_plan.txtpb \
		--output_path=$(CURDIR)/../generators/resources/IFT/GLYF \
		--output_font="font.ift.woff2"

build/glyf-Preprocessed.ttf: ../generators/subsettedFonts/glyf-ift.ttf
	bazel run $(BAZEL_OPTS) @harfbuzz//:hb-subset -- $(CURDIR)/../generators/subsettedFonts/glyf-ift.ttf \
		--keep-everything \
		--no-hinting \
		-o $(CURDIR)/build/glyf-Preprocessed.ttf

config/glyf_segmentation_plan.txtpb: build/glyf-Preprocessed.ttf config/segmentation_config.txtpb
	bazel run $(BAZEL_OPTS) @ift_encoder//util:closure_glyph_keyed_segmenter_util -- \
	      --input_font=$(CURDIR)/build/glyf-Preprocessed.ttf \
	      --config=$(CURDIR)/config/segmentation_config.txtpb \
	      --nooutput_segmentation_analysis \
	      --include_initial_codepoints_in_config \
	      --output_segmentation_plan > $(CURDIR)/config/glyf_segmentation_plan.txtpb

# cff
cff-ift: build/cff-Preprocessed.ttf config/cff_segmentation_plan.txtpb
	mkdir -p $(CURDIR)/../generators/resources/IFT/CFF
	bazel run $(BAZEL_OPTS) @ift_encoder//util:font2ift -- \
		--input_font=$(CURDIR)/build/cff-Preprocessed.ttf \
		--plan=$(CURDIR)/config/cff_segmentation_plan.txtpb \
		--output_path=$(CURDIR)/../generators/resources/IFT/CFF \
		--output_font="font.ift.woff2"

build/cff-Preprocessed.ttf: ../generators/subsettedFonts/cff-ift.otf
	bazel run $(BAZEL_OPTS) @harfbuzz//:hb-subset -- $(CURDIR)/../generators/subsettedFonts/cff-ift.otf \
		--keep-everything \
		--no-hinting \
		-o $(CURDIR)/build/cff-Preprocessed.ttf

config/cff_segmentation_plan.txtpb: build/cff-Preprocessed.ttf config/segmentation_config.txtpb
	bazel run $(BAZEL_OPTS) @ift_encoder//util:closure_glyph_keyed_segmenter_util -- \
	      --input_font=$(CURDIR)/build/cff-Preprocessed.ttf \
	      --config=$(CURDIR)/config/segmentation_config.txtpb \
	      --nooutput_segmentation_analysis \
	      --include_initial_codepoints_in_config \
	      --output_segmentation_plan > $(CURDIR)/config/cff_segmentation_plan.txtpb

clean: 
	rm -f build/*
	rm -rf ../generators/resources/IFT/*
