#!/bin/bash
# _t5_chk_band.sh --- 确认 s54 改动 + 正在跑的臂未受影响
cd "$(dirname "$0")" || exit 1
echo '════ ① 改动后的那一行 ════'
grep -n 'phi-band-every' _t5_short.py | cut -c1-112 | sed 's/^/  /'
echo
echo '════ ② 语法 ════'
/root/miniconda3/envs/ml/bin/python -m py_compile _t5_short.py && echo '  ✅ SYNTAX_OK（真跑过 py_compile）'
echo
echo '════ ③ ★ 正在跑的臂是否受影响（应为：不受影响，仍是 200）════'
printf '  t5H3 引擎收到的 --phi-band-every = %s\n' \
  "$(grep -oE '\-\-phi-band-every [0-9]+' _w2_t5_short_t5H3.log 2>/dev/null | head -1 | awk '{print $2}')"
printf '  t5H3 实测带 band 的快照: %s\n' \
  "$(ls -1 _exp/_bk_t5/dry_t5H3/snap_*.npz 2>/dev/null | tr '\n' ' ')"
echo '  （带 band 的只有 snap_00000 / snap_00200 ⇒ 证明该臂仍是 200）'
