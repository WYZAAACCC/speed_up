#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_law_verdict.py —— **哪条律预测了实测根数**（`R623 §13` 的复核，⑥→② 回环）。

## 要回答的问题（可 FAIL）
  `R623 §13` 发现：C-2 说"每柱 23 根"，而基线实测 **4.6 根/块**（73 根 / 16 块）。
  ⇒ 究竟哪条律对？把**候选律**与**实测**摆在一起算。

## 候选律（都在框架里，各有出处）
  A. C-2 累计：`n(T) = α_KM·(M_s − T)`            （线性，T=T_end）
  B. KM 分数律：`N = N_end·(1 − e^{−α(M_s−T)})`   （指数，T=T_end）
  C. 分档计数：档数 `= floor(α·(M_s−T_end))`，每档 1 根  （= A 的取整）
  D. 四者一致的前提：`t` 与 `V_box` 的几何

## 实测（唯一权威，硬步骤 A）
  每个算例自己的 `meta.json` + `series.csv` 末行的 `nslab_n` / `nblk_sig` / `blk_laths`。
"""
import csv
import json
import os
import sys

sys.path.insert(0, ".")
import windowB_closure as CL  # noqa: E402

CAND_DIRS = [
    "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
    "/mnt/f/speed_up/_exp/_bk_t5",
]
TAGS = sys.argv[1:] or ["dry_t10B9", "dry_t10PRT2_b3_1005_1213"]


def find(tag):
    for base in CAND_DIRS:
        d = os.path.join(base, tag)
        if os.path.isdir(d):
            return d
    return None


print("=" * 100)
print("哪条律预测了实测根数？（R623 §13 的复核）")
print("=" * 100)
for tag in TAGS:
    d = find(tag)
    print(f"\n{'=' * 100}\n【{tag}】  dir={d}")
    if d is None:
        print("  **目录不存在** ⇒ 跳过")
        continue
    mp = os.path.join(d, "meta.json")
    sp = os.path.join(d, "series.csv")
    if not os.path.exists(mp):
        print("  **无 meta.json** ⇒ 跳过")
        continue
    meta = json.load(open(mp, encoding="utf-8"))
    ea = meta.get("exp_args", {}) or {}

    def g(k, dflt=None):
        v = ea.get(k, meta.get(k, dflt))
        return dflt if v is None else v

    akm = float(g("alpha_km", CL.ALPHA_KM_REF))
    tend = float(g("T_end", 298.0))
    nv = int(g("nv", 0))
    N = int(g("N", 0))
    dx = float(g("dx_nm", 62.5)) * 1e-9
    pl = float(g("plate_L", 1000.0)) * 1e-9
    pw = float(g("plate_W", 500.0)) * 1e-9
    pt = float(g("plate_T", 510.0)) * 1e-9
    qs = int(g("qs_clock", 0) or 0)
    qsm = int(g("qs_max_relax", 0) or 0)
    L = N * dx
    ms = CL.M_S_TI64
    print(f"  参数（meta.json）: N={N} dx={dx*1e9:.1f}nm L={L*1e6:.3f}µm nv={nv} "
          f"α_KM={akm} T_end={tend} qs_clock={qs} qs_max_relax={qsm}")
    print(f"                    plate = {pl*1e9:.0f}×{pw*1e9:.0f}×{pt*1e9:.0f} nm")

    # ---- 候选律 ----
    n_c2 = CL.alpha_km_n_lath(tend, akm)
    n_int = CL.n_lath_int(tend, akm)
    f_end = 1.0 - pow(2.718281828459045, -akm * (ms - tend))
    print(f"\n  候选律（到 T_end = {tend} K）：")
    print(f"    A C-2 累计        n = α·(M_s−T) = {akm}×{ms-tend:.0f} = **{n_c2:.3f}**")
    print(f"    B KM 分数律×N_end  = f×n = {f_end:.6f}×{n_int} = **{f_end*n_int:.3f}**")
    print(f"    C 分档计数         = floor(α·ΔT) = **{n_int}**")
    n_ratio = L / pt
    print(f"    D 几何层数 L/t     = {L*1e9:.0f}/{pt*1e9:.0f} = **{n_ratio:.3f}**"
          f"  （盒子沿 t 方向能放几层）")

    # ---- 实测 ----
    if not os.path.exists(sp):
        print("\n  **无 series.csv** ⇒ 拿不到实测根数")
        continue
    rows = list(csv.DictReader(open(sp, encoding="utf-8")))
    if not rows:
        print("\n  **series.csv 空**")
        continue
    last = rows[-1]
    nslab = last.get("nslab_n", "?")
    nblk = last.get("nblk_sig", "?")
    bl = last.get("blk_laths", "?")
    print(f"\n  实测（series.csv 末行 step={last.get('step')}）：")
    print(f"    nslab_n   = {nslab!r}    （柱剖面里的段数）")
    print(f"    nblk_sig  = {nblk!r}    （块数）")
    print(f"    blk_laths = {bl!r}")
    try:
        _ns = int(float(nslab))
        _nb = int(float(nblk)) if nblk not in ("", None) else 0
        if _nb > 0:
            print(f"    ⇒ **每块平均根数 = {_ns}/{_nb} = {_ns/_nb:.2f}**")
            print(f"    ⇒ 与 A（{n_c2:.2f}）差 {abs(_ns/_nb - n_c2)/max(n_c2,1e-9)*100:.0f}%；"
                  f"与 D（{n_ratio:.2f}）差 "
                  f"{abs(_ns/_nb - n_ratio)/max(n_ratio,1e-9)*100:.0f}%")
        print(f"    ⇒ 总根数 {_ns} 对 nv={nv}："
              f"{'**未填满**（差 %d）' % (nv-_ns) if _ns < nv else '**已满**'}")
    except (TypeError, ValueError):
        print("    （某列为空 ⇒ 无法算比值）")

print("\n" + "=" * 100)
print("★ 判读要点：把**每块平均根数**与 A/B/C/D 四个候选值比，最近的即最可能的律；")
print("  并注意 `nslab_n` 是**柱剖面段数**（口径见 `R50` 的 `nslab_nu` 去重列），")
print("  在多块体系里它**不等于**总根数 —— 两者必須分开读。")
print("=" * 100)
