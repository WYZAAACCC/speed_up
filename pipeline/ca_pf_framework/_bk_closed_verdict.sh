#!/bin/bash
# _bk_closed_verdict.sh —— 闭环算例（cl1 / cl1g）的**完整证据包**，一条命令跑完。
#   A. athermal 律核验 A-1..A-8（形核温度、有序比、块完整性、体积尺度）
#   B. 标准判决 V-1..V-8b（与归档同一套判据；V-8b 窗口随 plate.T 缩放）
#   C. 与归档 eng12 的**对照读数**（不同配置，只作上下文，不作单变量归因）
#   D. 工具自检（量具 / 引擎恒等性）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
LOG=_w2_bk_closed_verdict.log
: > "$LOG"
{
  echo "################ A. athermal 律核验（cl1 = 闭环主配置）"
  "$PY" -u _bk_athermal.py --root _exp/_bk_closed --tag cl1 2>&1
  echo
  echo "################ A'. 单变量隔离臂 cl1g（γ_F1 = 0.15，其余逐字相同）"
  "$PY" -u _bk_athermal.py --root _exp/_bk_closed --tag cl1g 2>&1 | tail -14
  echo
  echo "################ B. 标准判决（V-1..V-8b）—— cl1"
  "$PY" _bk_verdict.py --root _exp/_bk_closed --tag cl1 --arms dry \
      --ctrl-tag L200 2>&1 | grep -E 'V-[0-9]|目录=|mtime|^臂 |测点'
  echo
  echo "################ B'. 标准判决 —— cl1g"
  "$PY" _bk_verdict.py --root _exp/_bk_closed --tag cl1g --arms dry \
      --ctrl-tag L200 2>&1 | grep -E 'V-[0-9]'
  echo
  echo "################ C. 末态读数对照（cl1 / cl1g / 归档 eng12）"
  "$PY" - <<'PYEOF'
import csv, json, os
def tail(tag, root):
    p = os.path.join(root, tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    return rows[0], rows[-1]
for tag, root in (('dry_cl1', '_exp/_bk_closed'), ('dry_cl1g', '_exp/_bk_closed'),
                  ('eng_eng12', '_exp/_bk_eng')):
    r = tail(tag, root)
    if r is None:
        print('  %-12s （缺）' % tag); continue
    f, l = r
    print('  %-12s 步=%-5s Vt %s→%s µm³ | nslab %s→%s | nf3col %s→%s | runs=%s'
          % (tag, l['step'], f['Vt'][:6], l['Vt'][:6], f['nslab_n'], l['nslab_n'],
             f['nf3_col'], l['nf3_col'], l['runs']))
    print('  %-12s 厚度(剔孤儿见 B 段)；原始 ths=%s' % ('', l.get('ths', '')))
PYEOF
  echo
  echo "################ D. 工具自检"
  "$PY" _bk_measure.py --selftest 2>&1 | tail -2
  "$PY" windowB_closure.py 2>&1 | tail -2
  "$PY" _bk_athermal.py --selftest 2>&1 | tail -2
} >> "$LOG" 2>&1
echo "=== CLOSED VERDICT DONE ===" >> "$LOG"
