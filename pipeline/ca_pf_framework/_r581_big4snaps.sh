#!/bin/bash
# _r581_big4snaps.sh --- 先看那 16 个快照的规模（规划内存与时间）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
printf '  %-10s %-14s %-12s %s\n' '臂' '快照' '字节' 'human'
echo '  ------------------------------------------------------------------'
tot=0
for t in p2_b3 p2_b5 p2_b5ov p2_b5ps; do
  for s in 00000 00200 00400 00600; do
    f="_exp/_bk_p2/dry_$t/snap_$s.npz"
    if [ -f "$f" ]; then
      b=$(stat -c%s "$f")
      tot=$((tot + b))
      printf '  %-10s %-14s %-12s %s\n' "$t" "snap_$s" "$b" "$(du -h "$f" | cut -f1)"
    else
      printf '  %-10s %-14s %s\n' "$t" "snap_$s" '（缺）'
    fi
  done
done
echo '  ------------------------------------------------------------------'
printf '  合计 %s 字节（约 %.1f GB，压缩后）\n' "$tot" "$(echo "$tot/1073741824" | bc -l)"
echo
echo '  ── 其中一个快照的键与规模（看 band_* 有多大）──'
PY=/root/miniconda3/envs/ml/bin/python
$PY - <<'PYEOF'
import numpy as np, os
p = '_exp/_bk_p2/dry_p2_b3/snap_00600.npz'
if not os.path.exists(p):
    print('  （没有 %s）' % p); raise SystemExit
z = np.load(p)
print('  文件 %s（%.1f MB）' % (p, os.path.getsize(p)/1e6))
tot = 0
for k in z.files:
    a = z[k]
    b = a.nbytes
    tot += b
    print('    %-16s %-22s %-10s %8.1f MB' % (k, str(a.shape), str(a.dtype), b/1e6))
print('  解压后合计 %.1f MB' % (tot/1e6))
# 关键：band_fld 的取值数（= 场数 + 1）
if 'band_fld' in z.files:
    f = np.asarray(z['band_fld']).ravel()
    u = np.unique(f)
    print('  band_fld 取值 %d 个：%s%s' % (u.size, u[:12], '…' if u.size > 12 else ''))
if 'region' in z.files:
    r = np.asarray(z['region'])
    ks = sorted(set(int(x) for x in np.unique(r)) - {0})
    print('  region 里的场号 %d 个' % len(ks))
PYEOF
