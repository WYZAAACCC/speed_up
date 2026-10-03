#!/bin/bash
# _t5_rv_arm.sh --- ★★★★★ 同配置但 `--var-rule random` 的对照臂（唯一变量 = 变体选择规则）
#
# ## 依据（**实测，不是推测**）
# `_t5_varrule_chk.sh` 从**进程命令行**确认：
#   * `t5N276`：`--grow-stack --nuc-init 6`，**没传 `--var-rule`** ⇒ 默认 **`ed`**（`argmax(drv)`）
#     ⇒ **永远选同一变体** ⇒ `n_var_sig` 恒 = 1 ⇒ **只有 1 个块** ⇒
#     **④（块间影响）在原理上不可能发生**（`nf2` 需要**异变体**界面）；
#   * `t5V2`：显式传 `--var-rule random`，且它**出现过 `n_var_sig=2`**。
# 代码：`_bk_exp.py:3426` default='ed'；`:1791` 把 `var_rule` 传进形核配置。
#
# ## 处置（**保守 · 可回退 · 记账**）
# **不动正在跑的 `t5N276`**（保留为干净基线）⇒ **另起同配置臂 `t5NR`，唯一差别 = `--var-rule random`。**
# 这样：① 两个配置可直接对照；② 若新臂证明 random 能带来多变体/多块，**结论有对照支撑**。
#
# ## 配置（与 `t5N276` **逐项相同**，只多一个 flag）
#   --N 80（5 µm）· --nvar 12 · --m 23 ⇒ nv=276 · --B 3 · --steps 6000
#   --eng-elong 7.00 · --overlap-nm 62.5 · 13 算子全开 · --ckpt-every 100 --ckpt-keep 2
#   **＋ --var-rule random**   ← **唯一变量**
#
# ## 内存
# `nv=276` @ N=80 约需 5.7 GB；若余量不足 < 7 GB ⇒ **先停 `t5AM_ell`/`t5AM_combo`**（其结论已出）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_nr.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

say '════ 起对照臂 t5NR（唯一变量：--var-rule random）════'
say '  依据：t5N276 用默认 ed ⇒ 永远同变体 ⇒ ④ 原理上不可能发生（实测命令行已确认）'
free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

AVAIL=$(free -m | awk 'NR==2{print $7}')
if [ "$AVAIL" -lt 7000 ]; then
  say "  ⚠ 余量 ${AVAIL} MB < 7000 ⇒ 让路：停 t5AM_ell / t5AM_combo（结论已出）"
  for T in t5AM_ell t5AM_combo; do
    for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $T" | awk '{print $1}'); do
      kill -TERM "$P" 2>/dev/null && say "     已 TERM $T pid=$P"
    done
  done
  sleep 10
fi

setsid $PY _t5_short.py --tag t5NR --N 80 --nvar 12 --m 23 --B 3 --steps 6000 \
    --cores 0-7 --mem-limit-gb 8.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --var-rule random \
    < /dev/null > _w2_t5_nr_engine.log 2>&1 &
say "  已起 tag=t5NR（--var-rule random）"

sleep 120
say '  ── 120 s 后：构造横幅关键行（**先验：确认 --var-rule random 真的进去了**）──'
grep -nE 'var-rule|var_rule|nv=|N=80|形核|❌|Traceback' _w2_t5_nr_engine.log 2>/dev/null \
  | head -8 | cut -c1-165 >> "$LOG"
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5NR' | awk '{print $1}' | head -1)
if [ -n "$P" ]; then
  say "  ★ 进程命令行核对（最可靠）："
  tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-var-rule [a-z]+|\-\-eng-elong [0-9.]+|\-\-nvar [0-9]+|\-\-m [0-9]+' \
    | sed 's/^/     /' >> "$LOG"
else
  say "  ⚠ 未找到 t5NR 引擎进程 ⇒ 可能启动失败，查日志"
fi
free -m | sed -n 2p | awk '{printf "  起后内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
say '=== 后续用 _t5_blkmon 的 TAGS 或直接读 series.csv ==='
