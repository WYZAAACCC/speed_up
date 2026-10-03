#!/bin/bash
# _t5_v2band.sh --- 验 `t5V2` 的 band 分辨率（新启动器 ⇒ 应每 40 步）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "NOW = $(date '+%F %T')"
echo '════ t5V2 的快照与 band 标记 ════'
for S in $(ls -1 _exp/_bk_t5/dry_t5V2/snap_*.npz 2>/dev/null | sort); do
  H=$($PY -c "
import numpy as np
with np.load('$S',allow_pickle=False) as z:
    ks=set(z.files)
    print('Y' if 'band_fld' in ks else 'N')
" 2>/dev/null)
  printf '  %-46s band=%s\n' "$(basename $S)" "$H"
done
echo
echo '════ t5H3 对照（旧启动器 ⇒ 应每 200 步）════'
for S in snap_01000 snap_01040 snap_01080 snap_01120; do
  F=_exp/_bk_t5/dry_t5H3/$S.npz
  [ -f "$F" ] || continue
  H=$($PY -c "
import numpy as np
with np.load('$F',allow_pickle=False) as z: print('Y' if 'band_fld' in z.files else 'N')
" 2>/dev/null)
  printf '  %-46s band=%s\n' "$S" "$H"
done
echo
echo '════ 结论（预先写死）════'
echo '  若 t5V2 的 band 出现在 40 的倍数（含非 200 倍数）⇒ **它的判据② 分辨率是 40 步**'
echo '  若只在 200 的倍数 ⇒ 启动器的 s54 改动没生效（须记账）'
