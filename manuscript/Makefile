# Build the manuscript PDF.
#
#   make            manuscript_npj.pdf via latexmk (preferred)
#   make clean      remove build artefacts
#   make figures    regenerate the figures from results/ before building
#
# latexmk resolves the bibtex/latex passes itself. If you only have a bare TeX
# installation, `make manual` runs the four passes by hand.

TEX  := manuscript_npj
BIB  := references.bib
DEPS := $(TEX).tex $(BIB) $(wildcard figures/*.pdf)

.PHONY: all clean figures references manual check

all: $(TEX).pdf

$(TEX).pdf: $(DEPS)
	latexmk -pdf -interaction=nonstopmode -halt-on-error $(TEX).tex

manual: $(DEPS)
	pdflatex -interaction=nonstopmode $(TEX).tex
	bibtex $(TEX)
	pdflatex -interaction=nonstopmode $(TEX).tex
	pdflatex -interaction=nonstopmode $(TEX).tex

figures:
	cd .. && python3 scripts/08_figures.py

references:
	cd .. && python3 scripts/check_references.py

# Fails if the manuscript cites a key references.bib does not define.
check: $(TEX).tex $(BIB)
	cd .. && python3 scripts/check_citations.py

clean:
	latexmk -C $(TEX).tex 2>/dev/null || true
	rm -f $(TEX).aux $(TEX).bbl $(TEX).blg $(TEX).log $(TEX).out $(TEX).fdb_latexmk $(TEX).fls
