#!/bin/bash
# _t5_v2b.sh --- ★★★★★ V2 **修正版**：保留自洽的 K=23，只加 `--var-rule random` + `m=36`
#
# ## 为什么要改（**引擎 N8 自洽检查抓到的**）
# 上一版我传了 `--nuc-fresh-every 5`，引擎**拒绝运行**并报：
#   ❌ `--nuc-fresh-every 5` 与 `--nuc-block-target 3` **不自洽**（N8）
#      ⇒ 修法：去掉它（自动取 23），或显式传 23。
# **N8 的条件**：`实际块数 = ceil(B·n/K)` **必须等于** `--nuc-block-target B`。
#   `K=5,  B=3, n=23` ⇒ ceil(69/5) = 14 ≠ 3  ❌
#   `K=23, B=3, n=23` ⇒ ceil(69/23) = 3  ✓  ← **`t5H3` 的配置本来就是自洽的**
# **⇒ ⇒ 所以 `t5H3` 的问题**不是调度**（目标就是 3 个块），
#      而是**那 2 个额外块的 `fresh` 事件全被拒**（单变体组没空位）。
# **⇒ 本版的修法**：**保留自洽的 `K=23`**，只加
#      **`--var-rule random`**（让 `fresh` 能选**不同变体**）+ **`m=36`**（给单组留余量）。
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LG=_w2_t5_v2b.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LG"; }

say '════ 起臂前 ════'
free -m | sed -n 2p | sed 's/^/  /'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  在场: pid=%s 已跑=%s\n", $1, $2}'
say '  ★ 本臂：--N 160 --nvar 2 --m 36 --B 3 --var-rule random   （**不传** --nuc-fresh-every ⇒ 自动 K=23，自洽）'

$PY _t5_short.py --tag t5V2 \
   --N 160 --nvar 2 --m 36 --B 3 --steps 6000 --cores 8-15 --mem-limit-gb 12.0 \
   --overlap-nm 62.5 --every 20 --snap-every 40 --pair-every 50 \
   --ckpt-every 20 --ckpt-keep 2 --var-rule random \
   --archive-old > _w2_t5_v2b_A.log 2>&1 &
NP=$!
say "  ★ pid=$NP（tag=t5V2）—— 本脚本会**一直等它**"
sleep 300
say '  ── 300 s 后：横幅关键行（应有 var-rule、不应有 N8 报错）──'
grep -E '导出板条数|总根数|必须至少|不自洽|var-rule|N8 自动推导|nv=' \
  _w2_t5_short_t5V2.log 2>/dev/null | head -8 | cut -c1-134 | sed 's/^/    /'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  在场: pid=%s 已跑=%s\n", $1, $2}'
free -m | sed -n 2p | sed 's/^/    /'
say '=== V2B LAUNCHED ==='
wait $NP
say "  V2 结束：exit=$?"
