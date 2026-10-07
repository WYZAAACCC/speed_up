#!/bin/bash
# _r456_prof.sh —— ★★ **单步耗时分解**（决定 GPU 能不能帮上忙）
#
# 只跑 2 步，用 cProfile 抓函数级耗时。
# 配置与 abA 逐字相同（N=112、25 场、3 线程），保证代表性。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

LATHS="1,3,5,7,9,11,1,3,5,7,9,11,1,3,5,7,9,11,1,3,5,7,9,11"
COMMON="--N 112 --dx-nm 62.5 --steps 2 --every 1 --snap-every 2 --pair-every 2 \
--norm-smooth 0 --nthreads 3 --reinit-dt 1e-4 \
--laths $LATHS --plate-L 1000 --plate-W 500 --plate-T 510 \
--gamma0 0.25 --beta-h 6.477 \
--grow-stack --nuc-law athermal --nuc-init 6 --nuc-fresh-every 4 \
--alpha-km 0.041739 --T-end 298.0 --facet-proj 0 --facet-excl 0"

rm -rf _exp/_bk_mb/dry_prof
echo "############ cProfile 跑 2 步  $(date '+%F %T')"
PYTHONUNBUFFERED=1 "$PY" -m cProfile -o _r456_prof.out _bk_exp.py $COMMON \
    --tag prof --out _exp/_bk_mb > _r456_prof.log 2>&1
echo "退出码=$?"

echo
echo "======== 按**累计时间**排前 25 ========"
"$PY" - <<'PYEOF'
import pstats
st = pstats.Stats('_r456_prof.out')
st.sort_stats('cumulative').print_stats(25)
PYEOF

echo
echo "======== 按**自身时间**排前 20 ========"
"$PY" - <<'PYEOF'
import pstats
st = pstats.Stats('_r456_prof.out')
st.sort_stats('tottime').print_stats(20)
PYEOF

echo
echo "======== 关键字聚合（FFT / argmin / einsum / upwind / reinit / 测量） ========"
"$PY" - <<'PYEOF'
import pstats
st = pstats.Stats('_r456_prof.out')
groups = {
    'FFT':      ('fft',),
    'argmin/region': ('argmin', 'region'),
    'einsum/弹性': ('einsum', 'sigma', 'elastic', 'Lam', 'lambda'),
    'upwind/推进': ('upwind', 'grad', 'advance', '_advance'),
    'reinit':   ('reinit', 'sussman'),
    '测量/输出': ('measure', 'blocks', 'snapshot', 'savez', 'csv'),
    '距离变换/邻域': ('distance_transform', 'binary_dilation', 'label', 'roll'),
}
tot = st.total_tt
for name, keys in groups.items():
    acc = 0.0
    for (fn, _, fname), (cc, nc, tt, ct, _) in st.stats.items():
        low = (fn + ' ' + fname).lower()
        if any(k.lower() in low for k in keys):
            acc += tt
    print('  %-16s 自身时间 %8.2f s  （%.1f%%）' % (name, acc, 100 * acc / tot))
print('  %-16s %8.2f s' % ('总自身时间', tot))
PYEOF
