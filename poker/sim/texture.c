/*
 * texture.c - Hold'em range-vs-range flop analysis by board texture (for c-bet strategy).
 *
 *   ./texture RANGE_A RANGE_B TRIALS
 *
 * RANGE files hold 169 weights (0..1), one per line, in class-index order (see common.h).
 * A = preflop raiser, B = caller. For each deal: a combo from each range (no card conflicts),
 * a random flop, and 6 random turn+river run-outs. Results are grouped by texture key:
 *   key = hi*24 + paired*12 + suits*4 + conn      hi: 0 A-high,1 K,2 Q,3 J/T,4 9-or-lower
 *   suits: 0 rainbow, 1 two-tone, 2 monotone       conn: 0 dry, 1 straight possible(3 ranks in a
 *   5-window), 2 very connected (3 ranks within 3, e.g. 987 / T98)  (3 unused)
 * Output CSV: key,count,eqA,A_strong,B_strong,A_toppair,B_toppair,A_air,B_air
 *   strong = two pair or better (made code >= 6), toppair = top pair or better (>=3), air = no pair no draw.
 */
#include "common.h"
#include "codes.h"
#include <omp.h>

static double WA[169], WB[169];
static int CMB[1326][2], CCL[1326];

static void load_range(const char *p, double *w) {
    FILE *f = fopen(p, "r"); if (!f) { perror(p); exit(1); }
    for (int i = 0; i < 169; i++) if (fscanf(f, "%lf", &w[i]) != 1) { fprintf(stderr, "bad range\n"); exit(1); }
    fclose(f);
}
static inline int draw_combo(rng_t *r, const double *w) {
    for (;;) {
        int k = rbelow(r, 1326);
        double x = w[CCL[k]];
        if (x >= 1.0 || (x > 0 && (rnext(r) >> 11) * (1.0 / 9007199254740992.0) < x)) return k;
    }
}
static int texture_key(const int *f) {
    int r[3] = {RANK(f[0]), RANK(f[1]), RANK(f[2])};
    int hi = r[0]; if (r[1] > hi) hi = r[1]; if (r[2] > hi) hi = r[2];
    int hk = hi == 12 ? 0 : hi == 11 ? 1 : hi == 10 ? 2 : hi >= 8 ? 3 : 4;
    int paired = r[0] == r[1] || r[0] == r[2] || r[1] == r[2];
    int s0 = SUIT(f[0]), s1 = SUIT(f[1]), s2 = SUIT(f[2]);
    int suits = (s0 == s1 && s1 == s2) ? 2 : (s0 == s1 || s0 == s2 || s1 == s2) ? 1 : 0;
    uint32_t m = (1u << r[0]) | (1u << r[1]) | (1u << r[2]);
    int conn = 0;
    if (!paired) {
        for (int lo = -1; lo <= 8; lo++) {
            uint32_t w = 0; for (int x = lo; x <= lo + 4; x++) w |= 1u << (x < 0 ? 12 : x);
            if ((m & w) == m) conn = 1;
        }
        for (int lo = -1; lo <= 10; lo++) {
            uint32_t w = 0; for (int x = lo; x <= lo + 2; x++) w |= 1u << (x < 0 ? 12 : x);
            if ((m & w) == m) conn = 2;
        }
    }
    return hk * 24 + paired * 12 + suits * 4 + conn;
}

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: texture RANGE_A RANGE_B TRIALS\n"); return 1; }
    init_tables();
    load_range(argv[1], WA); load_range(argv[2], WB);
    long trials = atol(argv[3]);
    int k = 0;
    for (int a = 0; a < 52; a++) for (int b = a + 1; b < 52; b++) { CMB[k][0] = a; CMB[k][1] = b; CCL[k] = class169(a, b); k++; }
    static double N[120], EQ[120], AS[120], BS[120], AT[120], BT[120], AA[120], BA[120];
    #pragma omp parallel
    {
        double n[120] = {0}, eq[120] = {0}, as[120] = {0}, bs[120] = {0}, at[120] = {0}, bt[120] = {0}, aa[120] = {0}, ba[120] = {0};
        rng_t r; rseed(&r, 4242ULL + 31ULL * omp_get_thread_num());
        long my = trials / omp_get_num_threads();
        for (long t = 0; t < my; t++) {
            int ka, kb;
            const int *x, *y;
            for (;;) {
                ka = draw_combo(&r, WA); kb = draw_combo(&r, WB); x = CMB[ka]; y = CMB[kb];
                if (x[0] != y[0] && x[0] != y[1] && x[1] != y[0] && x[1] != y[1]) break;
            }
            int deck[52]; int ex[4] = {x[0], x[1], y[0], y[1]}; int nd = build_deck(deck, ex, 4);
            shuffle_k(&r, deck, nd, 3);
            int board[5] = {deck[0], deck[1], deck[2], 0, 0};
            int key = texture_key(board);
            int da, db;
            int ma = holdem_code(x, board, 3, eval_holdem(x, board, 3), &da);
            int mb = holdem_code(y, board, 3, eval_holdem(y, board, 3), &db);
            double s = 0;
            for (int ro = 0; ro < 6; ro++) {
                /* sample turn+river from deck[3..nd) */
                int i1 = 3 + rbelow(&r, nd - 3), i2;
                do { i2 = 3 + rbelow(&r, nd - 3); } while (i2 == i1);
                board[3] = deck[i1]; board[4] = deck[i2];
                uint32_t va = eval_holdem(x, board, 5), vb = eval_holdem(y, board, 5);
                s += va > vb ? 1 : va == vb ? 0.5 : 0;
            }
            n[key] += 1; eq[key] += s / 6;
            as[key] += ma >= 6; bs[key] += mb >= 6; at[key] += ma >= 3; bt[key] += mb >= 3;
            aa[key] += (ma == 0 && da == 0); ba[key] += (mb == 0 && db == 0);
        }
        #pragma omp critical
        for (int i = 0; i < 120; i++) { N[i] += n[i]; EQ[i] += eq[i]; AS[i] += as[i]; BS[i] += bs[i]; AT[i] += at[i]; BT[i] += bt[i]; AA[i] += aa[i]; BA[i] += ba[i]; }
    }
    printf("key,count,eqA,A_strong,B_strong,A_toppair,B_toppair,A_air,B_air\n");
    for (int i = 0; i < 120; i++) if (N[i] > 0)
        printf("%d,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f\n", i, N[i], EQ[i], AS[i], BS[i], AT[i], BT[i], AA[i], BA[i]);
    return 0;
}
