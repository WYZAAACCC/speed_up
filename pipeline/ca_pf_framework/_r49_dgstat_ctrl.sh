#!/bin/bash
# R49 正对照：新落盘的 `dG` 统计量（p90/max）必须**存在、有序、且与中位数不同**。
#   已知答案：对任意样本，median ≤ p90 ≤ max 恒成立。
#   ⇒ 若违反，说明索引错位（`ed_by_face` 元组被我改长了，最容易错的就是下标）。
# 跑一条**很小的短臂**（N=32、200 步），既当接线对照，也当"统计量确实分开"的证据。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
# ⚠ 第一次用了 `--plate-L 400 --plate-W 200`（= 3.2 × 1.6 胞）⇒ 板条**退化**，
#   `tip` 档一个胞都没有（`_mm.sum() >= 20` 不成立）⇒ 正对照在**最要紧的那一档**
#   上"0/0"通过。这正是 `AGENTS.md §3` 教训 19 的变体：**先确认测试能看到目标现象**。
#   改用 1600 × 700 nm（12.8 × 5.6 胞，与 `mb1s` 同规格）。
TAG=r49dg
DIR="_exp/_bk_mb/dry_$TAG"
rm -rf "$DIR"
"$PY" -u _bk_exp.py --arm dry --N 48 --dx-nm 125 --laths 1,1 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 200 --every 20 --snap-every 20 --pair-every 40 --nthreads 2 \
  --tag "$TAG" --out _exp/_bk_mb > "_w2_${TAG}.log" 2>&1
echo "=== exit rc=$?"
"$PY" - "$DIR" <<'PY'
import csv, os, sys
d = sys.argv[1]
rows = list(csv.DictReader(open(os.path.join(d, 'series.csv'))))
print('CSV 行数 =', len(rows))
have = [c for c in ('dG_tip', 'dG_tip_p90', 'dG_tip_max', 'dG_side',
                    'dG_side_p90', 'dG_side_max', 'ed_tip_p90') if c in rows[0]]
print('新列在位 =', have)
ok_all = True
for tag in ('tip', 'side'):
    print('--- %s' % tag)
    print('   %-6s %-13s %-13s %-13s %s' % ('step', 'median', 'p90', 'max', '序'))
    n_ok = 0
    n_tot = 0
    for r in rows:
        try:
            med = float(r['dG_%s' % tag]); p90 = float(r['dG_%s_p90' % tag])
            mx = float(r['dG_%s_max' % tag])
        except (KeyError, ValueError):
            continue
        n_tot += 1
        good = (med <= p90 + 1e-6) and (p90 <= mx + 1e-6)
        n_ok += good
        if len(rows) <= 4 or r is rows[-1] or n_tot <= 2:
            print('   %-6s %-13.4e %-13.4e %-13.4e %s'
                  % (r['step'], med, p90, mx, 'OK' if good else '**乱序**'))
    print('   单调性 %d/%d' % (n_ok, n_tot))
    if n_ok != n_tot or n_tot == 0:
        ok_all = False
    # 统计量必须**真的分开**（否则等于没测）
    sp = [(float(r['dG_%s_max' % tag]) / float(r['dG_%s' % tag]))
          for r in rows if r.get('dG_%s' % tag) not in (None, '', '0.0')
          and float(r.get('dG_%s' % tag, 0) or 0) != 0.0]
    if sp:
        print('   max/median 比值: min=%.3f  max=%.3f' % (min(sp), max(sp)))
print('VERDICT =', 'PASS' if ok_all else 'FAIL')
PY
