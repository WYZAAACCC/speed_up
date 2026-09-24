import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("        init_solid = (ca.gid > 0).copy()\n        for s_ in range(nst):",
              "        init_solid = (ca.gid > 0).copy()\n        nn = 0\n        for s_ in range(nst):", 1)
s = s.replace("            ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt)",
              "            nn += ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt)\n"
              "            if s_ == 0:\n"
              "                _liq = int((ca.gid == 0).sum())\n"
              "                _dT = float(np.clip(T_LIQ - T, 0, None)[ca.gid == 0].max()) if _liq else -1\n"
              "                print('       [dbg] step0 液相={} dT_max={:.2f} 形核={}'.format(_liq, _dT, nn))", 1)
s = s.replace("        rows = []\n        for g in range(1, len(ca.axes)):",
              "        print('       [dbg] 总形核 = {} ; 晶粒总数 = {}'.format(nn, len(ca.axes) - 1))\n"
              "        rows = []\n        for g in range(1, len(ca.axes)):", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("instrumented T7")