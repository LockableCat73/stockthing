/*
 * omaha_pre.c - Omaha starting-hand strength (no decisions preflop in this game, but it tells
 * you how strong you are going into the flop).
 *
 *   ./omaha_pre features NPLAYERS TRIALS   -> equity aggregated by hand features (every seat sampled)
 *   ./omaha_pre named NPLAYERS TRIALS H1 H2 ...   (hands like AsAhKsKh) -> equity of each hand
 */
#include "common.h"
#include <omp.h>

static int parse_card(const char *s) {
    int r = -1, su = -1;
    for (int i = 0; i < 13; i++) if (RANKCH[i] == s[0]) r = i;
    for (int i = 0; i < 4; i++) if (SUITCH[i] == s[1]) su = i;
    return (r < 0 || su < 0) ? -1 : r * 4 + su;
}

/* feature extraction */
static void features(const int *h, int *suitc, int *pairc, int *conn, int *acesuited, int *broad) {
    int sc[4] = {0}, rc[13] = {0};
    for (int i = 0; i < 4; i++) { sc[SUIT(h[i])]++; rc[RANK(h[i])]++; }
    int s2 = 0, s3 = 0, s4 = 0; for (int i = 0; i < 4; i++) { s2 += sc[i] == 2; s3 += sc[i] == 3; s4 += sc[i] == 4; }
    *suitc = s4 ? 4 : s3 ? 3 : s2 == 2 ? 0 : s2 == 1 ? 1 : 2; /* 0 DS, 1 SS, 2 rainbow, 3 three-suited, 4 monotone */
    int np = 0, nt = 0, nq = 0; for (int r = 0; r < 13; r++) { np += rc[r] == 2; nt += rc[r] == 3; nq += rc[r] == 4; }
    *pairc = nq ? 4 : nt ? 3 : np; /* 0 none, 1 one pair, 2 two pair, 3 trips, 4 quads */
    uint32_t m = 0; for (int r = 0; r < 13; r++) if (rc[r]) m |= 1u << r;
    int nd = __builtin_popcount(m);
    /* connectivity: smallest window (in ranks, ace can be low) containing all distinct ranks */
    int bestspan = 99;
    for (int lo = -1; lo <= 12; lo++) for (int hi = lo; hi <= 12; hi++) {
        uint32_t w = 0; for (int r = lo; r <= hi; r++) w |= 1u << (r < 0 ? 12 : r);
        if ((m & w) == m && hi - lo < bestspan) bestspan = hi - lo;
    }
    /* 0: 4 distinct ranks within 4 (rundown, e.g. 9876), 1: within 5 (one gap), 2: within 6,
       3: 3+ distinct ranks within 5 (partially connected), 4: other */
    if (nd == 4 && bestspan <= 3) *conn = 0;
    else if (nd == 4 && bestspan == 4) *conn = 1;
    else if (nd == 4 && bestspan == 5) *conn = 2;
    else {
        int ok = 0;
        for (int lo = -1; lo <= 8; lo++) {
            uint32_t w = 0; for (int r = lo; r <= lo + 4; r++) w |= 1u << (r < 0 ? 12 : r);
            if (__builtin_popcount(m & w) >= 3) ok = 1;
        }
        *conn = ok ? 3 : 4;
    }
    *acesuited = 0;
    for (int i = 0; i < 4; i++) if (RANK(h[i]) == 12) for (int j = 0; j < 4; j++) if (j != i && SUIT(h[j]) == SUIT(h[i])) *acesuited = 1;
    *broad = 0; for (int i = 0; i < 4; i++) *broad += RANK(h[i]) >= 8;
}

int main(int argc, char **argv) {
    init_tables();
    if (argc < 4) { fprintf(stderr, "usage\n"); return 1; }
    int np = atoi(argv[2]); long trials = atol(argv[3]);
    if (!strcmp(argv[1], "features")) {
        static double N[5][5][5][2][5], S[5][5][5][2][5];
        #pragma omp parallel
        {
            static __thread double n[5][5][5][2][5], s[5][5][5][2][5];
            memset(n, 0, sizeof n); memset(s, 0, sizeof s);
            rng_t r; rseed(&r, 555ULL + omp_get_thread_num() * 1337ULL + np);
            int deck[52]; for (int i = 0; i < 52; i++) deck[i] = i;
            int nth = omp_get_num_threads(); long my = trials / nth;
            for (long t = 0; t < my; t++) {
                shuffle_k(&r, deck, 52, np * 4 + 5);
                const int *board = deck + np * 4; uint32_t v[10], best = 0; int nb = 0;
                for (int p = 0; p < np; p++) { v[p] = eval_omaha(deck + 4 * p, board, 5); if (v[p] > best) { best = v[p]; nb = 1; } else if (v[p] == best) nb++; }
                for (int p = 0; p < np; p++) {
                    int a, b, c, d, e; features(deck + 4 * p, &a, &b, &c, &d, &e);
                    n[a][b][c][d][e] += 1; if (v[p] == best) s[a][b][c][d][e] += 1.0 / nb;
                }
            }
            #pragma omp critical
            { double *x = &n[0][0][0][0][0], *y = &N[0][0][0][0][0], *x2 = &s[0][0][0][0][0], *y2 = &S[0][0][0][0][0];
              for (size_t i = 0; i < sizeof n / sizeof(double); i++) { y[i] += x[i]; y2[i] += x2[i]; } }
        }
        printf("suit,pair,conn,acesuited,broadway,count,share\n");
        for (int a = 0; a < 5; a++) for (int b = 0; b < 5; b++) for (int c = 0; c < 5; c++) for (int d = 0; d < 2; d++) for (int e = 0; e < 5; e++)
            if (N[a][b][c][d][e] > 0) printf("%d,%d,%d,%d,%d,%.0f,%.3f\n", a, b, c, d, e, N[a][b][c][d][e], S[a][b][c][d][e]);
    } else if (!strcmp(argv[1], "named")) {
        int nh = argc - 4;
        double *eq = calloc(nh, sizeof(double));
        #pragma omp parallel for schedule(dynamic)
        for (int k = 0; k < nh; k++) {
            int h[4]; for (int i = 0; i < 4; i++) h[i] = parse_card(argv[4 + k] + 2 * i);
            rng_t r; rseed(&r, 31337ULL * (k + 1) + np);
            int deck[52]; int n = build_deck(deck, h, 4); double s = 0;
            for (long t = 0; t < trials; t++) {
                shuffle_k(&r, deck, n, (np - 1) * 4 + 5);
                const int *board = deck + (np - 1) * 4;
                uint32_t hv = eval_omaha(h, board, 5), best = 0; int nb = 0;
                for (int p = 0; p < np - 1; p++) { uint32_t v = eval_omaha(deck + 4 * p, board, 5); if (v > best) { best = v; nb = 1; } else if (v == best) nb++; }
                if (hv > best) s += 1; else if (hv == best) s += 1.0 / (nb + 1);
            }
            eq[k] = s / trials;
        }
        printf("hand,players,equity\n");
        for (int k = 0; k < nh; k++) printf("%s,%d,%.4f\n", argv[4 + k], np, eq[k]);
    }
    return 0;
}
