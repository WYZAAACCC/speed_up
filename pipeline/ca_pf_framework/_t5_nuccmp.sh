#!/bin/bash
# _t5_nuccmp.sh --- 对比本臂与 abA 的**形核调度参数**（为什么 abA 有多块）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① 本启动器传给引擎的形核相关参数 ════'
grep -nE "nuc-|grow-stack|var-rule" _t5_short.py | sed 's/^/  /'
echo
echo '════ ② 本臂（t5H3）启动横幅里的形核调度行 ════'
grep -nE 'fresh-every|N8 自动推导|block-target|nuc-init|grow-stack|引擎路径' \
  _w2_t5_short_t5H3.log 2>/dev/null | head -8 | cut -c1-130 | sed 's/^/  /'
echo
echo '════ ③ abA 启动横幅里的同类行（找它的日志）════'
for f in _r445_abA.log _r426_abA.log; do
  [ -f "$f" ] || continue
  echo "  ── $f ──"
  grep -nE 'fresh-every|N8 自动推导|block-target|nuc-init|grow-stack|引擎路径|var-rule' \
    "$f" 2>/dev/null | head -8 | cut -c1-130 | sed 's/^/     /'
done
echo
echo '════ ④ abA 实际用过的命令行（若检查点里存了 cmdline）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import glob, os
import numpy as np
for d in ('_exp/_bk_mb/dry_abA/ckpt',):
    fs = sorted(glob.glob(os.path.join(d, '*.npz')))
    if not fs:
        print('  %s ⚠ 无检查点' % d); continue
    with np.load(fs[0], allow_pickle=False) as z:
        if 'cmdline' in z.files:
            s = str(np.asarray(z['cmdline']).item())
            print('  abA 的 cmdline（%d 字符）：' % len(s))
            import re
            for k in ('nuc-fresh-every', 'nuc-init', 'grow-stack', 'var-rule',
                      'nuc-block-target', 'nuc-harden-f', 'laths'):
                m = re.search(r'--%s[= ]([^\s]+)' % k, s)
                print('     --%-18s = %s' % (k, m.group(1) if m else '（未传）'))
        else:
            print('  ⚠ 检查点里没有 cmdline')
PYEOF
