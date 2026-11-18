/* test_eval.c - exhaustive check of the evaluator against known 5- and 7-card counts */
#include "common.h"
int main(void) {
    init_tables();
    long long c5[9] = {0}, c7[9] = {0}, distinct = 0;
    static uint8_t seen[1 << 24];
    int h[7];
    for (h[0] = 0; h[0] < 52; h[0]++) for (h[1] = h[0]+1; h[1] < 52; h[1]++)
    for (h[2] = h[1]+1; h[2] < 52; h[2]++) for (h[3] = h[2]+1; h[3] < 52; h[3]++)
    for (h[4] = h[3]+1; h[4] < 52; h[4]++) {
        uint32_t v = eval_cards(h, 5); c5[CAT(v)]++;
        if (!seen[v]) { seen[v] = 1; distinct++; }
    }
    for (h[0] = 0; h[0] < 52; h[0]++) for (h[1] = h[0]+1; h[1] < 52; h[1]++)
    for (h[2] = h[1]+1; h[2] < 52; h[2]++) for (h[3] = h[2]+1; h[3] < 52; h[3]++)
    for (h[4] = h[3]+1; h[4] < 52; h[4]++) {
        sm_t m; sm_clear(&m); for (int i = 0; i < 5; i++) sm_add(&m, h[i]);
        for (h[5] = h[4]+1; h[5] < 52; h[5]++) { sm_t m2 = m; sm_add(&m2, h[5]);
        for (h[6] = h[5]+1; h[6] < 52; h[6]++) { sm_t m3 = m2; sm_add(&m3, h[6]); c7[CAT(sm_eval(m3))]++; } }
    }
    const long long e5[9] = {1302540,1098240,123552,54912,10200,5108,3744,624,40};
    const long long e7[9] = {23294460,58627800,31433400,6461620,6180020,4047644,3473184,224848,41584};
    int ok = 1;
    for (int i = 0; i < 9; i++) {
        printf("%-15s 5c %9lld (exp %9lld)   7c %10lld (exp %10lld)\n", CATNAME[i], c5[i], e5[i], c7[i], e7[i]);
        if (c5[i] != e5[i] || c7[i] != e7[i]) ok = 0;
    }
    printf("distinct 5-card hand values: %lld (expect 7462)\n", distinct);
    if (distinct != 7462) ok = 0;
    printf(ok ? "ALL OK\n" : "MISMATCH\n");
    return !ok;
}
