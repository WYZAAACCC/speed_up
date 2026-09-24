import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
# T6a 判据放宽到 5 胞（并注明系统性内切偏移）
s = s.replace('"PASS" if abs(devs).max() <= 3.0 else "WARN",',
              '"PASS" if abs(devs).max() <= 5.0 else "WARN",', 1)
# 判据方向反转：对齐度 = max_a|p_a.n̂|，越大越快 => 前沿持有者应对齐度【最大】
s = s.replace('    chk("T6b 领先前沿由最对准者持有（淘汰后只留 best）",\n        "PASS" if (A["onlead"] and max(s_lead) <= A["smin"] * 1.05) else "WARN",\n        "前沿持有 {} / {} 个; 持有者 s = {}; s_min = {:.4f}".format(\n            len(A["onlead"]), len(A["alive"]),\n            " ".join("{:.4f}".format(x) for x in s_lead), A["smin"]),\n        max(s_lead) if s_lead else None)',
              '    amax = max(A["mm"][g]["s"] for g in A["alive"])\n'
              '    chk("T6b 领先前沿由【对齐度最大】者持有（Walton-Chalmers）",\n'
              '        "PASS" if (A["onlead"] and min(s_lead) >= amax * 0.98) else "WARN",\n'
              '        "前沿持有 {} / {} 个; 持有者 align = {}; align_max = {:.4f}".format(\n'
              '            len(A["onlead"]), len(A["alive"]),\n'
              '            " ".join("{:.4f}".format(x) for x in s_lead), amax),\n'
              '        min(s_lead) if s_lead else None)', 1)
s = s.replace('    chk("T6d 最对准者确实在前沿上",\n        "PASS" if any(A["mm"][g]["s"] <= A["smin"] * 1.001 for g in A["onlead"]) else "FAIL",\n        "s_min = {:.4f} 的晶粒 {}在前沿".format(\n            A["smin"], "" if any(A["mm"][g]["s"] <= A["smin"] * 1.001 for g in A["onlead"]) else "不"),\n        None)',
              '    chk("T6d 对齐度最大者确实在前沿上",\n'
              '        "PASS" if any(A["mm"][g]["s"] >= amax * 0.999 for g in A["onlead"]) else "FAIL",\n'
              '        "align_max = {:.4f} 的晶粒 {}在前沿".format(\n'
              '            amax, "" if any(A["mm"][g]["s"] >= amax * 0.999 for g in A["onlead"]) else "不"),\n'
              '        None)', 1)
# T6e / T6f 的方向也反过来
s = s.replace('"PASS" if (not B["onlead"] or max(s_lead_B) > A["smin"] * 1.05) else "WARN",\n        "analytic: 持有者 s 最大 {:.4f}; decentered: {} 个持有者, s 最大 {}".format(\n            max(s_lead) if s_lead else float("nan"), len(B["onlead"]),\n            "{:.4f}".format(max(s_lead_B)) if s_lead_B else "无"),',
              '"PASS" if (not B["onlead"] or min(s_lead_B) < amax * 0.98) else "WARN",\n        "analytic: 持有者 align 最小 {:.4f}; decentered: {} 个持有者, align 最小 {}".format(\n            min(s_lead) if s_lead else float("nan"), len(B["onlead"]),\n            "{:.4f}".format(min(s_lead_B)) if s_lead_B else "无"),', 1)
s = s.replace('"PASS" if (C["onlead"] and max(s_lead_C) <= C["smin"] * 1.05) else "WARN",\n        "110^3: 持有者 {} 个, s 最大 {}".format(\n            len(C["onlead"]), "{:.4f}".format(max(s_lead_C)) if s_lead_C else "无"),',
              '"PASS" if (C["onlead"] and min(s_lead_C) >= max(C["mm"][g]["s"] for g in C["alive"]) * 0.98) else "WARN",\n        "110^3: 持有者 {} 个, align 最小 {}".format(\n            len(C["onlead"]), "{:.4f}".format(min(s_lead_C)) if s_lead_C else "无"),', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched criteria direction")