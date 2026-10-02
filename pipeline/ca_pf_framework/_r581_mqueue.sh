#!/bin/bash
# _r581_mqueue.sh --- ★★★ **R33 的更正的判决长跑**：把 `m` 从 4 提到 12，看块能不能长过 4 根。
#
# ## 为什么（R33 的发现）
# `nfsv`（同变体⇒新场）只能在**同变体的空场**里选 ⇒ **同变体板条数硬上限 = m = nv/12**。
# 我此前的两臂用 **m=4**，而 `--nuc-block-target 5` 要 5 根 ⇒ **配置自相矛盾**。
# 短程判决（`_r581_mtest.sh`，N=64/60 步）：**m=4 ⇒ nslab_n max 4（nfsv_nofield=1）；
# m=12 ⇒ max 5 = target（nfsv_nofield=0）**。⇒ 现在要**长程**确认。
#
# ## 内存账（用 goal §(12) 的实测系数，**onfly 档 a = 9.000**）
#   `nv = 12*m = 144`；`CELL = 160³ = 4.096e6`
#   ⇒ 引擎项 ≈ 9.000 × 144 × 4.096e6 B = **5.3 GB**；加固定项 ⇒ 单臂 ≈ 6–7 GB
#   ⇒ **两臂 ≈ 13 GB < 24 GB** ✅（但仍按 P23：**起跑前过内存闸**）
#
# ## 运行方式
#   与 `_r581_p2.py` 的既有臂**逐字同配置**，**只差 `--m`**（单变量）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r581_mqueue.log
MIN_FREE_MB="${1:-9000}"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ── 阶段 1：等**当前所有臂**结束 ──
# ⚠ 用 `grep -v grep`（P27：`ps|grep` 会匹配到自己 ⇒ 死循环）
_n_arms() { ps -eo args --no-headers 2>/dev/null | grep '_r581_p2\.py' | grep -vc grep; }
say "顺序链启动：等当前臂结束后跑 m=12 的两臂；内存闸 = ${MIN_FREE_MB} MB"
n0=$(_n_arms)
say "当前在跑的臂数 = $n0"
if [ "$n0" -gt 0 ]; then
  say "阶段 1：等它们结束…"
  while [ "$(_n_arms)" -gt 0 ]; do sleep 60; done
  say "阶段 1 完成：所有臂已结束"
fi

# ── 阶段 2：内存闸（P23：加车道的判据是**内存**）──
avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存闸：MemAvailable = ${avail} MB（要求 ≥ ${MIN_FREE_MB}）"
if [ "$avail" -lt "$MIN_FREE_MB" ]; then
  say "❌ 内存不足 ⇒ **不起跑**（如实记账，不硬上）"
  exit 3
fi
say "✅ 过闸"

# ── 阶段 3：起两臂（互不相交的核）──
say "起 p2_m12 : --m 12 --B 5 --cores 0-3"
$PY _r581_p2.py --run --tag p2_m12 --N 160 --m 12 --B 5 --cores 0-3 --archive-old \
    > _w2_r581_p2_p2_m12.log 2>&1 &
say "起 p2_m12b: --m 12 --B 3 --cores 4-7"
$PY _r581_p2.py --run --tag p2_m12b --N 160 --m 12 --B 3 --cores 4-7 --archive-old \
    > _w2_r581_p2_p2_m12b.log 2>&1 &
wait
say "两臂都已结束"
for t in p2_m12 p2_m12b; do
  d="_exp/_bk_p2/dry_$t"
  if [ -d "$d" ]; then
    say "  $t: series=$(wc -l < "$d/series.csv" 2>/dev/null || echo 0) 行；nuc_dbg=$([ -f "$d/nuc_dbg.json" ] && stat -c %s "$d/nuc_dbg.json" || echo 0) B"
  fi
done
say "=== R581 MQUEUE DONE ==="
