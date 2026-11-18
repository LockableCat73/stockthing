/*
 * cats.c - street-by-street hand-category equities when EVERY player sees the flop with a random
 * hand (the situation in the no-preflop-betting variants).
 *
 *   ./cats VARIANT NPLAYERS TRIALS [PINEAPPLE_STRATEGY_CSV]
 *   VARIANT = holdem | pineapple | omaha | ttt
 *
 * Every player in every deal is used as "hero" (all seats are symmetric), so one deal gives
 * NPLAYERS samples. For each player we classify the hand on the flop and turn into a
 * (made, draw) pair and record the share of the pot won at showdown. Heads-up equities between
 * every ordered pair of players (ignoring the others) are also tabulated by category.
 *
 * Output CSV rows (first field = table):
 *   flop,made,draw,count,share          multiway equity by category
 *   turn,made,draw,count,share
 *   river,cat,r1,count,share            river hand (category, top rank) vs the whole field
 *   win,cat,r1,count                    winning hand at showdown (one per deal)
 *   huflop,keyA,keyB,count,shareA       key = made*16+draw ; heads-up equity A vs B
 *   huturn,keyA,keyB,count,shareA
 *   meta,variant,players,trials
 *
 * Category codes are documented in the *_NAMES tables below and in ../results/README.md.
 */
#include "common.h"
#include "pineclass.h"
#include <omp.h>

enum { V_HOLDEM, V_PINE, V_OMAHA, V_TTT };

#include "codes.h"

/* ---------------------------------------------------------------- Omaha */
static const char *OM_NAMES[] = {"nothing", "pair (not top)", "top pair", "overpair", "two pair (not top two)",
    "top two pair", "trips (board pair)", "bottom set", "middle set", "top set", "straight (non-nut)",
    "nut straight", "flush (non-nut)", "nut flush", "full house+"};
/* draw = 4*flush + straight : straight 0 none,1 1-7 outs,2 8-12 outs,3 13+ outs ; flush 0 none,1 non-nut,2 nut */

static int omaha_code(const int *h, const int *b, int nb, uint32_t v, int *draw, int street_has_more) {
    int cnt[13], d[5], nd; uint32_t BR; board_info(b, nb, cnt, d, &nd, &BR);
    int cat = CAT(v), made = 0; *draw = 0;
    if (cat >= FULLHOUSE) return 14;
    if (cat == FLUSH) {
        int s = -1; for (int k = 0; k < 4; k++) { int c = 0; for (int i = 0; i < nb; i++) c += SUIT(b[i]) == k; if (c >= 3) s = k; }
        return (s >= 0 && holds(h, 4, top_missing(s, b, nb), s)) ? 13 : 12;
    }
    if (cat == STRAIGHT) made = ((int)((v >> 16) & 15) == best_board_straight(BR, 3)) ? 11 : 10;
    else {
        int hc[13] = {0}; for (int i = 0; i < 4; i++) hc[RANK(h[i])]++;
        int t = (v >> 16) & 15;
        if (cat == TRIPS && cnt[t] == 1) made = (t == d[0]) ? 9 : (nd > 1 && t == d[1]) ? 8 : 7;
        else if (cat == TRIPS && cnt[t] == 2) made = 6;
        else {
            uint32_t M = 0, PP = 0;
            for (int r = 0; r < 13; r++) { if (hc[r] && cnt[r]) M |= 1u << r; if (hc[r] >= 2) PP |= 1u << r; }
            if (__builtin_popcount(M) >= 2) made = (nd > 1 && (M >> d[0] & 1) && (M >> d[1] & 1)) ? 5 : 4;
            else if (PP && topbit(PP) > d[0]) made = 3;
            else if (M >> d[0] & 1) made = 2;
            else if (M || PP) made = 1;
            else made = 0;
        }
    }
    if (!street_has_more) return made;
    /* outs: enumerate every unseen card */
    int used[52] = {0}; for (int i = 0; i < 4; i++) used[h[i]] = 1; for (int i = 0; i < nb; i++) used[b[i]] = 1;
    int bb[6]; memcpy(bb, b, nb * sizeof(int));
    int fo = 0, so = 0;
    for (int c = 0; c < 52; c++) {
        if (used[c]) continue;
        bb[nb] = c; int nc = CAT(eval_omaha(h, bb, nb + 1));
        if (nc == FLUSH || nc == STFLUSH) fo++;
        else if (nc == STRAIGHT && cat < STRAIGHT) so++;
    }
    int fb = 0;
    if (fo) {
        fb = 1;
        for (int s = 0; s < 4; s++) {
            int bc = 0, hcs = 0; for (int i = 0; i < nb; i++) bc += SUIT(b[i]) == s; for (int i = 0; i < 4; i++) hcs += SUIT(h[i]) == s;
            if (bc == 2 && hcs >= 2 && holds(h, 4, top_missing(s, b, nb), s)) fb = 2;
        }
    }
    int sb = so == 0 ? 0 : so <= 7 ? 1 : so <= 12 ? 2 : 3;
    *draw = fb * 4 + sb;
    return made;
}

