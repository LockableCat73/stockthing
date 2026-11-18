/*
 * pineapple.c - optimal preflop discard for Pineapple (3 hole cards, discard 1 before the flop,
 * then play as Hold'em; everyone sees the flop).
 *
 *   ./pineapple discard NPLAYERS TRIALS [OPP_STRATEGY_CSV]
 *
 * For each of the 1755 suit-isomorphic 3-card classes, deals TRIALS random deals and, using the
 * SAME deal (common random numbers), evaluates all three possible discards to showdown against
 * NPLAYERS-1 opponents. Opponents also hold 3 cards and discard: randomly if no strategy file is
 * given, else according to the strategy (class,drop) from a previous iteration.
 * The discarded card is dead (it is never dealt to the board).
 *
 * Output CSV: class,cards,combos,eq_drop0,eq_drop1,eq_drop2,strong0,strong1,strong2
 *   where card i is the i-th card of `cards` and strongX = share of pot won with trips or better.
 */
#include "common.h"
#include <omp.h>

#define NKEY (52 * 52 * 52)
static int16_t key_class[NKEY];  /* sorted-desc key -> class */
static int8_t key_perm[NKEY];    /* suit permutation index that canonicalises it */
static int PERMS[24][4];
static int NCLASS = 0;
static int CREP[2000][3], CCOMBOS[2000];
static int8_t DROP[2000];        /* strategy: index into CREP of the card to discard */
static int8_t DROPCARD_KEY_OK = 0;
static int drop_card_for_key[NKEY];

static inline int mkkey(int a, int b, int c) { return a * 2704 + b * 52 + c; }
static void sort3desc(int *x) {
    if (x[0] < x[1]) { int t = x[0]; x[0] = x[1]; x[1] = t; }
    if (x[1] < x[2]) { int t = x[1]; x[1] = x[2]; x[2] = t; }
    if (x[0] < x[1]) { int t = x[0]; x[0] = x[1]; x[1] = t; }
}
static inline int applyp(int p, int c) { return RANK(c) * 4 + PERMS[p][SUIT(c)]; }

static void init_classes(void) {
    int np = 0;
    for (int a = 0; a < 4; a++) for (int b = 0; b < 4; b++) for (int c = 0; c < 4; c++) for (int d = 0; d < 4; d++)
        if (a != b && a != c && a != d && b != c && b != d && c != d) {
            PERMS[np][0] = a; PERMS[np][1] = b; PERMS[np][2] = c; PERMS[np][3] = d; np++;
        }
    static int canon_to_class[NKEY];
    for (int i = 0; i < NKEY; i++) { canon_to_class[i] = -1; key_class[i] = -1; }
    for (int a = 0; a < 52; a++) for (int b = 0; b < a; b++) for (int c = 0; c < b; c++) {
        int best = 1 << 30, bp = 0;
        for (int p = 0; p < 24; p++) {
            int x[3] = {applyp(p, a), applyp(p, b), applyp(p, c)}; sort3desc(x);
            int k = mkkey(x[0], x[1], x[2]);
            if (k < best) { best = k; bp = p; }
        }
        if (canon_to_class[best] < 0) {
            canon_to_class[best] = NCLASS;
            CREP[NCLASS][0] = best / 2704; CREP[NCLASS][1] = (best / 52) % 52; CREP[NCLASS][2] = best % 52;
            CCOMBOS[NCLASS] = 0; NCLASS++;
        }
        int k = mkkey(a, b, c);
        key_class[k] = (int16_t)canon_to_class[best]; key_perm[k] = (int8_t)bp;
        CCOMBOS[canon_to_class[best]]++;
    }
}

