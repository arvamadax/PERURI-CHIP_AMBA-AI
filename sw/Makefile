CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -std=c11 -D_GNU_SOURCE

# host-test: tes software + penjaga nonce di PC. demo: build untuk board (CC=arm-linux-gnueabihf-gcc).
host-test: test_host
	./test_host

test_host: test_host.c ascon_soft.c ascon_hps.c
	$(CC) $(CFLAGS) -o $@ $^

ascon_demo: ascon_demo.c ascon_soft.c ascon_hps.c
	$(CC) $(CFLAGS) -o $@ $^

clean:
	rm -f test_host ascon_demo
.PHONY: host-test clean