/* ----------------------------------------------------------- Tic-tac-toe */
static const char *TF_NAMES[] = {"nothing", "pair with a corner", "pocket pair", "two pair", "trips/set", "quads"};
static const char *TFD_NAMES[] = {"no draw", "4-straight", "4-flush", "4-straight + 4-flush"};
static const int CORNERS[4] = {0, 2, 6, 8};

static int ttt_flop_code(const int *h, const int *g, int *draw) {
    int best = 0, sd = 0;
    for (int i = 0; i < 4; i++) for (int j = i + 1; j < 4; j++) {
        int c4[4] = {h[0], h[1], g[CORNERS[i]], g[CORNERS[j]]};
        int cat = CAT(eval_cards(c4, 4));
        if (cat > best) best = cat;
        uint32_t m = 0; for (int k = 0; k < 4; k++) m |= 1u << RANK(c4[k]);
        if (__builtin_popcount(m) == 4) {
            for (int hi = 12; hi >= 3; hi--) {
                uint32_t w = hi >= 4 ? (0x1Fu << (hi - 4)) : 0x100Fu;
                if ((m & w) == m) { sd = 1; break; }
            }
        }
    }
    int fd = 0;
    if (SUIT(h[0]) == SUIT(h[1])) {
        int c = 0; for (int i = 0; i < 4; i++) c += SUIT(g[CORNERS[i]]) == SUIT(h[0]);
        fd = c >= 2;
    }
    *draw = fd * 2 + sd;
    int pocket = RANK(h[0]) == RANK(h[1]);
    switch (best) {
        case QUADS: return 5;
        case TRIPS: return 4;
        case TWOPAIR: return 3;
        case PAIR: return pocket ? 2 : 1;
        default: return 0;
    }
}
static const char *TT_NAMES[] = {"high card", "pair", "two pair", "trips", "straight", "flush", "full house", "quads", "straight flush"};
static const char *TTD_NAMES[] = {"0 center outs to straight+", "1-3 outs", "4-7 outs", "8-11 outs", "12+ outs"};

static int ttt_turn_code(const int *h, int *g, uint32_t v_edge, int *draw) {
    int cat = CAT(v_edge);
    int used[52] = {0}; used[h[0]] = used[h[1]] = 1;
    for (int i = 0; i < 9; i++) if (i != 4) used[g[i]] = 1;
    int save = g[4], outs = 0;
    for (int c = 0; c < 52; c++) {
        if (used[c]) continue;
        g[4] = c;
        uint32_t best = v_edge;
        for (int k = 0; k < 4; k++) { uint32_t x = eval_ttt_line(h, g, TTT_CENTER_LINES[k]); if (x > best) best = x; }
        int nc = CAT(best);
        if (nc >= STRAIGHT && nc > cat) outs++;
    }
    g[4] = save;
    *draw = outs == 0 ? 0 : outs <= 3 ? 1 : outs <= 7 ? 2 : outs <= 11 ? 3 : 4;
    return cat;
}

