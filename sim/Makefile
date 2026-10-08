SIM ?= icarus
TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(CURDIR)/../rtl/ascon_round.v
COCOTB_TOPLEVEL = ascon_round
COCOTB_TEST_MODULES = test_round
export PYTHONPATH := $(CURDIR)/../model:$(PYTHONPATH)
include $(shell cocotb-config --makefiles)/Makefile.sim
