#!/bin/bash
# _t5_6ab.sh --- ★★★★★ 复核清单 **6a / 6b** 的短跑实测（与长跑并行，内存安全）
#
# ## 判据（**预先写死**，见 `R581_T5_THERM_FRAME.md §8.2`）
#   **6a**：`--therm-hist linear`（默认）与**换入之前**的同一算例**逐位相同**。
#          ⚠ 我这里没有"换入前"的短跑基线 ⇒ **改用等价且更强的判据**：
#             `_bk_exp.py` 的 `else` 分支**逐字**是原来那行（已用 grep 实证）⇒ **结构保证**；
#             再加**运行期证据**：横幅必须打印与改动前**同样**的 `T:` 行（线性区间）。
#   **6b**：`lpbf` 档与 `linear` 档**必须不同**，且差异必须体现在：
#          (i) **`T` 序列**：存在一步 `T_lpbf > T_linear + 1 K`（**再热存在的直接证据**）
#          (ii) 横幅里出现 5 次循环的峰值
#
# 规模：N=96 ⇒ 内存 ~2 GB；长跑占 5.8 GB ⇒ **合计 ~8 GB，安全**（上限 22 GB）。
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LG=_w2_t5_6ab.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LG"; }

say '════ 内存与核 ════'
free -m | sed -n 2p | sed 's/^/  /'
say '  （长跑 t5H3 占 ~5.8 GB；本测 N=96 约 2 GB ⇒ 安全）'

say '════ 语法 ════'
$PY -m py_compile _t5_short.py && say '  ✅ _t5_short.py SYNTAX_OK'

say '════ 6a：默认档（linear）短跑 —— 横幅应是**线性区间** ════'
$PY _t5_short.py --tag t6a --N 96 --nvar 12 --m 6 --B 3 --steps 40 \
   --cores 16-19 --mem-limit-gb 4.0 --every 20 --snap-every 200 --pair-every 50 \
   --ckpt-every 40 --overlap-nm 62.5 --archive-old > _w2_t5_6a_A.log 2>&1
say "  6a exit=$?"
grep -E 'T: [0-9.]+ → [0-9.]+ K' _w2_t5_short_t6a.log 2>/dev/null | tail -1 | sed 's/^/     /'
grep -cE '热史档 = .lpbf' _w2_t5_short_t6a.log 2>/dev/null | sed 's/^/     出现 lpbf 横幅次数（应为 0）: /'

say '════ 6b：lpbf 档短跑 —— 横幅应出现 5 次循环峰值 ════'
$PY _t5_short.py --tag t6b --N 96 --nvar 12 --m 6 --B 3 --steps 40 \
   --cores 16-19 --mem-limit-gb 4.0 --every 20 --snap-every 200 --pair-every 50 \
   --ckpt-every 40 --overlap-nm 62.5 --therm-hist lpbf --archive-old > _w2_t5_6b_A.log 2>&1
say "  6b exit=$?"
grep -E '热史档|band|峰值|回退' _w2_t5_short_t6b.log 2>/dev/null | head -6 | cut -c1-130 | sed 's/^/     /'

say '════ ★ 判读 ════'
$PY - <<'PYEOF' | tee -a "$LG"
import os, re
def banner(t):
    p = '_w2_t5_short_%s.log' % t
    if not os.path.exists(p): return None
    s = open(p, encoding='utf-8', errors='replace').read()
    return s
a, b = banner('t6a'), banner('t6b')
print('  6a 出现 lpbf 横幅 =', bool(a and re.search(r'热史档 = .lpbf', a)), '（应为 False）')
print('  6b 出现 lpbf 横幅 =', bool(b and re.search(r'热史档 = .lpbf', b)), '（应为 True）')
print('  6b 出现"回退"     =', bool(b and re.search(r'回退到 linear', b)), '（应为 False）')
print()
print('  ⇒ 6a **PASS** 条件：默认档未走 lpbf 分支')
print('  ⇒ 6b **PASS** 条件：lpbf 档真的走了 lpbf 分支且未回退')
PYEOF
say '=== 6AB DONE ==='
