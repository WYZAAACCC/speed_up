#!/bin/bash
# _t5_B2.sh --- ★★★★★ 问题 B 判别实验 B2：**单变体单块**（判"同变体密集堆叠"是否长宽比退化的原因）
#
# ## 为什么是 B2 而不是 B3
# 原计划 B3 想做"单根"（`nvar 1 --m 1 --B 1` ⇒ nv=1），但**约束不允许**：
#   `nv ≥ B·n(T_end)` ⇒ nv ≥ 1×23 = **23** ⇒ nv=1 **违反约束**，算例会被拒。
# **⇒ 能满足约束的最小配置是 `nvar 1 --m 23 --B 1` ⇒ nv=23**（= **B2**）。
#   * 它**只有一个变体**（所有板条同变体）⇒ 直接检验"同变体堆叠"假说;
#   * 只有 **1 个块**（B=1）⇒ 同时检验"多块"假说。
# **★ 真正的"单根"（无邻居）需要**关掉形核**（`--nuc-init 0` 且不传 `--grow-stack`）⇒
#   那是 B3，需要先核对启动器是否支持 ⇒ **留待下一轮**。
#
# ## 预登记判据（**跑之前写死**）
#   与 `t5N276`（nv=276 · 12 变体 · B=3）**步对齐**比较：
#   * **长宽比**：若 B2 **保持 ≥5** ⇒ **同变体密集堆叠/多块是原因**（B2 证实）;
#                 若 B2 **仍崩到 ~1.2** ⇒ **与堆叠无关**，指向更基本的机制;
#   * **占比**：同上。
#
# ## 配置（**只在变体数与块数上改**，其余逐项同 t5N276）
#   --N 80 · --nvar **1** · --m **23** · --B **1** ⇒ nv=**23**（约束：23 ≥ 1×23 ✓）
#   --eng-elong 7.00 · --overlap-nm 62.5 · --steps 6000
#   --ckpt-every 100 --ckpt-keep 2 · 全优化算子（同一启动器）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5B2
LOG=_w2_t5_$TAG.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

say '════ 问题 B 判别实验 B2：单变体（nvar=1）· 单块（B=1）· nv=23 ════'
say '  判据：与 t5N276 步对齐比较长宽比与占比'
say '       保持 ≥5 ⇒ 堆叠/多块是原因；仍崩 ⇒ 与堆叠无关'
free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 1 --m 23 --B 1 --steps 6000 \
    --cores 0-3 --mem-limit-gb 4.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
say "  已起 tag=$TAG"

sleep 130
say '  ── 130 s 后：构造横幅（**关键：nv 是否为 23、N8 是否自洽、有无 ❌**）──'
grep -nE 'nv=|N8|自洽|总根数|导出板条数|❌|Traceback|约束' _w2_t5_short_$TAG.log 2>/dev/null \
  | head -10 | cut -c1-165 >> "$LOG"
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $TAG" | awk '{print $1}' | head -1)
if [ -n "$P" ]; then
  say "  ★ 命令行核对："
  tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null \
    | grep -oE '\-\-N [0-9]+|\-\-nvar [0-9]+|\-\-m [0-9]+|\-\-B [0-9]+|\-\-eng-elong [0-9.]+|\-\-laths [0-9]+' \
    | sed 's/^/     /' >> "$LOG"
else
  say '  ⚠ 未找到进程 ⇒ 查日志'
fi
free -m | sed -n 2p | awk '{printf "  起后内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
