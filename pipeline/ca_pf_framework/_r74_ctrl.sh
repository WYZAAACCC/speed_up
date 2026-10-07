#!/bin/bash
# _r74_ctrl.sh —— **正对照：新分支真的被走到了吗？**
#
# ## 依据（`R30_AUDIT_LEDGER.md` §77 的教训 2）
# 「改了代码不等于代码生效」。§76 就是因为 `excl` 恒为 `None` 而得出**错的**结论。
# ⇒ 必须先证明"挂了 `vmap` 之后，同一个算例的结果**变了**"。
#
# ## 做法（**最便宜**）
# 跑一条**很短的**臂（40 步，与 `m3fp10` 同配置），
# 与**归档的** `m3fp10`（那次 `excl` 是 None）的**同一步**行逐位比。
#   * **不同** ⇒ 新分支生效 ✅（因为唯一的差别就是 `excl`）
#   * **相同** ⇒ 仍然没生效 ⇒ 继续查
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
TAG=m3ctrl
rm -rf "_exp/_bk_mb/dry_$TAG"
echo "=== 正对照（40 步）  $(date '+%F %T')"
$PY -u _bk_exp.py --arm dry --N 96 --dx-nm 62.5 \
  --laths 1,1,1 --multi-block --block-gap-nm 0 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --facet-proj 10 \
  --steps 40 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag "$TAG" --out _exp/_bk_mb > "_w2_r74_${TAG}.log" 2>&1
echo "=== rc=$?"
echo '### 与归档 m3fp10 逐步对照（v0/vt 是最敏感的标量）'
$PY - <<'PY'
import csv, os
def rd(t, steps=(0, 20, 40)):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    if not os.path.exists(p):
        return {}
    return {int(r['step']): r for r in csv.DictReader(open(p))
            if int(r['step']) in steps}
a = rd('m3fp10'); b = rd('m3ctrl')
print('  %-6s %-24s %-24s %s' % ('step', 'm3fp10 (excl=None)', 'm3ctrl (excl=on)', '同否'))
same = True
for s in (0, 20, 40):
    if s not in a or s not in b:
        print('  %-6s （缺）' % s); continue
    va = a[s]['Vt']; vb = b[s]['Vt']
    eq = (va == vb)
    same = same and eq
    print('  %-6s %-24s %-24s %s' % (s, va[:22], vb[:22], '**同**' if eq else '**不同**'))
print()
print('  ⇒ 新分支生效 :', '❌ 仍相同 ⇒ 未生效' if same else '✅ 不同 ⇒ 生效')
PY
