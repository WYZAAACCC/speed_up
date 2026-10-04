#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_maturefill.py --- 用**末态实测的成熟板条体积**算「填满盒子需要多少根」。

## 为什么不能用 `--plate-*`
`--plate-L/W/T = 1000×500×510 nm` 是 **`stack` 通道的播种尺寸**，不是成熟尺寸。
成熟板条是**长大并停止**之后的实际体积 ⇒ 必须从**跑完的算例**里读。

## 数据源
`t5N276F`（对照臂）已跑到 **T_end = 298 K**（降温结束 ⇒ 形核/长大停止）：
`series.csv` 末行的 `Vt`（总体积）、`nslab_n`（显著片数）、`vols`（**逐场体积**）。

AGENTS.md §3.6：`/mnt/f` 的 9p 读会静默给旧数据 ⇒ 反复读到与 `wc -l` 一致。
"""
import csv
import os
import subprocess
import sys

BASE = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5/dry_%s/series.csv"
V10 = 10.0 ** 3          # 10 µm 盒 = 1000 µm³
V5 = 5.0 ** 3            # 5 µm 盒 = 125 µm³


def robust_rows(p):
    n = int(subprocess.check_output(["wc", "-l", p]).split()[0])
    rows = []
    for _ in range(8):
        with open(p, "r", newline="", encoding="utf-8", errors="replace") as fh:
            rr = list(csv.DictReader(fh))
        if len(rr) >= len(rows):
            rows = rr
        if len(rows) >= n - 1:
            break
    return rows, n


def main():
    for tag in (sys.argv[1:] or ["t5N276F"]):
        p = BASE % tag
        if not os.path.exists(p):
            print("%s ⚠ 无 CSV" % tag)
            continue
        rows, n = robust_rows(p)
        print("══ %s ══ wc -l=%d 解析=%d 一致=%s" % (tag, n, len(rows), len(rows) >= n - 1))
        # 取最后一行**有 vol 数据**的
        last = None
        for r in reversed(rows):
            if (r.get("vols") or "").strip():
                last = r
                break
        if last is None:
            print("  ⚠ 没有 vols 行")
            continue
        print("  末行 step=%s  Vt=%s µm³  nslab_n=%s  n_lath=%s  w_lath=%s  a_lath=%s  n_var_sig=%s"
              % (last.get("step"), (last.get("Vt") or "")[:9], last.get("nslab_n"),
                 (last.get("n_lath") or "")[:8], (last.get("w_lath") or "")[:8],
                 (last.get("a_lath") or "")[:8], last.get("n_var_sig")))
        vols = [float(x) for x in (last.get("vols") or "").split("/") if x.strip()]
        vols = [v for v in vols if v > 0]
        if not vols:
            print("  ⚠ vols 解析为空")
            continue
        vols.sort()
        Vt = float(last.get("Vt") or 0.0)
        print("  逐场体积（µm³）：n=%d  最小=%.4f  中位=%.4f  均值=%.4f  最大=%.4f  合计=%.2f"
              % (len(vols), vols[0], vols[len(vols) // 2],
                 sum(vols) / len(vols), vols[-1], sum(vols)))
        print("  记账：`Vt`=%.4f µm³ vs 逐场合计=%.4f µm³（差 %.1f%%）"
              % (Vt, sum(vols), 100 * abs(Vt - sum(vols)) / max(Vt, 1e-30)))
        print()
        print("  ★ 用**成熟板条体积**算「填满盒子需要多少根」：")
        for lab, v in (("中位", vols[len(vols) // 2]), ("均值", sum(vols) / len(vols)),
                       ("最大", vols[-1])):
            print("     %s = %.4f µm³ ⇒ 填满 10 µm 盒(1000 µm³) = **%.0f 根**；"
                  "填满 5 µm 盒(125 µm³) = %.0f 根"
                  % (lab, v, V10 / v, V5 / v))
        # 若"成熟板条"用最大片（最接近完整长成的单片）
        print()
        print("  ★ 与各需求对照（用中位数 %.4f µm³）：" % vols[len(vols) // 2])
        nm = vols[len(vols) // 2]
        for lab, need in (("`--B 3`×`n(T_end)=23` = 69 根", 69),):
            print("     %s ⇒ 体积 %.2f µm³ = 10 µm 盒的 %.2f%%"
                  % (lab, need * nm, 100 * need * nm / V10))
        print("     填满 10 µm 盒需 %.0f 根 = 该需求的 **%.1f 倍**"
              % (V10 / nm, (V10 / nm) / 69))
        print("     N=160 f64 物化实测 nv_max=270 ⇒ 最多填 %.1f%%（10 µm 盒）"
              % (100 * 270 * nm / V10))


if __name__ == "__main__":
    main()
