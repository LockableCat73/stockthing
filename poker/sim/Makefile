CC ?= gcc
CFLAGS ?= -O3 -march=native -fopenmp -Wall -Wno-unused-variable
BINS = test_eval preflop pineapple cats omaha_pre texture

all: $(BINS)

%: %.c common.h codes.h pineclass.h
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f $(BINS)

.PHONY: all clean
