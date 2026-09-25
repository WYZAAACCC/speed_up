import io
p = "_chk_t21a.py"
s = io.open(p, encoding="utf-8").read()
a = """    rec('A4c uniaxial-z: spearman(dgrowth, w_v) >= 0.9', spearman(dg, wz) >= 0.9,
        'rho = %.3f' % spearman(dg, wz))"""
b = """    gap = df_.min() - du_.max()
    within = max(df_.max() - df_.min(), du_.max() - du_.min())
    rec('A4c uniaxial-z: TWO-LEVEL structure (gap > 5 x within-group spread)',
        gap > 5 * within,
        'gap = %+.3f%% ; within-group = %.3f%% ; ratio = %.1f'
        % (100 * gap, 100 * within, gap / within))
    print("      [记账] spearman is NOT a valid metric here: w_v is *exactly* "
          "degenerate inside each class (2 classes only), so the applied stress "
          "selects a FAMILY (集束/变体群), never a single variant.")"""
assert a in s; s = s.replace(a, b)
io.open(p, "w", encoding="utf-8").write(s)
print("patched A4c ok")