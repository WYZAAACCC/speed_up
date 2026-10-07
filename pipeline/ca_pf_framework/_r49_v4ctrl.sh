#!/bin/bash
# R49 正对照（修正版）：V-4 改用 core 口径后，**两种臂都必须跑通且行为正确**
#   ① 有 `box_touch_core` 列的新臂 ⇒ 判 core，旧口径只报
#   ② 无该列的归档臂          ⇒ 明确降级，不冒充
# ⚠ 用正确的 `--root`（臂在 `_exp/_bk_mb`，不是默认的 `_exp/_bk_block`）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1

for arm in dry_mb1s62 dry_mb1L dry_mb1s; do
  echo "########## $arm"
  $PY _bk_verdict.py --root _exp/_bk_mb --tag "${arm#dry_}" --arms dry 2>&1 \
    | grep -E 'V-4|box_touch|找不到臂' | head -4
  echo
done
echo "########## 直接核对两列（证明 core != 旧，且 mb1L 正是被旧口径误判的那条）"
$PY - <<'PY'
import csv, os
for arm in ('dry_mb1s', 'dry_mb1L', 'dry_mb1Ls', 'dry_mb1s62'):
    p = os.path.join('_exp/_bk_mb', arm, 'series.csv')
    if not os.path.exists(p):
        print('%-11s : 无 CSV' % arm); continue
    with open(p) as f:
        rd = list(csv.DictReader(f))
    old = sorted(set(r.get('box_touch', '?') for r in rd))
    new = sorted(set(r.get('box_touch_core', '(缺列)') for r in rd))
    verdict = ('**旧口径会误判撞壁**' if '1' in old and new == ['0']
               else ('一致' if old == new else '?'))
    print('%-11s n=%-4d 旧 box_touch=%-10s 新 box_touch_core=%-10s %s'
          % (arm, len(rd), old, new, verdict))
PY
