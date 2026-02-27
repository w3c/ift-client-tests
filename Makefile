SHELL=/bin/bash
SHELLOPTS=braceexpand:emacs:hashall:histexpand:history:interactive-comments:monitor
BAZEL_OPTS = -c opt --copt=-DABSL_MIN_LOG_LEVEL=absl::LogSeverity::kInfo

.PHONY: all clean tests

all: test-coverage-report.txt tests

test-coverage-report.txt: spec/Overview.html IFTClient/Tests/xhtml1/index.html
	python3 check_coverage.py spec/Overview.html IFTClient/Tests/xhtml1/index.html  > test-coverage-report.txt

tests: IFTClient/Tests/xhtml1/index.html

IFTClient/Tests/xhtml1/index.html: \
	build/IFT/GLYF/font.ift.woff2 build/IFT/CFF/font.ift.woff2 \
	build/subsettedFonts/cff-fallback.otf build/subsettedFonts/glyf-fallback.ttf
	cd generators/; python3 ./ClientTestCaseGenerator.py

build/subsettedFonts/cff-ift.otf build/subsettedFonts/glyf-ift.ttf &: generators/sourceFonts/cff.otf  generators/sourceFonts/glyf.ttf
	mkdir -p build/subsettedFonts/
	cd generators/; python3 ./makeSubsettedFont.py ift

build/subsettedFonts/cff-fallback.otf build/subsettedFonts/glyf-fallback.ttf &: generators/sourceFonts/cff.otf  generators/sourceFonts/glyf.ttf
	mkdir -p build/subsettedFonts/
	cd generators/; python3 ./makeSubsettedFont.py fallback

build/config/glyf_segmentation_plan.txtpb: build/subsettedFonts/glyf-ift.ttf encoder/config/segmentation_config.txtpb
	mkdir -p build/config/
	cd encoder; bazel run $(BAZEL_OPTS) @ift_encoder//util:closure_glyph_keyed_segmenter_util -- \
	      --input_font=$(CURDIR)/build/subsettedFonts/glyf-ift.ttf \
	      --config=$(CURDIR)/encoder/config/segmentation_config.txtpb \
	      --nooutput_segmentation_analysis \
	      --include_initial_codepoints_in_config \
	      --output_segmentation_plan > $(CURDIR)/build/config/glyf_segmentation_plan.txtpb

build/config/cff_segmentation_plan.txtpb: build/subsettedFonts/cff-ift.otf encoder/config/segmentation_config.txtpb
	mkdir -p build/config/
	cd encoder; bazel run $(BAZEL_OPTS) @ift_encoder//util:closure_glyph_keyed_segmenter_util -- \
	      --input_font=$(CURDIR)/build/subsettedFonts/cff-ift.otf \
	      --config=$(CURDIR)/encoder/config/segmentation_config.txtpb \
	      --nooutput_segmentation_analysis \
	      --include_initial_codepoints_in_config \
	      --output_segmentation_plan > $(CURDIR)/build/config/cff_segmentation_plan.txtpb

build/IFT/GLYF/font.ift.woff2: build/config/glyf_segmentation_plan.txtpb build/subsettedFonts/glyf-ift.ttf
	mkdir -p build/IFT/GLYF
	cd encoder; bazel run $(BAZEL_OPTS) @ift_encoder//util:font2ift -- \
		--input_font=$(CURDIR)/build/subsettedFonts/glyf-ift.ttf \
		--plan=$(CURDIR)/build/config/glyf_segmentation_plan.txtpb \
		--output_path=$(CURDIR)/build/IFT/GLYF \
		--output_font="font.ift.woff2"

build/IFT/CFF/font.ift.woff2: build/config/cff_segmentation_plan.txtpb build/subsettedFonts/cff-ift.otf
	mkdir -p build/IFT/CFF
	cd encoder; bazel run $(BAZEL_OPTS) @ift_encoder//util:font2ift -- \
		--input_font=$(CURDIR)/build/subsettedFonts/cff-ift.otf \
		--plan=$(CURDIR)/build/config/cff_segmentation_plan.txtpb \
		--output_path=$(CURDIR)/build/IFT/CFF \
		--output_font="font.ift.woff2"

clean:
	rm -f test-coverage-report.txt
	rm -rf build/
	rm -rf IFTClient/

