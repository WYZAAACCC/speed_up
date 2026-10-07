#!/bin/bash
# _r457_prof2.sh —— ★★ **把"一次性构造"与"每步耗时"分开**
#
# `_r456` 的 profile 把两者混在一起：`lambda_packed`（造 FFT 空间的 Green 算子 (N³,6,6)）
# 一次性花了 ~84 s，而每步只有几秒。要回答"GPU 能不能帮上忙"，
# 必须知道**每步**里 FFT / einsum / argmin 各占多少。
#
# 做法：同一配置跑 **2 步** 与 **14 步**，两次 profile 相减 ⇒ 干净的**每步**分解。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

LATHS="1,3,5,7,9,11,1,3,5,7,9,11,1,3,5,7,9,11,1,3,5,7,9,11"
BASE="--N 112 --dx-nm 62.5 --every 1 --snap-every 1 --pair-every 1 \
--norm-smooth 0 --nthreads 3 --reinit-dt 1e-4 \
--laths $LATHS --plate-L 1000 --plate-W 500 --plate-T 510 \
--gamma0 0.25 --beta-h 6.477 \
--grow-stack --nuc-law athermal --nuc-init 6 --nuc-fresh-every 4 \
--alpha-km 0.041739 --T-end 298.0 --facet-proj 0 --facet-excl 0"

for S in 2 14; do
  rm -rf "_exp/_bk_mb/dry_prof$S"
  echo "############ steps=$S  $(date '+%F %T')"
  PYTHONUNBUFFERED=1 "$PY" -m cProfile -o "_r457_p$S.out" _bk_exp.py $BASE \
      --steps $S --tag "prof$S" --out _exp/_bk_mb > "_r457_$S.log" 2>&1
  echo "  退出码=$?"
done

echo
echo "======== 相减：**每步**的时间分解（12 步的差 / 12） ========"
"$PY" - <<'PYEOF'
import pstats

def load(f):
    return pstats.Stats(f)

s2, s14 = load('_r457_p2.out'), load('_r457_p14.out')
t2, t14 = s2.total_tt, s14.total_tt
n = 12.0
print('  总自身时间：%d 步 = %.1f s ；%d 步 = %.1f s' % (2, t2, 14, t14))
print('  ⇒ **每步**（相减）= %.2f s  ← 这才是"每步成本"' % ((t14 - t2) / n))

def merged(st):
    d = {}
    for (fn, _, fname), (cc, nc, tt, ct, _) in st.stats.items():
        key = '%s:%s' % (fname.split('/')[-1], fn)
        d[key] = d.get(key, 0.0) + tt
    return d

m2, m14 = merged(s2), merged(s14)
keys = set(m2) | set(m14)
diff = sorted(((m14.get(k, 0.0) - m2.get(k, 0.0)) / n, k) for k in keys)
print('\n  按**每步自身时间**排前 18：')
print('    %-12s %-52s %s' % ('每步(s)', '函数', '占比'))
tot = (t14 - t2) / n
for v, k in reversed(diff[-18:]):
    if v <= 0.0005:
        continue
    print('    %-12.4f %-52s %.1f%%' % (v, k[:52], 100 * v / tot))

groups = {
    'FFT (scipy/np)':      ('fft',),
    'einsum':              ('einsum',),
    'argmin/region':       ('argmin', 'region'),
    'linalg(inv/norm)':    ('inv', 'norm', 'linalg'),
    'upwind/梯度':          ('gradient', 'upwind', '_upwind'),
    '测量/输出':            ('measure', 'blocks', 'savez', 'zlib', 'compress'),
    '邻域/roll/label':      ('roll', 'label', 'distance_transform',
                            'binary_dilation'),
}
print('\n  **分组**（每步）：')
for name, ks in groups.items():
    acc = sum(max(0.0, m14.get(k, 0.0) - m2.get(k, 0.0)) / n
              for k in keys if any(x in k.lower() for x in ks))
    print('    %-20s %8.4f s/步  （%.1f%%）' % (name, acc, 100 * acc / tot))
print('    %-20s %8.4f s/步' % ('合计（分组和）', 0.0))
PYEOF
