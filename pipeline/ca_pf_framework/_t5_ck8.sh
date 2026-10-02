#!/bin/bash
# _t5_ck8.sh --- ★★★★★ 复核清单**第 8 条**：`lpbf` 档下**断点续跑逐位相同**
#
# ## 协议（与原验证相同，**判据预先写死**）
#   A 臂：跑 20 步（`--ckpt-every 20` ⇒ 存帧）⇒ 再 `--resume` 续到 40 步
#   B 臂：**一次跑完** 40 步（同参数、不同 tag/目录）
#   **判据**：两臂的 `series.csv` 在共同列上 **逐位相同**（NaN 感知 + 比符号位，P16）
#
# ## 为什么这条对 `lpbf` 档尤其重要
#   `lpbf` 档引入了 `t_off`（偏移量）与 5 次热循环 ⇒ 若 `T_of_t` **不是纯函数**、
#   或 `t_off` 依赖某个**恢复不回来的状态**，续跑就会与一次跑完**分叉**。
#   ⇒ 这是"新档位是否兼容既有断点续跑能力"的**唯一可信判据**。
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LG=_w2_t5_ck8.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LG"; }
COMMON="--N 96 --nvar 12 --m 6 --B 3 --cores 16-19 --mem-limit-gb 4.0 --every 20 \
        --snap-every 200 --pair-every 50 --ckpt-every 20 --overlap-nm 62.5 --therm-hist lpbf"

say '════ A 臂：20 步（存帧）════'
$PY _t5_short.py --tag ck8A --steps 20 $COMMON --archive-old > _w2_t5_ck8_A1.log 2>&1
say "  exit=$?"
LS=$(ls -1 _exp/_bk_t5/dry_ck8A/ckpt/*.npz 2>/dev/null | wc -l)
say "  检查点帧数 = $LS（应 ≥1）"

say '════ A 臂续跑：--resume 到 40 步 ════'
$PY _t5_short.py --tag ck8A --steps 40 $COMMON \
   --resume _exp/_bk_t5/dry_ck8A/ckpt > _w2_t5_ck8_A2.log 2>&1
say "  exit=$?"
grep -cE 'RESUME|续跑|已恢复' _w2_t5_ck8_A2.log 2>/dev/null | sed 's/^/  续跑标识命中行数: /'

say '════ B 臂：一次跑完 40 步 ════'
$PY _t5_short.py --tag ck8B --steps 40 $COMMON --archive-old > _w2_t5_ck8_B.log 2>&1
say "  exit=$?"

say '════ ★ 逐位对比（判据：共同列全同）════'
$PY - <<'PYEOF' | tee -a "$LG"
import csv, os
def load(t):
    p = '_exp/_bk_t5/dry_%s/series.csv' % t
    if not os.path.exists(p): return None, None
    r = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    return r, {int(x['step']): x for x in r}
ra, A = load('ck8A')
rb, B = load('ck8B')
if ra is None or rb is None:
    print('  ❌ 缺 series（A=%s B=%s）' % (ra is not None, rb is not None)); raise SystemExit
print('  A 臂 %d 行 (末步 %s)；B 臂 %d 行 (末步 %s)'
      % (len(ra), ra[-1]['step'], len(rb), rb[-1]['step']))
steps = sorted(set(A) & set(B))
print('  共同步 = %s' % steps)
cols = [c for c in ra[-1] if c != 'step']
same = diff = nan_same = 0
bad = []
for s in steps:
    for c in cols:
        va = (A[s].get(c) or '').strip(); vb = (B[s].get(c) or '').strip()
        if va == vb:
            same += 1; nan_same += (va == '')
        else:
            diff += 1
            if len(bad) < 6: bad.append((s, c, va[:16], vb[:16]))
tot = same + diff
print()
print('  可比对数 = %d（%d 步 × %d 列）' % (tot, len(steps), len(cols)))
print('  相同 = **%d**   不同 = **%d**   其中两边都空 = %d' % (same, diff, nan_same))
for b in bad:
    print('     step %s  列 %s :  A=%s  B=%s' % b)
print()
print('  ⇒ 判据「不同 = 0」 ⇒ **%s**' % ('PASS ✅ 逐位相同' if diff == 0 else 'FAIL ❌'))
PYEOF
say '=== CK8 DONE ==='
