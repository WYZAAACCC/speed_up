#!/bin/bash
# _r581_mqueue2.sh --- ★★★★ **第二级队列：`m=20`（R53 算出的甜点）**
#
# ## 为什么是 `m=20`（R53 的账，量具 `_r581_tscale.py` + `_r581_mscale.py`）
# | m  | nv  | 内存(预测) | 600 步全程(外推) | 能放几根 | 对照 C5 的 220–450 |
# |----|-----|-----------|-----------------|---------|-------------------|
# | 4  | 48  | 4.86 GB   | 2.23 h          | 48      | ❌                |
# | 12 | 144 | 8.39 GB   | 6.67 h          | 144     | ❌                |
# | **20** | **240** | **11.93 GB** | **11.12 h** | **240** | ✅ **落在带内** |
# | 38 | 456 | 19.90 GB  | 21.14 h(≈24.4 含构造) | 456 | ✅（贴线）      |
# | 45 | 540 | 22.99 GB ❌ | 25.03 h ❌     | 540     | 两条预算都超      |
# ⇒ **`m=20` 是唯一"两条预算都宽松 + 根数落进目标带"的档。**
#
# ## 运行方式
# 与 `_r581_mqueue.sh` **同一套**：等**所有** `_r581_p2.py` 臂结束 ⇒ 过内存闸 ⇒ 起两臂。
# 本脚本**独立于**第一级队列（不改它，避免"改运行中的脚本"这种危险动作）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r581_mqueue2.log
MIN_FREE_MB="${1:-13000}"     # m=20 **单臂** ~12 GB（P23：单臂 + 余量 ⇒ 闸 13 GB）
CHECK_M12="${2:-1}"           # ★ 默认 1：**先等 p2_m12 出现并跑完**，再起 m20（防四臂同跑）
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ⚠ P27：`grep -v grep`
_n_arms() { ps -eo args --no-headers 2>/dev/null | grep '_r581_p2\.py' | grep -vc grep; }
_have_m12() { [ -d "_exp/_bk_p2/dry_p2_m12" ]; }

say "第二级队列启动：等臂结束后跑 **m=20**（R53 的甜点）；内存闸 = ${MIN_FREE_MB} MB"
say "当前在跑的臂数 = $(_n_arms)"

say "阶段 1：等所有 `_r581_p2.py` 臂结束…"
while [ "$(_n_arms)" -gt 0 ]; do sleep 60; done
say "阶段 1 完成"

if [ "$CHECK_M12" = "1" ]; then
  # ★★★ 第 1 版这里有**顺序 bug**（留痕）：原写法是
  #     `while _have_m12 && [ arms -gt 0 ]` —— 而**第一级队列还没起 `p2_m12` 时**
  #     `_have_m12()` 是 **false** ⇒ 条件立刻为假 ⇒ **本队列会在 m12 还没跑之前就起 m20**
  #     ⇒ **四个臂同时跑 ≈ 34 GB ⇒ 击穿 22 GB 预算**（P23）。
  #   ⇒ 正确顺序：**先等 `p2_m12` 出现，再等它跑完**。
  say "阶段 1b：等第一级队列**起** `p2_m12`（最多等 6 h）…"
  _w=0
  while ! _have_m12; do
    sleep 60; _w=$((_w + 1))
    if [ "$_w" -ge 360 ]; then
      say "❌ 等了 6 h 仍没见到 `p2_m12` ⇒ **退出**（不硬上，如实记账）"
      exit 4
    fi
  done
  say "阶段 1b：`p2_m12` 已出现；等它和它的同伴跑完…"
  while [ "$(_n_arms)" -gt 0 ]; do sleep 60; done
  say "阶段 1b 完成"
fi

avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存闸：MemAvailable = ${avail} MB（要求 ≥ ${MIN_FREE_MB}）"
if [ "$avail" -lt "$MIN_FREE_MB" ]; then
  say "❌ 内存不足 ⇒ **不起跑**（如实记账，不硬上）"
  exit 3
fi
say "✅ 过闸"

say "阶段 2：起臂"
# ★★★ **只起一条臂**（留痕：第 1 版起了两条，是错的）——
#   R53 的账：`m=20` 单臂预测峰值 **11.93 GB** ⇒ **两条 = 23.9 GB > 22 GB 预算**（P23 明写
#   "加车道的判据是内存不是空闲核"）⇒ **`m ≥ 20` 的档只能一次跑一条**。
#   ⇒ 本队列**只跑 `p2_m20`（B=5 主档）**；对照档（B=3）留待需要时另起。
say "起 p2_m20 : --m 20 --B 5 --cores 0-7（**单臂**，P23）"
$PY _r581_p2.py --run --tag p2_m20 --N 160 --m 20 --B 5 --cores 0-7 --archive-old \
    > _w2_r581_p2_p2_m20.log 2>&1
say "臂已结束"
for t in p2_m20; do
  d="_exp/_bk_p2/dry_$t"
  if [ -d "$d" ]; then
    say "  $t: series=$(wc -l < "$d/series.csv" 2>/dev/null || echo 0) 行"
  fi
done
say "=== R581 MQUEUE2 DONE ==="
