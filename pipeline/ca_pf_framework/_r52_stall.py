#!/usr/bin/env python3
"""R52: **端面"停住"是真的，还是量具伪影？**

## 为什么要问
§34 实测：`dry_mb1s62` 在 500–1000 步窗口里 `tip` 的 `Δsep/2` 只走 **+8.2 nm**，
而积分预言 521.8 nm（比值 63.6）。但 `tip_sep_nm` 是**面簇中位位置之差**
（`_bk_measure.face_separations`）—— 若板条**尖端变钝/变圆**，
满足 `(n·a)²>0.81` 的胞会变少且位置内移，**读数会停住而实体仍在伸长**。

## 交叉口径（三者互相独立）
1. `tip_sep_nm` —— 面簇中位位置之差（金标准，但要 φ）
2. `a_lath`     —— 该场沿自身 `a` 轴的**包围跨度**（`_linear_extent`）
3. `n_tip`      —— tip 档的**胞数**（若尖端变钝，胞数会掉）
另看 `f3_area_m2` / `nf3`（板条之间的 F3 面积）与 `E_el_J`（弹性能）。
"""
import csv
import math
import os
import sys

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
D = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_mb1s62'
rows = list(csv.DictReader(open(os.path.join(D, 'series.csv'))))


def f(r, k):
    try:
        v = float(r.get(k, ''))
        return v if math.isfinite(v) else float('nan')
    except (TypeError, ValueError):
        return float('nan')


print('臂 %s  行数 %d' % (D, len(rows)))
cols = ['step', 'tip_sep_nm', 'a_lath', 'n_tip', 'dG_tip', 'v_tip_nabs',
        'nf3', 'f3_area_m2', 'E_el_J', 'box_touch_core']
cols = [c for c in cols if c in rows[0]]
print()
print('  %-6s %-12s %-12s %-8s %-12s %-11s %-8s %s'
      % ('step', 'tip_sep_nm', 'a_lath(nm)', 'n_tip', 'dG_tip',
         'v_tip_nabs', 'nf3', 'f3_area(µm²)'))
for r in rows:
    st = int(r['step'])
    if st % 100 and st != int(rows[-1]['step']):
        continue
    a = f(r, 'a_lath')
    print('  %-6d %-12.1f %-12.1f %-8s %-12.4e %-11.4f %-8s %.4f'
          % (st, f(r, 'tip_sep_nm'), a * 1e9 if math.isfinite(a) else float('nan'),
             str(r.get('n_tip', ''))[:8], f(r, 'dG_tip'), f(r, 'v_tip_nabs'),
             str(r.get('nf3', ''))[:8], f(r, 'f3_area_m2') * 1e12))
print()
# 分段速率对照
print('=== 分段速率：面间距口径 vs 包围跨度口径')
print('  %-14s %-14s %-14s %s' % ('窗口', 'd(tip_sep)/dstep', 'd(a_lath)/dstep', '一致?'))
for lo, hi in ((0, 500), (500, 1000), (1000, 1500), (0, 1500)):
    seg = [r for r in rows if lo <= int(r['step']) <= hi]
    out = []
    for key in ('tip_sep_nm', 'a_lath'):
        xs = [int(r['step']) for r in seg]
        ys = [f(r, key) * (1e9 if key == 'a_lath' else 1.0) for r in seg]
        pts = [(x, y) for x, y in zip(xs, ys) if math.isfinite(y)]
        if len(pts) >= 3:
            n = len(pts)
            mx = sum(p[0] for p in pts) / n
            my = sum(p[1] for p in pts) / n
            num = sum((p[0] - mx) * (p[1] - my) for p in pts)
            den = sum((p[0] - mx) ** 2 for p in pts)
            out.append(num / den if den else float('nan'))
        else:
            out.append(float('nan'))
    cons = ('**同号**' if (out[0] > 0) == (out[1] > 0) else '**反号 ⚠**')
    print('  %-14s %+-14.4f %+-14.4f %s'
          % ('%d–%d' % (lo, hi), out[0], out[1], cons))
print()
print('★ 判读：')
print('  · 若 `a_lath` 在 500–1000 里**继续增长**而 `tip_sep_nm` 停住')
print('    ⇒ **停住是面簇口径的伪影**（尖端变钝 ⇒ 该档胞内移/变少）。')
print('  · 若两者都停住 ⇒ 端面**真的**停住了（物理或数值 arrest）。')