/* actual card to drop for the (sorted-desc) combo a>b>c under the current DROP strategy */
static void build_drop_cards(void) {
    for (int a = 0; a < 52; a++) for (int b = 0; b < a; b++) for (int c = 0; c < b; c++) {
        int k = mkkey(a, b, c), cl = key_class[k], p = key_perm[k];
        int target = CREP[cl][DROP[cl]];
        int cards[3] = {a, b, c}, res = -1;
        for (int i = 0; i < 3; i++) if (applyp(p, cards[i]) == target) res = cards[i];
        drop_card_for_key[k] = res;
    }
    DROPCARD_KEY_OK = 1;
}
static inline int opp_drop(rng_t *r, const int *h3) {
    if (!DROPCARD_KEY_OK) return h3[rbelow(r, 3)];
    int x[3] = {h3[0], h3[1], h3[2]}; sort3desc(x);
    return drop_card_for_key[mkkey(x[0], x[1], x[2])];
}

static void cardstr(int c, char *o) { o[0] = RANKCH[RANK(c)]; o[1] = SUITCH[SUIT(c)]; o[2] = 0; }

int main(int argc, char **argv) {
    init_tables(); init_classes();
    if (argc < 4 || strcmp(argv[1], "discard")) { fprintf(stderr, "usage: see header\n"); return 1; }
    int np = atoi(argv[2]); long trials = atol(argv[3]);
    if (argc >= 5) {
        FILE *f = fopen(argv[4], "r"); if (!f) { perror("strategy"); return 1; }
        int cl, d; char line[256];
        while (fgets(line, sizeof line, f)) if (sscanf(line, "%d,%d", &cl, &d) == 2) DROP[cl] = (int8_t)d;
        fclose(f); build_drop_cards();
    }
    static double EQ[2000][3], ST[2000][3];
    #pragma omp parallel for schedule(dynamic)
    for (int cl = 0; cl < NCLASS; cl++) {
        rng_t r; rseed(&r, 99991ULL * cl + np * 7 + (argc >= 5 ? 1000 : 0));
        int deck[52]; int n = build_deck(deck, CREP[cl], 3);
        int nopp = np - 1, need = nopp * 3 + 5;
        double eq[3] = {0}, st[3] = {0};
        int keep[3][2] = {{CREP[cl][1], CREP[cl][2]}, {CREP[cl][0], CREP[cl][2]}, {CREP[cl][0], CREP[cl][1]}};
        for (long t = 0; t < trials; t++) {
            shuffle_k(&r, deck, n, need);
            /* board = cards after opponents' hands; opponents' discards are simply never seen */
            const int *board = deck + nopp * 3;
            sm_t bm; sm_clear(&bm); for (int i = 0; i < 5; i++) sm_add(&bm, board[i]);
            uint32_t best = 0; int nbest = 0;
            for (int p = 0; p < nopp; p++) {
                const int *h3 = deck + 3 * p; int d = opp_drop(&r, h3);
                sm_t m = bm; for (int i = 0; i < 3; i++) if (h3[i] != d) sm_add(&m, h3[i]);
                uint32_t v = sm_eval(m);
                if (v > best) { best = v; nbest = 1; } else if (v == best) nbest++;
            }
            for (int k = 0; k < 3; k++) {
                sm_t m = bm; sm_add(&m, keep[k][0]); sm_add(&m, keep[k][1]);
                uint32_t v = sm_eval(m); double s = 0;
                if (v > best) s = 1; else if (v == best) s = 1.0 / (nbest + 1);
                eq[k] += s; if (CAT(v) >= TRIPS) st[k] += s;
            }
        }
        for (int k = 0; k < 3; k++) { EQ[cl][k] = eq[k] / trials; ST[cl][k] = st[k] / trials; }
    }
    printf("class,cards,combos,eq_drop0,eq_drop1,eq_drop2,strong0,strong1,strong2\n");
    for (int cl = 0; cl < NCLASS; cl++) {
        char a[3], b[3], c[3]; cardstr(CREP[cl][0], a); cardstr(CREP[cl][1], b); cardstr(CREP[cl][2], c);
        printf("%d,%s%s%s,%d,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f\n", cl, a, b, c, CCOMBOS[cl],
               EQ[cl][0], EQ[cl][1], EQ[cl][2], ST[cl][0], ST[cl][1], ST[cl][2]);
    }
    return 0;
}
