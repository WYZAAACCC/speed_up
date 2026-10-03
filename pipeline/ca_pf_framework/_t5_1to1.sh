#!/bin/bash
# _t5_1to1.sh --- ★★★★★ 代码核验：一个场是否**唯一**对应一根板条？
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `seed_plate` 的写入式（看它是否**累加**到同一个场）════'
sed -n '2790,2830p' windowB_surface.py | grep -nE 'phi\[|max\(|min\(|np\.where|sdf' | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ② 有没有**连通性**检查（"一个场只能有一块"）？════'
grep -nE 'connected|连通|label\(|ndimage\.label|components' windowB_surface.py _bk_exp.py 2>/dev/null \
  | grep -viE '^\s*#' | head -12 | cut -c1-150 | sed 's/^/  /'
echo '  ⇒ 若上面为空或与本议题无关 ⇒ **代码里没有"一场一块"的强制检查**'
echo
echo '════ ③ 有没有"两个同场相邻会**合并**"的处理？════'
grep -nE 'merge|合并|coalesc|union' windowB_surface.py _bk_exp.py 2>/dev/null | head -10 | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ④ 场的编号语义（`nv = nvar × m` 的注释）════'
grep -nE 'nvar.*m|nv = |每个变体|laths' _bk_exp.py 2>/dev/null | grep -iE 'nv|nvar|m ' | head -10 | cut -c1-155 | sed 's/^/  /'
echo
echo '════ ⑤ `phi` 的**更新式**（看是否有把 φ 拉回正的项）════'
grep -nE 'phi\[.*\]\s*[-+]?=|phi =|np\.maximum|np\.minimum' _bk_exp.py 2>/dev/null | head -14 | cut -c1-150 | sed 's/^/  /'