/* ---------------------------------------------------------------- main */
#define NK 256
typedef struct {
    double fl_n[NK], fl_s[NK], tu_n[NK], tu_s[NK];
    double rv_n[9][13], rv_s[9][13], win[9][13];
    double hf_n[NK][NK], hf_s[NK][NK], ht_n[NK][NK], ht_s[NK][NK];
} acc_t;

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: cats VARIANT NPLAYERS TRIALS [STRATEGY]\n"); return 1; }
    init_tables();
    int var = !strcmp(argv[1], "holdem") ? V_HOLDEM : !strcmp(argv[1], "pineapple") ? V_PINE :
              !strcmp(argv[1], "omaha") ? V_OMAHA : !strcmp(argv[1], "ttt") ? V_TTT : -1;
    if (var < 0) { fprintf(stderr, "bad variant\n"); return 1; }
    int np = atoi(argv[2]); long trials = atol(argv[3]);
    if (var == V_PINE) {
        init_classes();
        if (argc < 5 || !load_drop_strategy(argv[4])) { fprintf(stderr, "pineapple needs a strategy file\n"); return 1; }
    }
    int hole_dealt = var == V_OMAHA ? 4 : var == V_PINE ? 3 : 2;
    int hole_kept = var == V_OMAHA ? 4 : 2;
    int nboard = var == V_TTT ? 9 : 5;
    acc_t *tot = calloc(1, sizeof(acc_t));

    #pragma omp parallel
    {
        acc_t *a = calloc(1, sizeof(acc_t));
        rng_t r; rseed(&r, 12345ULL + 1000ULL * omp_get_thread_num() + 77ULL * np + var);
        int deck[52]; for (int i = 0; i < 52; i++) deck[i] = i;
        int nth = omp_get_num_threads();
        long my = trials / nth + (omp_get_thread_num() < trials % nth);
        int H[10][4], key_f[10], key_t[10]; uint32_t fv[10];
        for (long t = 0; t < my; t++) {
            shuffle_k(&r, deck, 52, np * hole_dealt + nboard);
            int *board = deck + np * hole_dealt;
            for (int p = 0; p < np; p++) {
                const int *src = deck + p * hole_dealt;
                if (var == V_PINE) {
                    int dc = opp_drop(&r, src), k = 0;
                    for (int i = 0; i < 3; i++) if (src[i] != dc) H[p][k++] = src[i];
                } else for (int i = 0; i < hole_kept; i++) H[p][i] = src[i];
            }
            for (int p = 0; p < np; p++) {
                int mf, df, mt, dt;
                if (var == V_HOLDEM || var == V_PINE) {
                    mf = holdem_code(H[p], board, 3, eval_holdem(H[p], board, 3), &df);
                    mt = holdem_code(H[p], board, 4, eval_holdem(H[p], board, 4), &dt);
                    fv[p] = eval_holdem(H[p], board, 5);
                } else if (var == V_OMAHA) {
                    mf = omaha_code(H[p], board, 3, eval_omaha(H[p], board, 3), &df, 1);
                    mt = omaha_code(H[p], board, 4, eval_omaha(H[p], board, 4), &dt, 1);
                    fv[p] = eval_omaha(H[p], board, 5);
                } else {
                    mf = ttt_flop_code(H[p], board, &df);
                    mt = ttt_turn_code(H[p], board, eval_ttt_edges(H[p], board), &dt);
                    fv[p] = eval_ttt(H[p], board);
                }
                key_f[p] = mf * 16 + df; key_t[p] = mt * 16 + dt;
            }
            uint32_t best = 0; int nbest = 0;
            for (int p = 0; p < np; p++) { if (fv[p] > best) { best = fv[p]; nbest = 1; } else if (fv[p] == best) nbest++; }
            a->win[CAT(best)][(best >> 16) & 15] += 1;
            for (int p = 0; p < np; p++) {
                double s = fv[p] == best ? 1.0 / nbest : 0.0;
                a->fl_n[key_f[p]] += 1; a->fl_s[key_f[p]] += s;
                a->tu_n[key_t[p]] += 1; a->tu_s[key_t[p]] += s;
                int c = CAT(fv[p]), r1 = (fv[p] >> 16) & 15;
                a->rv_n[c][r1] += 1; a->rv_s[c][r1] += s;
                for (int q = 0; q < np; q++) {
                    if (q == p) continue;
                    double hs = fv[p] > fv[q] ? 1.0 : fv[p] == fv[q] ? 0.5 : 0.0;
                    a->hf_n[key_f[p]][key_f[q]] += 1; a->hf_s[key_f[p]][key_f[q]] += hs;
                    a->ht_n[key_t[p]][key_t[q]] += 1; a->ht_s[key_t[p]][key_t[q]] += hs;
                }
            }
        }
        #pragma omp critical
        {
            double *x = (double *)a, *y = (double *)tot;
            for (size_t i = 0; i < sizeof(acc_t) / sizeof(double); i++) y[i] += x[i];
        }
        free(a);
    }
    printf("meta,%s,%d,%ld\n", argv[1], np, trials);
    for (int k = 0; k < NK; k++) if (tot->fl_n[k] > 0) printf("flop,%d,%d,%.0f,%.3f\n", k / 16, k % 16, tot->fl_n[k], tot->fl_s[k]);
    for (int k = 0; k < NK; k++) if (tot->tu_n[k] > 0) printf("turn,%d,%d,%.0f,%.3f\n", k / 16, k % 16, tot->tu_n[k], tot->tu_s[k]);
    for (int c = 0; c < 9; c++) for (int r1 = 0; r1 < 13; r1++) {
        if (tot->rv_n[c][r1] > 0) printf("river,%d,%d,%.0f,%.3f\n", c, r1, tot->rv_n[c][r1], tot->rv_s[c][r1]);
        if (tot->win[c][r1] > 0) printf("win,%d,%d,%.0f\n", c, r1, tot->win[c][r1]);
    }
    for (int i = 0; i < NK; i++) for (int j = 0; j < NK; j++) {
        if (tot->hf_n[i][j] > 0) printf("huflop,%d,%d,%.0f,%.3f\n", i, j, tot->hf_n[i][j], tot->hf_s[i][j]);
        if (tot->ht_n[i][j] > 0) printf("huturn,%d,%d,%.0f,%.3f\n", i, j, tot->ht_n[i][j], tot->ht_s[i][j]);
    }
    (void)HM_NAMES; (void)HD_NAMES; (void)OM_NAMES; (void)TF_NAMES; (void)TFD_NAMES; (void)TT_NAMES; (void)TTD_NAMES;
    return 0;
}
