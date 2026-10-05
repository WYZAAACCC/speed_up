#!/bin/bash
# _t10_p2verdict2.sh --- 延长窗口的判决作业（轮询 60×180s = 3 小时）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10PRT2
OUT=_w2_t10_prt2_verdict2.log
: > "$OUT"
echo "══ 判决作业（延长窗口）启动 $(date '+%m-%d %H:%M:%S') ══" >> "$OUT"
MX=0
for i in $(seq 1 60); do
  MX=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
  if [ -n "$MX" ] && [ "${MX:-0}" -ge 100 ] 2>/dev/null; then
    echo "  [$(date '+%H:%M:%S')] 检测到 snap_$MX ⇒ 开始分析" >> "$OUT"
    break
  fi
  sleep 180
done
{
  echo "════ t10PRT2 判决  $(date '+%m-%d %H:%M:%S')  快照最大=${MX:-0} ════"
  echo
  echo "── ① ★ 死核率（同口径，基线 t10CL2 = 10/47 = 21%）──"
  $PY _t10_deadseed.py $TAG "${MX:-0}" 2>&1 | tail -20
  echo
  echo "── ② ★ 形核事件 / 场号唯一性（基线 47 事件、唯一性 1.000）──"
  $PY - <<PYEOF
import os, re
from collections import Counter
HERE = "$PWD"
txt = open(os.path.join(HERE, "_w2_t5_short_$TAG.log"), encoding="utf-8", errors="replace").read()
pat = re.compile(r"athermal 形核\*{0,2} @ step (\d+)：T=([\d.]+) K.{0,200}?场 (\d+)（累计", re.S)
ev = pat.findall(txt)
if ev:
    steps = [int(a) for a, _b, _c in ev]
    fields = [int(c) for _a, _b, c in ev]
    c = Counter(fields)
    dup = {k: v for k, v in c.items() if v > 1}
    print("  事件数 = %d ；不同场号 = %d ；唯一性 = %.3f" % (len(fields), len(c), len(c)/max(len(fields),1)))
    print("  步分布 =", sorted(set(steps)))
    print("  重复场号 =", dup if dup else "无 ⇒ 无一场多核")
    print("  场号全表 =", sorted(c))
else:
    print("  ⚠ 未解析到事件")
modes = re.findall(r"模式 \*\*(\w+)\*\*", txt)
print("  模式分布 =", dict(Counter(modes)))
PYEOF
  echo
  echo "── ③ 七项（逐连通分量 PCA）──"
  $PY _t10_seven.py $TAG "${MX:-0}" 2>&1 | tail -22
  echo
  echo "── ④ 全部场分量数 ──"
  $PY _t10_allfields.py $TAG "${MX:-0}" 2>&1 | tail -8
  echo
  echo "── ⑤ [SEEDCARVED] 统计 ──"
  echo -n "  行数 = "; grep -ac '\[SEEDCARVED\]' _w2_t5_short_$TAG.log 2>/dev/null
  echo -n "  ★ protected 含 0 的行数（应 0）= "
  grep -a '\[SEEDCARVED\]' _w2_t5_short_$TAG.log 2>/dev/null | grep -c 'protected=\[0[,\]]'
  echo "  被保护次数最多的场（前 6）："
  grep -a '\[SEEDCARVED\]' _w2_t5_short_$TAG.log 2>/dev/null \
    | grep -oE 'protected=\[[0-9, ]*\]' | sort | uniq -c | sort -rn | head -6 | sed 's/^/    /'
  echo
  echo "── ⑥ 两级清理 / 内存 / swap ──"
  echo -n "  播种清理 = "; grep -ac '\[SEEDCLEAN\]' _w2_t5_short_$TAG.log 2>/dev/null
  echo -n "  周期清理 = "; grep -ac '\[SEEDCLEAN-STEP\]' _w2_t5_short_$TAG.log 2>/dev/null
  free -m | sed -n '2,3p' | sed 's/^/  /'
  tail -2 _w2_t10_swapfix2.log 2>/dev/null | sed 's/^/  /'
  echo
  echo "  基线对照：t10CL2 = 47 事件/10 死核(21%)/⑦=100%/长厚 11.31/长宽 5.11/n_var_sig 4"
} >> "$OUT" 2>&1
cat "$OUT"
