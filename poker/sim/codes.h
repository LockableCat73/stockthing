/* codes.h - helpers and Hold'em/Pineapple flop/turn hand classification shared by cats.c and texture.c */
#ifndef CODES_H
#define CODES_H
#include "common.h"
/* ------------------------------------------------------------ helpers */
static inline int top_missing(int s, const int *board, int nb) {
    uint32_t m = 0; for (int i = 0; i < nb; i++) if (SUIT(board[i]) == s) m |= 1u << RANK(board[i]);
    for (int r = 12; r >= 0; r--) if (!(m & (1u << r))) return r;
    return -1;
}
static inline int holds(const int *h, int nh, int rank, int suit) {
    for (int i = 0; i < nh; i++) if (RANK(h[i]) == rank && SUIT(h[i]) == suit) return 1;
    return 0;
}
/* highest straight (high rank) that can be made using >= `need` ranks from board mask BR */
static inline int best_board_straight(uint32_t BR, int need) {
    for (int hi = 12; hi >= 3; hi--) {
        uint32_t w = hi >= 4 ? (0x1Fu << (hi - 4)) : 0x100Fu;
        if (__builtin_popcount(BR & w) >= need) return hi;
    }
    return -1;
}
static void board_info(const int *b, int nb, int *cnt, int *d, int *nd, uint32_t *BR) {
    memset(cnt, 0, 13 * sizeof(int)); *BR = 0;
    for (int i = 0; i < nb; i++) { cnt[RANK(b[i])]++; *BR |= 1u << RANK(b[i]); }
    *nd = 0; for (int r = 12; r >= 0; r--) if (cnt[r]) d[(*nd)++] = r;
}

/* ------------------------------------------------ Hold'em / Pineapple */
static const char *HM_NAMES[] = {"nothing", "weak pair", "middle pair", "top pair weak kicker",
    "top pair good kicker (J+)", "overpair", "two pair", "trips (board pair)", "set", "straight",
    "nut straight", "flush", "nut flush", "full house+"};
static const char *HD_NAMES[] = {"no draw", "gutshot", "OESD", "flush draw", "nut flush draw",
    "flush draw + straight draw"};

static int holdem_code(const int *h, const int *b, int nb, uint32_t v, int *draw) {
    int cnt[13], d[5], nd; uint32_t BR; board_info(b, nb, cnt, d, &nd, &BR);
    int cat = CAT(v), made; *draw = 0;
    if (cat >= FULLHOUSE) return 13;
    if (cat == FLUSH) {
        int s = -1; for (int k = 0; k < 4; k++) { int c = 0; for (int i = 0; i < nb; i++) c += SUIT(b[i]) == k; if (c >= 3) s = k; }
        if (s < 0) return 11;
        return holds(h, 2, top_missing(s, b, nb), s) ? 12 : 11;
    }
    if (cat == STRAIGHT) return ((int)((v >> 16) & 15) == best_board_straight(BR, 3)) ? 10 : 9;
    int r0 = RANK(h[0]), r1 = RANK(h[1]);
    if (r0 < r1) { int t = r0; r0 = r1; r1 = t; }
    if (r0 == r1) {
        if (cnt[r0] >= 1) made = 8;
        else if (r0 > d[0]) made = 5;
        else if (nd > 1 && r0 > d[1]) made = 2;
        else made = 1;
    } else if (cnt[r0] >= 2 || cnt[r1] >= 2) made = 7;
    else if (cnt[r0] && cnt[r1]) made = 6;
    else if (cnt[r0] || cnt[r1]) {
        int m = cnt[r0] ? r0 : r1, k = cnt[r0] ? r1 : r0;
        if (m == d[0]) made = k >= 9 ? 4 : 3;
        else if (nd > 1 && m == d[1]) made = 2;
        else made = 1;
    } else made = 0;
    /* draws */
    int fd = 0;
    for (int hi = 0; hi < 2; hi++) {
        int s = SUIT(h[hi]); if (hi == 1 && SUIT(h[0]) == s) continue;
        int c = (SUIT(h[0]) == s) + (SUIT(h[1]) == s);
        for (int i = 0; i < nb; i++) c += SUIT(b[i]) == s;
        if (c == 4) { int nut = holds(h, 2, top_missing(s, b, nb), s) ? 2 : 1; if (nut > fd) fd = nut; }
    }
    uint32_t all = BR | (1u << r0) | (1u << r1); int so = 0;
    for (int r = 0; r < 13; r++)
        if (!(all & (1u << r)) && STR[all | (1u << r)] && !STR[BR | (1u << r)]) so++;
    int sd = so >= 2 ? 2 : so;
    if (fd && sd) *draw = 5; else if (fd) *draw = 2 + fd; else *draw = sd;
    return made;
}

#endif
