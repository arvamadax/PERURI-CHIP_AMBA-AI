.PHONY: all model sim clean
all: model sim

model:
	cd model && python -m pytest -q

sim:
	$(MAKE) -C sim

clean:
	$(MAKE) -C sim clean
	rm -rf sim/results.xml sim/__pycache__ model/__pycache__ model/.pytest_cache
