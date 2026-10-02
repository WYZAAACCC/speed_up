#!/bin/bash
# _r581_resume_probe.sh --- 断点续跑：**文档怎么规划的 + 引擎持有哪些状态**
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① 文档里关于"续跑/断点"的规划 ════'
grep -rn '续跑\|断点\|可恢复' --include='*.md' . 2>/dev/null | head -12 | cut -c1-136 | sed 's/^/  /'
echo '  （以上为全部命中）'
echo
echo '════ ② 引擎持有哪些**需要保存才能续跑**的状态 ════'
echo '  ── windowB_surface.py 的 LevelSetMulti ──'
grep -n 'def __init__\|self\.phi\|self\.seeds\|self\.rng\|self\.t_s\|self\.it *=\|self\.nuc' \
  windowB_surface.py 2>/dev/null | head -20 | cut -c1-112 | sed 's/^/    /'
echo
echo '  ── windowB_pf3d.py 的 PF3D ──'
grep -n 'def __init__\|self\.phi\|self\._h\|self\.work\|self\.fft\|self\.Eh' \
  windowB_pf3d.py 2>/dev/null | head -14 | cut -c1-112 | sed 's/^/    /'
echo
echo '════ ③ 快照**存了什么** vs **续跑需要什么** ════'
PY=/root/miniconda3/envs/ml/bin/python
$PY - <<'PYEOF'
import numpy as np, os
p = '_exp/_bk_blk/dry_BK6/snap_00250.npz'
if os.path.exists(p):
    z = np.load(p)
    print('  快照的键（%d 个）：' % len(z.files))
    for k in z.files:
        a = z[k]
        print('    %-16s %-20s %s' % (k, str(a.shape), a.dtype))
    print()
    need = {
        'region（场号图）': 'region' in z.files,
        '整场 φ（level set）': 'phi' in z.files,
        '界面带 φ（逐场）': 'band_val' in z.files,
        '时刻 t_s': 't_s' in z.files,
        '步号 step': 'step' in z.files,
        '惯习面/坐标轴': 'n_hab' in z.files,
        '变体映射 vmap': 'vmap_keys' in z.files,
        'RNG 状态': any('rng' in k.lower() or 'random' in k.lower() for k in z.files),
        '形核位点池 / 已用位点': any('site' in k.lower() or 'pool' in k.lower() for k in z.files),
        '温度/冷却进度': any('T_' in k or 'temp' in k.lower() for k in z.files),
        '弹性工作态（FFT/应变）': any('eps' in k.lower() or 'fft' in k.lower() for k in z.files),
        '记账/closure 状态': any('acc' in k.lower() or 'clo' in k.lower() for k in z.files),
    }
    print('  ── 续跑需要的东西，快照里有吗 ──')
    for k, v in need.items():
        print('    %-28s %s' % (k, '✅ 有' if v else '**❌ 没有**'))
PYEOF
echo
echo '════ ④ 引擎是不是**确定性**的（决定"重跑"能不能等价于"续跑"）════'
echo '  R163b 的实测结论（本会话）：给定同 seed，15–19 个主状态列**逐位相同**（NaN 感知比较）'
echo '  ⇒ 确定性 ✅ ⇒ **重跑给出同一条轨迹，但要从 step 0 重算**（**不等于续跑**）'
