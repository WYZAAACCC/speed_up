#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_consistency.py —— **⑥ 终检 · 层次①（物理模型）**：跨判据自洽检查。

## 为什么要它（思路）
  各判据自身"算术正确"**不等于**它们彼此自洽。本工具把**同一参数集**下
  各判据算出的量放在一起，检查它们**互相是否矛盾**、**量纲是否一致**、
  **极限是否合理**（③ 纪律第 6 条要求的可 FAIL 判据：量纲 / 极限 / 内部自洽 / 交叉核对）。

## 参数集（**唯一权威 = 生产算例自己的 `meta.json`**，硬步骤 A）
  见下方 `load_prod()`：读 `_exp/_bk_t5/<tag>/meta.json`（若没有就用档案值并注明）。
"""
import json
import math
import os
import sys

sys.path.insert(0, ".")
import windowB_closure as CL  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
TI_TAGS = ["dry_t10B9", "dry_t10PRT2_b3_1005_1213"]


def load_prod():
    """读生产算例的 meta.json（硬步骤 A：参数实际取值的唯一权威）。"""
    for tag in TI_TAGS:
        for base in (os.path.join(ROOT, "_exp", "_bk_t5"),
                     "/mnt/f/speed_up/_exp/_bk_t5"):
            p = os.path.join(base, tag, "meta.json")
            if os.path.exists(p):
                d = json.load(open(p, encoding="utf-8"))
                ea = d.get("exp_args", {}) or {}
                return tag, d, ea
    return None, {}, {}


tag, meta, ea = load_prod()
print("=" * 96)
print("⑥ 终检 · 层次①（物理模型）：跨判据自洽检查")
print("=" * 96)
if tag:
    print(f"参数来源（硬步骤 A）：`{tag}/meta.json`")
else:
    print("⚠ **没有找到生产 meta.json** ⇒ 下面用档案值（必须注明，不得当成权威）")


def g(k, dflt):
    v = ea.get(k, meta.get(k, dflt))
    return dflt if v is None else v


N = int(g("N", 160))
DX = float(g("dx_nm", 62.5)) * 1e-9
NV = int(g("nv", 220))
STEPS = int(g("steps", 20000))
AKM = float(g("alpha_km", 0.041739))
TEND = float(g("T_end", 298.0))
QS = int(g("qs_clock", 1) or 0)
QSMAX = int(g("qs_max_relax", 100) or 0)
PL = float(g("plate_L", 2400.0)) * 1e-9
PW = float(g("plate_W", 640.0)) * 1e-9
PT = float(g("plate_T", 510.0)) * 1e-9
L = N * DX
MS = CL.M_S_TI64

print(f"  N={N}  dx={DX*1e9:.1f} nm  L={L*1e6:.3f} µm  nv={NV}  steps={STEPS}")
print(f"  α_KM={AKM}  T_end={TEND}  qs_clock={QS}  qs_max_relax={QSMAX}")
print(f"  plate: L={PL*1e9:.0f} W={PW*1e9:.0f} T={PT*1e9:.0f} nm")

# ---------------- ① C-2：每块板条数（纯推导） ----------------
n_block = CL.alpha_km_n_lath(TEND, AKM)          # = α·(Ms − T_end)
n_blk_int = CL.n_lath_int(TEND, AKM)
print("\n" + "-" * 96)
print("① C-2 `n(T) = α_KM·(M_s − T_end)`  —— **纯推导**（`windowB_closure.py:142-158`）")
print(f"     n(T_end) = {AKM} × ({MS} − {TEND}) = {n_block:.4f}  ⇒ 取整 **{n_blk_int}**")

# ---------------- ② KM 分数律（体积分数） ----------------
T1 = CL.T_of_k(1, AKM)
f_end = 1.0 - math.exp(-AKM * (MS - TEND))
print("\n" + "-" * 96)
print("② KM 分数律 `f(T) = 1 − exp[−α(M_s − T)]`  —— **文献律**（`windowB_km.py:232`）")
print(f"     T_1 = M_s − 1/α = {T1:.3f} K      f(T_end) = {f_end:.8f}")

# ---------------- ③ 两者的一致性（**内部自洽判据**） ----------------
print("\n" + "-" * 96)
print("③ ★ **自洽检查 1**：C-2 与 KM 律的**每档增量**是否一致")
print("     档宽 ΔT = 1/α = %.3f K" % (1.0 / AKM))
# ⚠ **符号更正（2026-10-05，我的脚本第一版错了）**：`T_of_k(1)` 已经是 `T_1`（**上**端），
#   所以"首档"的**下端**是 `T_2 = T_1 − 1/α`。第一版把两者写反 ⇒ 报出负增量。
t_hi, t_lo = T1, T1 - 1.0 / AKM
d_km = n_blk_int * ((1 - math.exp(-AKM * (MS - t_hi)))
                    - (1 - math.exp(-AKM * (MS - t_lo))))
d_c2 = CL.alpha_km_n_lath(t_hi, AKM) - CL.alpha_km_n_lath(t_lo, AKM)
print(f"     首档区间 T: {t_lo:.3f} → {t_hi:.3f} K")
print(f"     KM 律首档增量  = {d_km:.4f}")
print(f"     C-2 首档增量   = {d_c2:.4f}")
print(f"     ⇒ {'**一致** ✅（两者是同一个量的积分/微分）' if abs(d_km - d_c2) < 1.0 else '**不一致 ⇒ 必须查** ❌'}")

# ---------------- ④ 步数轴（C-5） ----------------
n_stage = max(int(math.floor(AKM * (T1 - TEND))), 1)
steps_eff = QSMAX * n_stage if QS else STEPS
b_wrong = CL.beta_h_min(STEPS, DX, PT)
b_right = CL.beta_h_min(steps_eff, DX, PT)
BH = float(g("beta_h", 6.477))
print("\n" + "-" * 96)
print("④ C-5 `beta_h_min` 的**步数轴**（`R623 §11.2`）")
print(f"     档数 = floor(α·(T_1 − T_end)) = {n_stage}")
print(f"     真实步进轴（qs_clock={QS}）= {QSMAX} × {n_stage} = **{steps_eff}**"
      f"（`--steps` = {STEPS} 是**上界**）")
print(f"     beta_h_min(轴={STEPS:>6}) = {b_wrong:.4f}   对 --beta-h {BH}："
      f"{'违反' if b_wrong > BH else '满足'}")
print(f"     beta_h_min(轴={steps_eff:>6}) = {b_right:.4f}   对 --beta-h {BH}："
      f"{'违反' if b_right > BH else '满足'}")

# ---------------- ⑤ 表示上限（nv vs 物理要求） ----------------
print("\n" + "-" * 96)
print("⑤ ★ **自洽检查 2**：`nv` 够不够表示 C-2 要求的板条数")
print(f"     n(T_end) = {n_blk_int}    nv = {NV}")
_trunc = NV < n_blk_int
print(f"     ⇒ {'**受限**（nv < n）⇒ 结论必须标注「截断」⚠' if _trunc else '**够**（nv ≥ n）✅'}")

# ---------------- ⑥ 块厚（几何自洽） ----------------
w_block = n_blk_int * PT
print("\n" + "-" * 96)
print("⑥ ★ **自洽检查 3**：块厚 `W_block = n·t` 与 `L_box`、与文献带的关系")
print(f"     W_block = {n_blk_int} × {PT*1e9:.0f} nm = **{w_block*1e6:.2f} µm**")
print(f"     L_box   = {L*1e6:.2f} µm")
print(f"     ⇒ {'**几何上放得下** ✅' if w_block <= L else '**放不下 ⇒ 几何 veto** ❌'}")
print(f"     文献带 W_BLOCK_BAND_UM = {CL.W_BLOCK_BAND_UM}"
      f"（⚠ 该带在 `windowB_closure.py:118` **自注【仍未检索到】**）")

# ---------------- ⑦ 体积律（natural） ----------------
v_lath = PT * PL * PW
v_box = L ** 3
print("\n" + "-" * 96)
print("⑦ natural 体积律 `N_lath = f_KM·V_box/V_lath`（`R606 §3`）")
print(f"     V_lath = {v_lath*1e18:.4f} µm³   V_box = {v_box*1e18:.3f} µm³")
print(f"     N_lath(物理要求) = {v_box/v_lath*f_end:.0f} 根")
print(f"     本盒可表示 nv = {NV} ⇒ 达到分数 f ≈ {NV*v_lath/v_box*100:.2f}%")

print("\n" + "=" * 96)
print("★ 层次① 结论：以上 3 条自洽检查（③⑤⑥）必须**全部通过**；")
print("  任一不过 ⇒ 回 ② 重查，**不得**进 ⑧ 生产。")
print("=" * 96)
