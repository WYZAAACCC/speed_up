#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_p8_readout.py —— **⑧ 的核心读数**：判「块内根数」落在哪一侧。

## 判据（**逐字引自引擎 `_blk_verdict`**，见 `R625 §4.6.2`）
  * **主判据**：`blk_nprof == blk_laths` **且** `nblk_sig == 期望块数`（生产 = 9，`--nuc-block-target 9`）
  * `blk_nlath` 只作**上界**；`blk_nruns` 只作**诊断**（会多读）
  * ⚠ **`nslab_n` 在多块下"结构性无效"** ⇒ **不得**用它判成败

## 本脚本输出什么
  * 末行的块结构三件套（`nblk_sig` / `blk_laths` / `blk_span_nm`）；
  * **两套体积口径**下的总根数估计（`R624 §11.4`：引擎椭球 vs 物理足迹，差 3.0×）；
  * **落哪一侧**的判定（`R624 §6.5` / `R625 §4.6.1` 的预登记判据）。
"""
import csv
import os
import sys

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
TAG = sys.argv[1] if len(sys.argv) > 1 else "dry_t10PROD1"
T_UM = 0.250                      # 单根厚度 µm（`--eng-t-nm 250` 的**值**）
# ★★ 本工具第一版把"507 nm ≈ plate_T 510 nm"当成"量具对上" —— **那是巧合**。
#   两条独立证据（读数前必须先看，否则判据会错）：
#   ① `_bk_measure.py:176` 原文：
#      「`n_%d`（= `ths`，板条胞沿 `n*` 的**包围盒跨度**）**不是板条厚度**：
#        实测 `mb1s` 场 1 的包围跨度 624 → **2631 nm**，而由 φ 量出的
#        **两张宽面之间的距离**只有 780 → **732 nm** ⇒ 包围跨度被**碎片**与
#        **`n*` 与真实板条法向的 7.3° 夹角**撑大」
#   ② `507 / 62.5 = 8.11` 胞 ⇒ 与"`--eng-t-nm 250` 是全厚、`seed_plate` 用 `|d| ≤ t/2`"
#      一致（2×250 + 1 胞 = 507）⇒ **若引用 250 nm 必须声明它属哪套约定**。
#   ⇒ **判据改成"相邻层间距 ≈ 250 nm"**（厚度方向上第 k 层与第 k−1 层中心的距离），
#     而**不是**用包围盒跨度当厚度。
T_LAYER_NM = 250.0                # 单层的**厚度方向间距**（见 §4.6.3-3 的更正说明）
# ★★ 第三轮更正（同轮内，读 `_bk_exp.py:2028-2030`）：
#   引擎实际用的**核厚不是 250 nm**，而是
#       `t_nuc = (250 + --nuc-overlap-nm)`（`R28` 的"自动补厚度"；界面落在重叠区中面
#        ⇒ 每片被吃 `o/2`，于是把 `o` 加回去）
#   生产：`250 + 62.5 = **312.5 nm**`。
#   ⇒ 判"层间距"时**基准也要相应给两种**：`250`（名义）与 `312.5`（引擎实际）。
#   ⚠ 而 `blk_span_nm` 是**包围盒跨度**（含 ±1Δx 阶梯）⇒ 单根种子的理论跨度
#     ≈ `τ + 2Δx` = 437.5–562.5 nm；实测 507 nm **落在区间内** ⇒
#     **分辨力不足以判定"是否多除了一次 2"** ⇒ 登记为待判定（需专门探针）。
T_ENG_NM = 312.5                  # = 250 + 62.5（`--eng-t-nm` + `--nuc-overlap-nm`）
# 两套单根体积（R624 §11.4）
V_ELL = 0.3753                    # 引擎椭球 4/3·π·(R·elong)·R·(t/2)
V_PHYS = 0.1250                   # 物理足迹 1000×500×250 nm
B_TARGET = 9                      # --nuc-block-target

d = next((os.path.join(b, TAG) for b in BASES
          if os.path.exists(os.path.join(b, TAG, "series.csv"))), None)
if d is None:
    sys.exit(f"**找不到 {TAG}/series.csv**")
rows = list(csv.DictReader(open(os.path.join(d, "series.csv"), encoding="utf-8")))
print("=" * 96)
print(f"【{TAG}】 series.csv 行数 = {len(rows)}")
print("=" * 96)
if not rows:
    sys.exit("  尚无数据行")

hdr = list(rows[0].keys())
print(f"  表头 {len(hdr)} 列：step … nblk_sig 在第 "
      f"{hdr.index('nblk_sig')} 列，blk_laths 在第 {hdr.index('blk_laths')} 列")

print(f"\n{'step':>6} {'nblk_sig':>9} {'blk_laths':>10} {'blk_span_nm':>12} "
      f"{'nslab_nu':>9} {'nslab_n':>8} {'Vt(m³)':>12} "
      f"{'n(椭球)':>9} {'n(足迹)':>9}")
for r in rows[-8:]:
    vt = r.get('Vt') or ''
    try:
        vtf = float(vt)
        ne = f"{vtf / (V_ELL * 1e-18):.1f}"
        nph = f"{vtf / (V_PHYS * 1e-18):.1f}"
    except (TypeError, ValueError):
        ne = nph = '—'
    print(f"{r.get('step',''):>6} {r.get('nblk_sig',''):>9} "
          f"{r.get('blk_laths',''):>10} {r.get('blk_span_nm',''):>12} "
          f"{r.get('nslab_nu',''):>9} {r.get('nslab_n',''):>8} {vt:>12} "
          f"{ne:>9} {nph:>9}")

last = rows[-1]
print("\n" + "=" * 96)
print("★ ⑧ 判定（按 `R625 §4.6.1/§4.6.2` 的预登记判据）")
print("=" * 96)
try:
    nb = int(last['nblk_sig'])
    bl = last['blk_laths']
    sp = last['blk_span_nm']
except (KeyError, TypeError, ValueError):
    nb, bl, sp = None, '', ''
print(f"  末行 step={last.get('step')}  nblk_sig={nb}  blk_laths={bl!r}  "
      f"blk_span_nm={sp!r}")
print(f"  期望块数（--nuc-block-target） = {B_TARGET}")

# 主判据
if nb is not None:
    ok_blk = (nb == B_TARGET)
    print(f"  · 主判据-1 `nblk_sig == {B_TARGET}` : "
          f"{'✅' if ok_blk else '⚠ 尚未到（当前 %d）' % nb}")
# blk_laths 的数值化（可能是 '1/3/5' 这种斜杠串）
nums = []
if bl:
    for x in str(bl).replace('|', '/').split('/'):
        try:
            nums.append(int(x))
        except ValueError:
            pass
if nums:
    n_bl = max(nums)
    print(f"  · 主判据-2 每块板条数（`blk_laths` 各块）= {nums}  max = {n_bl}")
    side = ("**C-2 预言那一侧**（~24）⇒ 9 块 × %d = **%d 根**"
            % (n_bl, B_TARGET * n_bl) if n_bl >= 18 else
            ("**几何容量那一侧**（~9.4）⇒ 9 块 × %d = **%d 根**"
             % (n_bl, B_TARGET * n_bl) if n_bl <= 12 else
             "**两者之间** ⇒ 按实测报"))
    print(f"  · ⇒ 落在 {side}")
    try:
        spf = float(str(sp).split('/')[0])
        # ★ 判据改成"相邻层间距"口径（见文件头）：层间距 = span/(n−1)（n≥2）
        if n_bl >= 2:
            gap = spf / (n_bl - 1)
            print(f"  · **相邻层间距** = `blk_span_nm`/(n−1) = {spf:.0f}/{n_bl-1} "
                  f"= **{gap:.0f} nm** vs 单层间距 {T_LAYER_NM:.0f} nm ⇒ "
                  f"比值 {gap / T_LAYER_NM:.2f}"
                  f"（应 ≈1；容差 ±40%，因 `blk_span_nm` 是**包围盒跨度**、"
                  f"会被碎片与 `n*` 偏角撑大）")
        else:
            print(f"  · 单层（n=1）⇒ 层间距判据**不适用**"
                  f"（`blk_span_nm`={spf:.0f} nm 是 1 层的包围盒跨度，"
                  f"不是厚度；见文件头两条证据）")
    except (TypeError, ValueError):
        pass
else:
    print(f"  · `blk_laths` = {bl!r} ⇒ **尚无可解析的每块根数**（可能仍是单块阶段）")
print("\n  ⚠ 纪律：`nslab_n` 多块下结构性无效；`blk_nlath` 只作上界；`blk_nruns` 只作诊断。")
print("  ⚠ 总根数有两套口径（椭球/足迹，差 3.0×）⇒ **两套都要报**。")