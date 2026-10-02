#!/bin/bash
# _t5_ab2.sh --- ★★★★★ **两臂并行**：S4 简化的单变量 A/B（用户要求"多个仿真并行进行"）
#   A: --nuc-overlap-nm 62.5（1Δx，代码自带剂量–响应的最优 ⇒ **修复值**）
#   B: --nuc-overlap-nm 0   （旧默认 ⇒ **被审计的那个简化**）
#   其余**逐字相同**（含 abA 物理基线、13 项优化算子、断点续跑开关）
#   核：A 用 0-7，B 用 8-15（不相交，符合 P10）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LG=_w2_t5_ab2.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LG"; }
say '════ S4 单变量 A/B（N=160 / 10 µm / 60 步 / abA 物理 / 13 项优化算子 / 断点续跑）════'

$PY _t5_short.py --tag t5o62 --overlap-nm 62.5 --steps 60 --cores 0-7 \
   --mem-limit-gb 9.5 --archive-old > _w2_t5_ab2_A.log 2>&1 &
PA=$!
say "  A（overlap=62.5）pid=$PA  绑核 0-7"
sleep 20
$PY _t5_short.py --tag t5o0 --overlap-nm 0 --steps 60 --cores 8-15 \
   --mem-limit-gb 9.5 --archive-old > _w2_t5_ab2_B.log 2>&1 &
PB=$!
say "  B（overlap=0）  pid=$PB  绑核 8-15"
wait $PA; RA=$?
wait $PB; RB=$?
say "  A exit=$RA   B exit=$RB"
say ''
for t in t5o62 t5o0; do
  say "════ $t ════"
  grep -E '峰值 RSS|单步耗时|走到 step|检查点：|ckpt_[AB]' "_w2_t5_ab2_$([ "$t" = t5o62 ] && echo A || echo B).log" \
    | sed 's/^/  /'
  D=_exp/_bk_t5/dry_$t
  if [ -f "$D/series.csv" ]; then
    $PY - "$D/series.csv" "$t" <<'PYEOF'
import csv, sys
rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8', errors='replace')))
print('  %s：series %d 行，末步 %s' % (sys.argv[2], len(rows), rows[-1]['step']))
for c in ('nslab_n', 'nf3_col', 'nf3', 'nf2', 'nblk_sig', 'Vt', 'f_var', 'r_selfac',
          'n_lath', 'w_lath', 'a_lath', 'ths', 'box_touch', 'finite'):
    if c in rows[-1]:
        v = (rows[-1][c] or '')[:46]
        print('     %-12s = %s' % (c, v))
PYEOF
  else
    say "  ⚠ $D/series.csv 不存在"
  fi
done
say '=== T5 AB2 DONE ==='
