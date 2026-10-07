#!/usr/bin/env bash
# R513 —— 产出一份 **int16 快照**，好让 `_r512` 的"新旧都能读"能真正被验证。
#
# ## 为什么需要它（`_r512` 的 D1 FAIL 暴露的缺口）
#   任务(3) 把 `region` 从 int8 改成 int16（R474）。验收要求
#   「**新旧数据都能读**」，但我只验了**写**（`region()` 的 dtype 与数值），
#   **从没验过"读"**：`_r512` 扫了 400 个快照，**全是 int8、int16 有 0 个**。
#   原因：`abA` 在改动**之前**就起跑了，而改动**之后**的所有冒烟臂都写着
#   `--snap-every 99999`（= 不落快照）⇒ **int16 快照从来没存在过**。
#
# ## 本脚本
#   跑一个**很小很快**的臂，`--snap-every 40` ⇒ 产出若干 int16 快照。
#   ⚠ 只求"产出可读的快照"，**不产生任何物理结论**。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

OUT=_exp/_bk_mb
$PY -u _bk_exp.py --N 32 --dx-nm 62.5 --steps 120 --every 40 \
  --snap-every 40 --phi-band-every 0 --pair-every 40 --norm-smooth 0 \
  --nthreads 4 --laths 1,1,2,2,3,3 --plate-L 800 --plate-W 400 --plate-T 400 \
  --gamma0 0.25 --beta-h 6.477 --grow-stack --nuc-law athermal --nuc-init 2 \
  --alpha-km 0.041739 --T-end 600.0 --cool-rate 2.3524e6 \
  --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 --tag r513i16 --out $OUT \
  > _w2_r513_i16.log 2>&1
echo "退出码=$?"
echo "快照："
ls -1 $OUT/dry_r513i16/snap_*.npz 2>/dev/null | head -5
echo "dtype 检查："
$PY - <<'PYEOF'
import glob, numpy as np
fs = sorted(glob.glob('_exp/_bk_mb/dry_r513i16/snap_*.npz'))
for f in fs[:3] + fs[-1:]:
    z = np.load(f)
    print('  %s  region.dtype=%s  max=%d  band_fld=%s'
          % (f.split('/')[-1], z['region'].dtype, int(z['region'].max()),
             z['band_fld'].dtype if 'band_fld' in z.files else '—'))
PYEOF
