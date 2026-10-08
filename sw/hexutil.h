#ifndef HEXUTIL_H
#define HEXUTIL_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

static inline size_t hexbin(const char *h, uint8_t *out) {
    size_t n = strlen(h) / 2;
    for (size_t i = 0; i < n; i++) {
        unsigned v = 0;
        for (int j = 0; j < 2; j++) {
            char c = h[2 * i + j];
            v = v << 4 | (unsigned)(c <= '9' ? c - '0' : (c | 0x20) - 'a' + 10);
        }
        out[i] = (uint8_t)v;
    }
    return n;
}
#endif
