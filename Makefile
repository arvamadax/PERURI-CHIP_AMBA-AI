.PHONY: test clean
test:
	$(MAKE) -C sim

clean:
	$(MAKE) -C sim clean
	rm -rf sim/results.xml sim/__pycache__ model/__pycache__
