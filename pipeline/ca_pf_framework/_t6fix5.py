import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()

# 加入正确的包络支撑律
s = s.replace('''def support(P, n):
    n = np.array(n, float); n /= np.linalg.norm(n)
    return sum(abs(float(P[:, a] @ n)) for a in range(3))''',
'''def support(P, n):
    """decentered 格点规则下的有效半轴（= 报告 §8.4/T4 用的量）。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return sum(abs(float(P[:, a] @ n)) for a in range(3))


def apex_kernel(P, n):
    """【八面体 {sum_a|u_a| <= L} 沿 n̂ 的支撑】= max_a |p_a . n̂|。
    推导: 该八面体顶点在 (+-L,0,0)/(0,+-L,0)/(0,0,+-L)，故 support(n̂) = L*max_a|p_a.n̂|。
    注意 support(P,n) = sum_a|p_a.n̂| 是【decentered 规则的规律】，两者只在
    n̂ || <100> / <110> / <111> 等特殊方向重合 —— 这正是 T4 用 z/x/(111)/(120)
    四条方向能"通过"、而多晶随机取向会失败的原因。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return max(abs(float(P[:, a] @ n)) for a in range(3))''', 1)

# T6a: 用正确的律
s = s.replace("        s = support(ca.axes[g], n)\n        devs.append((float(sp[m].max()) - s0 - L_end / s) / dx)",
              "        s = apex_kernel(ca.axes[g], n)\n        devs.append((float(sp[m].max()) - s0 - L_end * s) / dx)", 1)
s = s.replace('chk("T6a 单晶自由生长律 a = V t / s（量出格点路径近似的地板）",\n        "PASS" if abs(devs).max() <= 3.0 else "WARN",\n        "9 个随机取向: 偏差 均值{:+.2f} std {:.2f} 最大|dev| {:.2f} 胞 (Vt=15dx)".format(',
              'chk("T6a 单晶自由生长律 a = V t * max_a|p_a.n̂|（真八面体支撑）",\n        "PASS" if abs(devs).max() <= 3.0 else "WARN",\n        "9 个随机取向: 偏差 均值{:+.2f} std {:.2f} 最大|dev| {:.2f} 胞 (Vt=15dx)".format(', 1)

# 多晶预测改用 apex_kernel；判据改成"顺序正确"
s = s.replace('    pred = {g: L_end / mm[g]["s"] for g in gids}',
              '    pred = {g: L_end * mm[g]["s"] for g in gids}   # s 此处 = apex_kernel', 1)
s = s.replace('        res[g] = dict(adv=-1e30, s=support(ca.axes[g], n), ncell=0, on_lead=False)',
              '        res[g] = dict(adv=-1e30, s=apex_kernel(ca.axes[g], n), ncell=0, on_lead=False)', 1)
s = s.replace('        res[g] = dict(adv=float(sp[m].max()) - s0, s=support(ca.axes[g], n),',
              '        res[g] = dict(adv=float(sp[m].max()) - s0, s=apex_kernel(ca.axes[g], n),', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched T6 -> correct octahedron law")