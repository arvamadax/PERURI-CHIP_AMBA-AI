SIM ?= icarus
TOP ?= ascon_round
TESTMOD ?= test_round
UNROLL ?= 1
TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(wildcard $(CURDIR)/../rtl/*.v) $(wildcard $(CURDIR)/tb_*.v)
COCOTB_TOPLEVEL = $(TOP)
COCOTB_TEST_MODULES = $(TESTMOD)
SIM_BUILD = sim_build/$(TOP)_u$(UNROLL)
COCOTB_RESULTS_FILE = results_$(TOP)_u$(UNROLL).xml
ifneq ($(filter ascon_perm tb_ctrl ascon_top,$(TOP)),)
COMPILE_ARGS += -P$(TOP).UNROLL=$(UNROLL)
endif
export UNROLL
export PYTHONPATH := $(CURDIR)/../model:$(PYTHONPATH)
include $(shell cocotb-config --makefiles)/Makefile.sim
