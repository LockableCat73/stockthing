/*
 * common.h - shared hand evaluator, RNG and helpers for the poker simulators.
 *
 * Cards are ints 0..51: rank = c>>2 (0 = deuce ... 12 = ace), suit = c&3.
 * A hand value is a 32-bit int; larger is better.
 *   value = category<<20 | r1<<16 | r2<<12 | r3<<8 | r4<<4 | r5
 * Categories: 0 high card, 1 pair, 2 two pair, 3 trips, 4 straight,
 *             5 flush, 6 full house, 7 quads, 8 straight flush.
 */
#ifndef POKER_COMMON_H
#define POKER_COMMON_H

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RANK(c) ((c) >> 2)
#define SUIT(c) ((c) & 3)
#define CAT(v) ((v) >> 20)

enum { HC = 0, PAIR, TWOPAIR, TRIPS, STRAIGHT, FLUSH, FULLHOUSE, QUADS, STFLUSH };
static const char *CATNAME[9] = {"High card", "Pair", "Two pair", "Trips", "Straight",
                                 "Flush", "Full house", "Quads", "Straight flush"};
static const char RANKCH[13] = {'2','3','4','5','6','7','8','9','T','J','Q','K','A'};
static const char SUITCH[4] = {'c','d','h','s'};

/* ---------------------------------------------------------------- RNG */
typedef struct { uint64_t s[4]; } rng_t;
static inline uint64_t rotl64(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static inline uint64_t rnext(rng_t *r) {
    uint64_t *s = r->s;
    uint64_t res = rotl64(s[1] * 5, 7) * 9, t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl64(s[3], 45);
    return res;
}
static inline uint32_t rbelow(rng_t *r, uint32_t n) {
    return (uint32_t)(((rnext(r) >> 32) * (uint64_t)n) >> 32);
}
static inline void rseed(rng_t *r, uint64_t seed) {
    for (int i = 0; i < 4; i++) {
        uint64_t z = (seed += 0x9E3779B97F4A7C15ULL);
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        r->s[i] = z ^ (z >> 31);
    }
}
/* move k random elements of deck[0..n) into deck[0..k) (partial Fisher-Yates) */
static inline void shuffle_k(rng_t *r, int *deck, int n, int k) {
    for (int i = 0; i < k; i++) {
        int j = i + (int)rbelow(r, (uint32_t)(n - i));
        int t = deck[i]; deck[i] = deck[j]; deck[j] = t;
    }
}

/* ---------------------------------------------------------- evaluator */
static uint8_t STR[8192]; /* best straight high rank + 1, or 0 */

static void init_tables(void) {
    for (int m = 0; m < 8192; m++) {
        STR[m] = 0;
        for (int hi = 12; hi >= 4; hi--) {
            int w = 0x1F << (hi - 4);
            if ((m & w) == w) { STR[m] = (uint8_t)(hi + 1); break; }
        }
        if (!STR[m] && (m & 0x100F) == 0x100F) STR[m] = 4; /* wheel, high = 5 (rank 3) */
    }
}

static inline int topbit(uint32_t x) { return 31 - __builtin_clz(x); }
static inline uint32_t top_n(uint32_t m, int n) {
    uint32_t v = 0;
    for (int i = 0; i < n; i++) {
        v <<= 4;
        if (m) { int b = topbit(m); v |= (uint32_t)b; m &= ~(1u << b); }
    }
    return v;
}

/* evaluate the cards described by four 13-bit per-suit rank masks (any count 1..9) */
static inline uint32_t eval_sm(uint32_t s0, uint32_t s1, uint32_t s2, uint32_t s3) {
    uint32_t all = s0 | s1 | s2 | s3;
    uint32_t fl = 0;
    if (__builtin_popcount(s0) >= 5) fl = s0;
    else if (__builtin_popcount(s1) >= 5) fl = s1;
    else if (__builtin_popcount(s2) >= 5) fl = s2;
    else if (__builtin_popcount(s3) >= 5) fl = s3;
    if (fl) { int st = STR[fl]; if (st) return (STFLUSH << 20) | ((uint32_t)(st - 1) << 16); }
    uint32_t quads = s0 & s1 & s2 & s3;
    if (quads) {
        int q = topbit(quads);
        uint32_t rest = all & ~(1u << q);
        return (QUADS << 20) | ((uint32_t)q << 16) | (rest ? ((uint32_t)topbit(rest) << 12) : 0);
    }
    uint32_t t3 = (s0 & s1 & s2) | (s0 & s1 & s3) | (s0 & s2 & s3) | (s1 & s2 & s3);
    uint32_t p2 = (s0 & s1) | (s0 & s2) | (s0 & s3) | (s1 & s2) | (s1 & s3) | (s2 & s3);
    if (t3) {
        int t = topbit(t3);
        uint32_t rest = p2 & ~(1u << t);
        if (rest) return (FULLHOUSE << 20) | ((uint32_t)t << 16) | ((uint32_t)topbit(rest) << 12);
    }
    if (fl) return (FLUSH << 20) | top_n(fl, 5);
    { int st = STR[all]; if (st) return (STRAIGHT << 20) | ((uint32_t)(st - 1) << 16); }
    if (t3) {
        int t = topbit(t3);
        return (TRIPS << 20) | ((uint32_t)t << 16) | (top_n(all & ~(1u << t), 2) << 8);
    }
    if (p2) {
        int a = topbit(p2);
        uint32_t p2b = p2 & ~(1u << a);
        if (p2b) {
            int b = topbit(p2b);
            uint32_t rest = all & ~(1u << a) & ~(1u << b);
            return (TWOPAIR << 20) | ((uint32_t)a << 16) | ((uint32_t)b << 12) |
                   (rest ? ((uint32_t)topbit(rest) << 8) : 0);
        }
        return (PAIR << 20) | ((uint32_t)a << 16) | (top_n(all & ~(1u << a), 3) << 4);
    }
    return top_n(all, 5);
}

typedef struct { uint32_t s[4]; } sm_t;
static inline void sm_clear(sm_t *m) { m->s[0] = m->s[1] = m->s[2] = m->s[3] = 0; }
static inline void sm_add(sm_t *m, int c) { m->s[SUIT(c)] |= 1u << RANK(c); }
static inline sm_t sm_or(sm_t a, sm_t b) {
    sm_t r; r.s[0] = a.s[0] | b.s[0]; r.s[1] = a.s[1] | b.s[1];
    r.s[2] = a.s[2] | b.s[2]; r.s[3] = a.s[3] | b.s[3]; return r;
}
static inline uint32_t sm_eval(sm_t m) { return eval_sm(m.s[0], m.s[1], m.s[2], m.s[3]); }
static inline uint32_t eval_cards(const int *c, int n) {
    sm_t m; sm_clear(&m);
    for (int i = 0; i < n; i++) sm_add(&m, c[i]);
    return sm_eval(m);
}

/* ------------------------------------------------- variant evaluators */
/* Hold'em / Pineapple: best 5 of hole2 + board (nb cards) */
static inline uint32_t eval_holdem(const int *hole, const int *board, int nb) {
    sm_t m; sm_clear(&m);
    sm_add(&m, hole[0]); sm_add(&m, hole[1]);
    for (int i = 0; i < nb; i++) sm_add(&m, board[i]);
    return sm_eval(m);
}

/* Omaha: exactly 2 of 4 hole + exactly 3 of board (nb = 3,4,5) */
static const int OPAIR[6][2] = {{0,1},{0,2},{0,3},{1,2},{1,3},{2,3}};
static inline uint32_t eval_omaha(const int *hole, const int *board, int nb) {
    sm_t hp[6], bt[10];
    for (int i = 0; i < 6; i++) {
        sm_clear(&hp[i]); sm_add(&hp[i], hole[OPAIR[i][0]]); sm_add(&hp[i], hole[OPAIR[i][1]]);
    }
    int nt = 0;
    for (int a = 0; a < nb; a++)
        for (int b = a + 1; b < nb; b++)
            for (int c = b + 1; c < nb; c++) {
                sm_clear(&bt[nt]); sm_add(&bt[nt], board[a]); sm_add(&bt[nt], board[b]);
                sm_add(&bt[nt], board[c]); nt++;
            }
    uint32_t best = 0;
    for (int i = 0; i < 6; i++)
        for (int j = 0; j < nt; j++) {
            uint32_t v = sm_eval(sm_or(hp[i], bt[j]));
            if (v > best) best = v;
        }
    return best;
}

/* Tic-tac-toe grid:  0 1 2 / 3 4 5 / 6 7 8.  Flop = corners 0,2,6,8; turn = sides 1,3,5,7;
 * river = center 4.  A player uses both hole cards + the 3 cards of any complete line. */
static const int TLINE[8][3] = {{0,1,2},{3,4,5},{6,7,8},{0,3,6},{1,4,7},{2,5,8},{0,4,8},{2,4,6}};
static const int TTT_EDGE_LINES[4] = {0, 2, 3, 5};   /* complete after the turn */
static const int TTT_CENTER_LINES[4] = {1, 4, 6, 7}; /* complete after the river */
static inline uint32_t eval_ttt_line(const int *hole, const int *grid, int l) {
    sm_t m; sm_clear(&m);
    sm_add(&m, hole[0]); sm_add(&m, hole[1]);
    sm_add(&m, grid[TLINE[l][0]]); sm_add(&m, grid[TLINE[l][1]]); sm_add(&m, grid[TLINE[l][2]]);
    return sm_eval(m);
}
static inline uint32_t eval_ttt(const int *hole, const int *grid) {
    uint32_t best = 0;
    for (int l = 0; l < 8; l++) { uint32_t v = eval_ttt_line(hole, grid, l); if (v > best) best = v; }
    return best;
}
static inline uint32_t eval_ttt_edges(const int *hole, const int *grid) {
    uint32_t best = 0;
    for (int k = 0; k < 4; k++) {
        uint32_t v = eval_ttt_line(hole, grid, TTT_EDGE_LINES[k]); if (v > best) best = v;
    }
    return best;
}

/* -------------------------------------------------- 169 starting hands */
/* grid index g = i*13 + j with i,j = 12-rank (row 0 = aces). i==j pair, i<j suited, i>j offsuit */
static inline int class169(int c1, int c2) {
    int r1 = RANK(c1), r2 = RANK(c2);
    if (r1 < r2) { int t = r1; r1 = r2; r2 = t; }
    int i = 12 - r1, j = 12 - r2;
    if (r1 == r2) return i * 13 + i;
    if (SUIT(c1) == SUIT(c2)) return i * 13 + j; /* suited: upper triangle */
    return j * 13 + i;                           /* offsuit: lower triangle */
}
static inline void class169_rep(int g, int *c1, int *c2) {
    int i = g / 13, j = g % 13;
    if (i == j) { *c1 = (12 - i) * 4 + 0; *c2 = (12 - i) * 4 + 1; }
    else if (i < j) { *c1 = (12 - i) * 4 + 0; *c2 = (12 - j) * 4 + 0; }
    else { *c1 = (12 - j) * 4 + 0; *c2 = (12 - i) * 4 + 1; }
}
static inline void class169_name(int g, char *out) {
    int i = g / 13, j = g % 13;
    if (i == j) { out[0] = RANKCH[12 - i]; out[1] = RANKCH[12 - i]; out[2] = 0; }
    else if (i < j) { out[0] = RANKCH[12 - i]; out[1] = RANKCH[12 - j]; out[2] = 's'; out[3] = 0; }
    else { out[0] = RANKCH[12 - j]; out[1] = RANKCH[12 - i]; out[2] = 'o'; out[3] = 0; }
}
static inline int class169_combos(int g) { int i = g / 13, j = g % 13; return i == j ? 6 : (i < j ? 4 : 12); }

/* deck of all cards except those in `excl` (n_excl). returns size */
static inline int build_deck(int *deck, const int *excl, int n_excl) {
    int used[52] = {0}, n = 0;
    for (int i = 0; i < n_excl; i++) used[excl[i]] = 1;
    for (int c = 0; c < 52; c++) if (!used[c]) deck[n++] = c;
    return n;
}

#endif
