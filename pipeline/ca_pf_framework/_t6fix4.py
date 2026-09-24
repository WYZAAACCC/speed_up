import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace('def _wc_case(nst, N, n_t, n_y, spacing, seed, periodic=(False, True, False), quiet=True):',
              'def _wc_case(nst, N, n_t, n_y, spacing, seed, periodic=(False, True, False),\n             capture="decentered"):', 1)
s = s.replace('    ca = CA3D(N, N, N, dx, irf=irf, seed=seed, periodic=periodic)',
              '    ca = CA3D(N, N, N, dx, irf=irf, seed=seed, periodic=periodic, capture=capture)', 1)
s = s.replace('A = _wc_case(nst=240, N=150, n_t=3, n_y=3, spacing=25, seed=99)',
              'A = _wc_case(nst=240, N=150, n_t=3, n_y=3, spacing=25, seed=99, capture="analytic")', 1)
s = s.replace('''    B = _wc_case(nst=240, N=150, n_t=3, n_y=3, spacing=25, seed=99,
                 periodic=(False, False, False))''',
              '''    B = _wc_case(nst=240, N=150, n_t=3, n_y=3, spacing=25, seed=99,
                 capture="decentered")''', 1)
s = s.replace('''    chk("T6e 关掉侧向周期边界后判据失效（证明周期边界是必需的修法）",
        "PASS" if (not B["onlead"] or max(s_lead_B) > A["smin"] * 1.05) else "WARN",
        "周期开: 持有者 s 最大 {:.4f}; 周期关: {} 个持有者, s 最大 {}".format(''',
              '''    chk("T6e 格点路径规则(decentered)会翻转取向顺序（证明必须用 analytic）",
        "PASS" if (not B["onlead"] or max(s_lead_B) > A["smin"] * 1.05) else "WARN",
        "analytic: 持有者 s 最大 {:.4f}; decentered: {} 个持有者, s 最大 {}".format(''', 1)
s = s.replace('C = _wc_case(nst=240, N=110, n_t=3, n_y=3, spacing=25, seed=99)',
              'C = _wc_case(nst=240, N=110, n_t=3, n_y=3, spacing=25, seed=99, capture="analytic")', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched T6 -> analytic")