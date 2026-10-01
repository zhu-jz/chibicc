PYTHON ?= python3
SOURCES = main.py common.py tokenizer.py preprocess.py parse.py type.py constexpr.py codegen.py LICENSE
ARCHIVE = build/chibicc.pyz

all: $(ARCHIVE)

$(ARCHIVE): build.py $(SOURCES)
	$(PYTHON) build.py -o $@

test:
	$(PYTHON) test.py

test-stage2: $(ARCHIVE)
	$(PYTHON) test.py --compiler $(ARCHIVE)

test-all: test test-stage2

.PHONY: all test test-stage2 test-all
