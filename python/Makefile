PYTHON ?= python3
SOURCES = main.py common.py tokenizer.py preprocess.py parse.py type.py constexpr.py codegen.py unicode.py hashmap.py LICENSE
ARCHIVE = build/chibicc.pyz
HEADERS = $(wildcard include/*.h)

all: check $(ARCHIVE)

check:
	$(PYTHON) -W error -m py_compile $(filter %.py,$(SOURCES)) build.py thirdparty.py test.py

$(ARCHIVE): build.py $(SOURCES) $(HEADERS)
	$(PYTHON) build.py -o $@

test:
	$(PYTHON) test.py

test-stage2: $(ARCHIVE)
	$(PYTHON) test.py --compiler $(ARCHIVE)

test-all: check test test-stage2

.PHONY: all check test test-stage2 test-all
