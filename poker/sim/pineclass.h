/* pineclass.h - suit-isomorphic classes of 3-card Pineapple hands and a discard strategy table.
 * Shared by pineapple.c and cats.c. */
#ifndef PINECLASS_H
#define PINECLASS_H
#include "common.h"
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


static int load_drop_strategy(const char *path) {
    FILE *f = fopen(path, "r"); if (!f) { perror(path); return 0; }
    int cl, d; char line[256];
    while (fgets(line, sizeof line, f)) if (sscanf(line, "%d,%d", &cl, &d) == 2) DROP[cl] = (int8_t)d;
    fclose(f); build_drop_cards(); return 1;
}
#endif
