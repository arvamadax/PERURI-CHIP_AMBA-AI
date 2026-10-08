.PHONY: all model sim cycles clean
UNROLLS = 1 2 4
SIMRUN = $(MAKE) -C sim

all: model sim

model:
	cd model && python -m pytest -q

sim:
	$(SIMRUN) TOP=ascon_round TESTMOD=test_round
	$(SIMRUN) TOP=tag_compare TESTMOD=test_tag_compare
	for u in $(UNROLLS); do $(SIMRUN) TOP=ascon_perm TESTMOD=test_ascon_perm UNROLL=$$u || exit 1; done
	for u in $(UNROLLS); do $(SIMRUN) TOP=tb_ctrl TESTMOD=test_ascon_ctrl UNROLL=$$u || exit 1; done

cycles:
	python sim/report_cycles.py

clean:
	rm -rf sim/sim_build sim/results*.xml sim/__pycache__ model/__pycache__ model/.pytest_cache
