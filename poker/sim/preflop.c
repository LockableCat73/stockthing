/*
 * preflop.c - preflop equities for 2-card games.
 *   ./preflop holdem MAXPLAYERS TRIALS   -> equity of all 169 classes vs N-1 random hands, N=2..MAX
 *   ./preflop ttt    MAXPLAYERS TRIALS   -> same for Tic-tac-toe poker
 *   ./preflop matrix TRIALS              -> heads-up 169x169 hold'em equity matrix
 * Output: CSV on stdout.
 */
#include "common.h"
#include <omp.h>

static double run_class(int variant, int g, int nplayers, long trials, uint64_t seed, double *winp) {
    rng_t r; rseed(&r, seed);
    int h[2]; class169_rep(g, &h[0], &h[1]);
    int deck[52]; int n = build_deck(deck, h, 2);
    double share = 0, wins = 0;
    int nopp = nplayers - 1, nboard = variant == 0 ? 5 : 9;
    int need = nopp * 2 + nboard;
    for (long t = 0; t < trials; t++) {
        shuffle_k(&r, deck, n, need);
        const int *board = deck + nopp * 2;
        uint32_t hv, best = 0; int nbest = 0;
        if (variant == 0) {
            sm_t b; sm_clear(&b); for (int i = 0; i < 5; i++) sm_add(&b, board[i]);
            sm_t m = b; sm_add(&m, h[0]); sm_add(&m, h[1]); hv = sm_eval(m);
            for (int p = 0; p < nopp; p++) {
                sm_t o = b; sm_add(&o, deck[2*p]); sm_add(&o, deck[2*p+1]);
                uint32_t v = sm_eval(o);
                if (v > best) { best = v; nbest = 1; } else if (v == best) nbest++;
            }
        } else {
            hv = eval_ttt(h, board);
            for (int p = 0; p < nopp; p++) {
                uint32_t v = eval_ttt(deck + 2*p, board);
                if (v > best) { best = v; nbest = 1; } else if (v == best) nbest++;
            }
        }
        if (hv > best) { share += 1; wins += 1; }
        else if (hv == best) share += 1.0 / (nbest + 1);
    }
    *winp = wins / trials;
    return share / trials;
}

static void do_preflop(int variant, int maxp, long trials) {
    static double eq[169][10], wp[169][10];
    #pragma omp parallel for schedule(dynamic)
    for (int job = 0; job < 169 * (maxp - 1); job++) {
        int g = job % 169, np = 2 + job / 169;
        eq[g][np] = run_class(variant, g, np, trials, 1000003ULL * job + 17 + variant, &wp[g][np]);
    }
    printf("class,name,combos,players,equity,win\n");
    for (int np = 2; np <= maxp; np++)
        for (int g = 0; g < 169; g++) {
            char nm[4]; class169_name(g, nm);
            printf("%d,%s,%d,%d,%.5f,%.5f\n", g, nm, class169_combos(g), np, eq[g][np], wp[g][np]);
        }
}

/* combos of each class */
static int CL[169][12][2], NCL[169];
static void build_class_lists(void) {
    memset(NCL, 0, sizeof NCL);
    for (int a = 0; a < 52; a++) for (int b = a + 1; b < 52; b++) {
        int g = class169(a, b); CL[g][NCL[g]][0] = a; CL[g][NCL[g]][1] = b; NCL[g]++;
    }
}

static void do_matrix(long trials) {
    build_class_lists();
    static double M[169][169];
    #pragma omp parallel for schedule(dynamic)
    for (int a = 0; a < 169; a++) {
        rng_t r; rseed(&r, 7777ULL + a);
        for (int b = a; b < 169; b++) {
            double s = 0;
            for (long t = 0; t < trials; t++) {
                const int *x, *y;
                for (;;) {
                    x = CL[a][rbelow(&r, NCL[a])]; y = CL[b][rbelow(&r, NCL[b])];
                    if (x[0] != y[0] && x[0] != y[1] && x[1] != y[0] && x[1] != y[1]) break;
                }
                int used[52] = {0}; used[x[0]] = used[x[1]] = used[y[0]] = used[y[1]] = 1;
                int bd[5], k = 0;
                while (k < 5) { int c = rbelow(&r, 52); if (!used[c]) { used[c] = 1; bd[k++] = c; } }
                sm_t bm; sm_clear(&bm); for (int i = 0; i < 5; i++) sm_add(&bm, bd[i]);
                sm_t mx = bm, my = bm; sm_add(&mx, x[0]); sm_add(&mx, x[1]); sm_add(&my, y[0]); sm_add(&my, y[1]);
                uint32_t vx = sm_eval(mx), vy = sm_eval(my);
                s += vx > vy ? 1.0 : (vx == vy ? 0.5 : 0.0);
            }
            M[a][b] = s / trials; M[b][a] = 1.0 - M[a][b];
        }
    }
    for (int a = 0; a < 169; a++) {
        for (int b = 0; b < 169; b++) printf(b ? ",%.4f" : "%.4f", M[a][b]);
        printf("\n");
    }
}

int main(int argc, char **argv) {
    init_tables();
    if (argc >= 4 && !strcmp(argv[1], "holdem")) do_preflop(0, atoi(argv[2]), atol(argv[3]));
    else if (argc >= 4 && !strcmp(argv[1], "ttt")) do_preflop(1, atoi(argv[2]), atol(argv[3]));
    else if (argc >= 3 && !strcmp(argv[1], "matrix")) do_matrix(atol(argv[2]));
    else { fprintf(stderr, "usage: see header\n"); return 1; }
    return 0;
}
