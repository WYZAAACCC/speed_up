#!/bin/bash
# _r581_mqueue3.sh --- ★★★★★ **C5 的**生产配方**：`m` + S4 **同时**开**（R69 的机制链要求）
#
# ## 为什么必须单独排这一条（R70 查出的配置缺口）
# R69 的机制链（每一环都有代码）：
#   1. `stack` 通道 = 「**同变体、新场**」（`_bk_exp.py:1974-1975` 逐字）
#   2. `nfsv` 只在**同变体**的空场里选新场（`windowB_surface.py:2326-2334`）
#   3. ⇒ **`m` 的上限卡住 `stack` 通道**；反之 **S4 关着时 `stack` 通道根本不通**
#      （实测：`p2_b5` 的 `stack=1` vs `p2_b5ov` 的 `stack=5`）
# **⇒ 只提 `m` 不开 S4，等于把名额空着；只开 S4 不提 `m`，4 片就撞墙。**
#
# ## R70 查出的**配置缺口**
# | 队列 | 配置 | 测的是什么 |
# |---|---|---|
# | `_r581_mqueue.sh`  | `--m 12 --B 5` / `--m 12 --B 3` | **`m` 单独**（**没有** `--overlap-nm`） |
# | `_r581_mqueue2.sh` | `--m 20 --B 5`                 | **`m` 单独**（**没有** `--overlap-nm`） |
# | `_r581_mn64.sh`    | `--N 64 --m 4/12` **+ `--nuc-overlap-nm 62.5`** | **`m` + S4**（N=64 代理） |
# **⇒ **N=160 上还没有任何一条臂跑过「`m` + S4」—— 而那才是 C5 的配方。**
#
# ## 本队列
# 等所有 `_r581_p2.py` 臂结束 ⇒ 跑 **`p2_m12ov`（`--m 12 --B 5 --overlap-nm 62.5`）**。
# ⚠ **单臂**（P23：`m=12` 单臂 8.39 GB；两条 16.8 GB 虽在 22 GB 内，
#   但前面队列可能还有残留 ⇒ 保守只起一条）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_r581_mqueue3.log
MIN_FREE_MB="${1:-9000}"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

_n_arms() { ps -eo args --no-headers 2>/dev/null | grep '_r581_p2\.py' | grep -vc grep; }
_have()   { [ -d "_exp/_bk_p2/dry_$1" ]; }

say "=== R581-R70：C5 的生产配方（**m + S4 同开**）==="
say "阶段 1：等当前所有臂结束…"
while [ "$(_n_arms)" -gt 0 ]; do sleep 60; done
say "阶段 1 完成"

say "阶段 2：等 `mqueue` 的 `p2_m12` 与 `mqueue2` 的 `p2_m20` 都跑完 ≤ 24 h…"
_w=0
while :; do
  [ "$(_n_arms)" -gt 0 ] && { sleep 60; continue; }
  # 两个前置 tag 都出现且系列停更 ⇒ 认为跑完
  if _have p2_m12 && _have p2_m20; then break; fi
  sleep 60; _w=$((_w + 1))
  [ "$_w" -ge 1440 ] && { say "❌ 等了 24 h ⇒ 退出"; exit 4; }
done
say "阶段 2 完成"

avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存闸：MemAvailable = ${avail} MB（要求 ≥ ${MIN_FREE_MB}）"
[ "$avail" -lt "$MIN_FREE_MB" ] && { say "❌ 内存不足 ⇒ 不起跑"; exit 3; }

say "起 p2_m12ov：--m 12 --B 5 --overlap-nm 62.5（**单臂**，P23）cores 0-7"
$PY _r581_p2.py --run --tag p2_m12ov --N 160 --m 12 --B 5 --overlap-nm 62.5 \
    --cores 0-7 --archive-old > _w2_r581_p2_p2_m12ov.log 2>&1
say "臂结束"
say "  p2_m12ov: series=$(wc -l < _exp/_bk_p2/dry_p2_m12ov/series.csv 2>/dev/null || echo 0) 行"
say "=== R581 MQUEUE3 DONE ==="
