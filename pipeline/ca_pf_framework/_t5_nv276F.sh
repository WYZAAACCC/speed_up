#!/bin/bash
# _t5_nv276F.sh --- ★★★★★ `t5N276` 的重跑：**唯一差别 = windowB_surface.py 的 stack 建新场修复**
#
# ## 与 `_t5_nv276.sh` 的逐项对照
#   **相同**：--N 80 --nvar 12 --m 23 --B 3 --steps 6000
#            --cores 0-7 --mem-limit-gb 8.0 --every 20 --snap-every 40 --pair-every 100
#            --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00
#            同一个启动器 `_t5_short.py`（⇒ 同一套 13 个优化算子、同一物理基线 abA）
#   **不同**：--tag t5N276 → **t5N276F**（日志名相应改变）
#            + **代码修复**：`windowB_surface.py` 的 `stack` 分支三处 `k` → `k_new`
#              （git b8108011；备份 `windowB_surface.py.bak_stackfield`）
#
# ## 预登记判据（**跑之前写死，跑完按此判**）
#   ① **板条数**：`nslab_n` 应从 t5N276 的 **19** 升到**接近引擎目标**（`n_target` ≤ 66/69）；
#   ② **唯一性**：`不同场号 / 形核事件数` 应从 **0.56** 升到 **≈1.0**（冒烟已验证 1.00）；
#   ③ **长宽比**：按**连通分量**测，**最大块的中位长宽比**应显著高于 t5N276 的 **2.93**
#      （目标：进入真实区间 5–20）；
#   ④ **最大块占比**（新口径）：多数场应 **≥90%**（即不是"等大碎块"）；
#   ⑤ **块结构**：`nblk_sig ≥ 2` 且 `nf2 > 0`（异变体界面出现）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_nv276F.log
TAG=t5N276F
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

say '════ 起修复版重跑（与 t5N276 逐项一致，只多 stack 建新场的代码修复）════'
say '  ★ 唯一差别 1：--tag t5N276 → t5N276F'
say '  ★ 唯一差别 2：windowB_surface.py 的 stack 分支三处 k → k_new（git b8108011）'
free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

# ── 代码修复的存在性断言（**先验证修复在位，否则不起**）──
if grep -q "out.append((k_new, 'stack'))" windowB_surface.py; then
  say '  ✅ 代码修复在位：`out.append((k_new, '"'"'stack'"'"'))` 存在'
else
  say '  ❌ 代码修复**不在位** ⇒ 拒绝启动（否则等于白跑一遍 t5N276）'
  exit 1
fi
if grep -q "out.append((k, 'stack'))" windowB_surface.py; then
  say '  ❌ 仍残留旧的 `out.append((k, '"'"'stack'"'"'))` ⇒ 拒绝启动'
  exit 1
fi

say '  ── 启动（--nvar 12 --m 23 ⇒ nv=276；--N 80 ⇒ 5.00 µm）──'
setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 12 --m 23 --B 3 --steps 6000 \
    --cores 0-7 --mem-limit-gb 8.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    < /dev/null > _w2_t5_$TAG.log 2>&1 &
PID=$!
say "  已起 tag=$TAG（外层 pid=$PID）"

sleep 130
say '  ── 130 s 后：构造是否通过 ──'
grep -nE '总根数|导出板条数|B_max|❌|不自洽|约束|Traceback|nv=' _w2_t5_$TAG.log 2>/dev/null \
  | head -10 | cut -c1-165 >> "$LOG"
say '  ── 进程命令行核对（确认参数真的进去了）──'
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $TAG" | awk '{print $1}' | head -1)
if [ -n "$P" ]; then
  tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null \
    | grep -oE '\-\-N [0-9]+|\-\-laths [0-9]+|\-\-nvar [0-9]+|\-\-m [0-9]+|\-\-B [0-9]+|\-\-eng-elong [0-9.]+|\-\-var-rule [a-z]+|\-\-overlap-nm [0-9.]+|\-\-grow-stack|\-\-nuc-init [0-9]+' \
    | sed 's/^/     /' >> "$LOG"
else
  say '  ⚠ 未找到引擎进程 ⇒ 查日志'
fi
free -m | sed -n 2p | awk '{printf "  起后内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
say '=== 后续用 _t5_two_arms.sh / 监控脚本查 ==='
