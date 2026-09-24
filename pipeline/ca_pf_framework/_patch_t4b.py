# -*- coding: utf-8 -*-
"""_patch_t4b.py --- 纠正 T4b/T4c：支撑函数 vs 径向函数是两个不同的量，两者各自都对"""
import io, sys
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_physics.py"
s = io.open(P, encoding="utf-8").read()
old = '''    ok = (worst <= 2.5) and (worst < worst_sup - 0.2)     # 吻合径向律 + 判据有区分度
    chk("T4b 取向律 = L/Σ_a|p_a.n̂|（八面体径向函数; envelope 捕获）",
        "PASS" if ok else "WARN",
        "{} 个测点; 与 l/Σ 最大偏差 {:.2f} 胞, 与 l*max(支撑律) 偏差 {:.2f} 胞 "
        "(判据: <=2.5 胞 且 明显优于支撑律)".format(nq, worst, worst_sup), (worst, worst_sup))'''
new = '''    # 【2026-09-23 更正】本判据量的是 proj.max() = 占据集沿 n̂ 的【支撑函数】，
    # 因此解析律就是 L*max_a|p_a.n̂|（凸集支撑 = L||n̂||_inf）—— 原判据是对的。
    # 与它并列的 `L/Σ` 是【径向函数】（沿射线到边界的距离，=|{Σ|u|<=L}| 的边界点），
    # 那才是【胞是否被包络覆盖】的判据（CA 的 thr=dx*Σ 即此），由 verify_ca3d_envelope.E1 正面测。
    # 两者都正确、只是不同的量；本判据只收紧容差，让它真的能看见东西。
    ok = (worst_sup <= 2.5)
    chk("T4b 取向律 apex(n̂) = L*max_a|p_a.n̂|（凸集支撑; envelope 捕获）",
        "PASS" if ok else "WARN",
        "{} 个测点; 与 l*max(支撑)差 {:.2f} 胞, 同测点与 l/Σ(径向)差 {:.2f} 胞 (判据 <=2.5 胞)".format(
            nq, worst_sup, worst), (worst_sup, worst))'''
if old not in s: print("!! 1"); sys.exit(1)
s = s.replace(old, new)
old = '''    chk("T4c 对照: decentered 规则偏离径向律的幅度（多晶淘汰失败根因）",
        "PASS" if worst_d > worst else "WARN",
        "decentered 最大偏差 {:.2f} 胞 vs analytic {:.2f} 胞 ⇒ 格点路径代价与取向强相关".format(
            worst_d, worst), worst_d)'''
new = '''    # 注意：支撑函数对 decentered 的格点路径缺陷【不敏感】（两者都 2 胞左右）。
    # 真正能暴露该缺陷的是"沿射线的径向可达距离"，见 verify_ca3d_envelope.py E1
    # （decentered 实测 r(<100>)/l=0.60~0.76，正确值 1.00）。本项只作记录。
    chk("T4c 记录: decentered 的支撑函数偏差（对格点路径缺陷不敏感）",
        "PASS",
        "decentered 支撑偏差 {:.2f} 胞 vs envelope {:.2f} 胞；径向缺陷请看 "
        "verify_ca3d_envelope.E1".format(worst_d, worst), worst_d)'''
if old not in s: print("!! 2"); sys.exit(1)
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8").write(s)

# ---- 审计文档 §N2 更正 ----
P2 = "/mnt/f/speed_up/pipeline/ca_pf_framework/CA3D_AUDIT_2026-09-23.md"
a = io.open(P2, encoding="utf-8").read()
old2 = '''| N2 | 文档把根因写成"支撑律用错（应为 ℓ·max）" | ❌ **概念错**：`ℓ·max_a\\|p_a·n̂\\|` 是八面体的**支撑函数**，`r=ℓ/Σ` 才是**径向函数**（就是 §4.4 写的、也是代码 `thr=dx·Σ` 用的）。两者在 ⟨100⟩/⟨110⟩/⟨111⟩ 上巧合相等 —— 真正的病是"格点路径预算"（N1） |'''
new2 = '''| N2 | ~~"支撑律用错"~~ → **【2026-09-23 自我更正】不是错** | `ℓ·max_a\\|p_a·n̂\\|` 是**支撑函数**（占据集沿 n̂ 的最大投影，`verify_ca3d_physics.T4b` 量的就是它，凸集支撑 = ℓ‖n̂‖∞ ✓ 对的）；`r=ℓ/Σ` 是**径向函数**（沿射线到边界的距离=胞是否被覆盖的判据，代码 `thr=dx·Σ` 与 §4.4 ✓ 也对的）。两者是**不同的量**，各自都正确。**真正的病仍是 N1（格点路径预算）**，它的可观测后果是"径向可达距离短 25~40%"（E1），而不是支撑函数偏差（对 N1 不敏感，T4c 记录 ⌀2 胞） |'''
if old2 not in a:
    print("!! N2 锚点未找到（手工核对）")
else:
    a = a.replace(old2, new2)
    io.open(P2, "w", encoding="utf-8").write(a)
    print("审计 §N2 已更正")
print("T4 判据已纠正")