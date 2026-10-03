#!/bin/bash
# _t5_B4single.sh --- ★★★★★★ 二分实验 B4：**只有种子、禁止形核** ⇒ 判"碎裂是否来自演化本身"
#
# ## 为什么要做（**七条候选全部被否证之后**）
# 已否证：① attach 吃源场 ② nfsv 复用场 ③ 幽灵薄壳（算术不可能）
#         ④ `_seed_next` 复用场号 ⑤ 未补厚 ⑥ 内层 F3 无驱动力 ⑦ 速度扩展
# **⇒ 现在要做的不是猜第八条，而是**把问题一分为二**：**
#    * **只有 1 根种子、完全不形核** ⇒ 若它**也碎裂/缩体积** ⇒ **原因在演化方程**;
#    * 若它**完好** ⇒ **原因必与形核/播种事件有关**。
#
# ## 配置（**最小、最干净**）
#   --N 64（4 µm 盒）· --nvar 1 · --m 1 · --B 1 ⇒ nv=**1**（只有场 1）
#   ⚠ `nv ≥ B·n(T_end)` 约束要求 nv ≥ 23 ⇒ **nv=1 会被拒**
#   ⇒ 折中：`--nvar 1 --m 23 --B 1` ⇒ nv=23，但**用 `--nuc-init 0` 且不传 `--grow-stack`**
#      ⇒ **只播 t=0 的种子（场 1）** ⇒ 其余 22 个场空着 ⇒ 等价于"单根"。
#   --steps 1200（够长以观察碎裂）· 其余同大算例（eng-elong 7 · overlap 62.5 · 全算子）
#
# ## 预登记判据（**跑之前写死**）
#   * **场 1 的 φ<0 连通分量数**：若从 1 涨到 ≥2 ⇒ **演化本身会造成碎裂** ⇒ **原因在演化方程**;
#   * 若**始终 = 1** 且体积不缩 ⇒ **演化无辜** ⇒ 原因在**形核/播种**（需继续查播种路径）。
#   * 同时报：**是否发生了任何形核事件**（若有 ⇒ 本实验的"单根"前提不成立，要重设）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5B4S
LOG=_w2_t5_$TAG.log
{
  echo "════ 二分实验 B4：只有种子、禁止形核（判'碎裂是否来自演化'）════"
  echo "  配置：N=64 · nvar 1 · m 23 · B 1 ⇒ nv=23 · **--nuc-init 0 且不传 --grow-stack**"
  echo "  判据：场 1 的瓣数 1→≥2 ⇒ 演化有责；恒=1 ⇒ 演化无辜（原因在形核/播种）"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 64 --nvar 1 --m 23 --B 1 --steps 1200 \
    --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --nuc-init 0 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
say_pid=$!
echo "  已起 tag=$TAG（外层 pid=$say_pid）" >> "$LOG"

sleep 140
{
  echo "  ── 140 s 后：构造是否通过 / 有没有形核 ──"
  grep -nE '❌|Traceback|形核|nv=|自洽' _w2_t5_short_$TAG.log 2>/dev/null | head -8 | cut -c1-160
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $TAG" | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    echo "  ★ 命令行核对：$(tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-nuc-init [0-9]+|\-\-grow-stack|\-\-N [0-9]+|\-\-eng-elong [0-9.]+')"
  else
    echo "  ⚠ 未找到进程"
  fi
} >> "$LOG"
