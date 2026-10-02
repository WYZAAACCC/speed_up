#!/bin/bash
# _r581_thin.sh --- ★★★★★ 按**内存纪律**（goal「内存道分波」）把车道减到 3 条
#
# ## 为什么（R159 的诊断）
# ① **四条队列脚本**（`_r581_mn64h/j/k/L.sh`）**在同一瞬间**（16:06:01，F/G 退出的那一刻）
#    都判定"N=64 上没人跑了" ⇒ **同时起臂** ⇒
#    **2 条 N=160（113 min，各 4.3/11.8 GB）+ 4 条 N=64（各 0.6–1.9 GB）= 20.7 GB**
#    ⇒ `available` 一度到 **54 MB**、swap 5.5 GB ⇒ **换页抖动**（P39）。
# ② **看门狗本该拦住它，但有个**单位 bug****：它拿 `MemAvailable` 的 **kB** 值去比 `LIM=1800`（MB）
#    ⇒ **只在 available < 1.8 MB 时才触发** ⇒ **等于没开**（P30 的又一次实例）。
#
# ## 本脚本做什么（**最保守**）
# * **停三条队列脚本**（h/j/k）⇒ **防止它们继续起臂**（它们的等待条件会反复满足）；
# * **停它们刚起的 3 条臂**（J20/I11e/K1，各只跑了 ~4 min ⇒ **损失最小**）；
# * **保留**：**两条 N=160**（各 113 min = Part 2 主线）+ **臂 L**（A39 的 600 步长跑，注册的下一步）；
# * **一个字节都不删**（只 kill 进程；产物留在 /mnt/f）✓
#
# ## 记账
# 停掉的臂**可以重跑**（脚本都在，`--out` 目录会 `mv` 归档而不是覆盖）。
set -u
cd "$(dirname "$0")" || exit 1
LOG=_w2_r581_thin.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say "=== R581-R159：按内存纪律减车道（6 → 3）==="
say "动作前的内存与进程："
awk '/MemAvailable/{printf "  available=%.0f MB\n", $2/1024}' /proc/meminfo | tee -a "$LOG"
bash _r581_arms.sh 2>/dev/null | sed -n '4,12p' | tee -a "$LOG"

# ---- ① 先停队列脚本（防止它们继续起臂）----
say "① 停队列脚本（h/j/k）—— **不动 L 的队列**（L 是注册的 A39 实验）"
for name in _r581_mn64h.sh _r581_mn64j.sh _r581_mn64k.sh; do
  for p in $(pgrep -f "bash $name" 2>/dev/null); do
    kill -TERM "$p" 2>/dev/null && say "    TERM pid=$p ($name)"
  done
done
sleep 3
for name in _r581_mn64h.sh _r581_mn64j.sh _r581_mn64k.sh; do
  for p in $(pgrep -f "bash $name" 2>/dev/null); do
    kill -9 "$p" 2>/dev/null && say "    KILL pid=$p ($name)"
  done
done

# ---- ② 停那三条只跑了 4 min 的臂 ----
say "② 停 J20 / I11e / K1（各只跑了 ~4 min ⇒ 损失最小）"
for tag in J20 I11e K1; do
  for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
    c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
    case "$c" in
      *"--tag $tag "*) kill -TERM "$p" 2>/dev/null && say "    TERM pid=$p ($tag)";;
    esac
  done
done
sleep 5
for tag in J20 I11e K1; do
  for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
    c=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
    case "$c" in
      *"--tag $tag "*) kill -9 "$p" 2>/dev/null && say "    KILL pid=$p ($tag)";;
    esac
  done
done
sleep 3

say "③ 结果核对（应剩：p2_m12、p2_m12b、L 三条）"
bash _r581_arms.sh 2>/dev/null | tee -a "$LOG"
say "=== R581-R159 THIN DONE ==="
