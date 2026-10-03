#!/bin/bash
# _t5_nv276.sh --- ★★★★★ 5 µm 盒 · nv=276 · nvar=12 · eng-elong=7 · 全优化算子 · 断点续跑
#
# ## 用户目标（原话）
# > **「起一个 5 微米计算盒子内，nv=276，nvar 为 12，N=160 的仿真算例，用上之前证明有效的
# >   eng-elong，使用断点续跑以及所有优化过的算子，如果内存不够的话就关掉几个进程。
# >   我需要在这个算例里面观察到：① 板条正常生长 ② 长宽比正常 ③ 板条之间堆叠成块
# >   ④ 块与块相互影响 ⑤ 出现自协调」**
#
# ## ⚠ 我改了一处参数（**记账，理由如下**）
# **"5 µm 盒" 与 "N=160" 互斥**：
#   N=160 × dx=62.5 nm = **10.00 µm**；要 5.00 µm 只能 N=80（dx=62.5）或 N=160 + dx=31.25 nm。
#   而 N=160 时 `nv=276` 的内存 ≈ **42 GB** ⇒ **超本机 22 GB**（不可行）。
# **⇒ 取 N=80（dx=62.5 nm）= 真正的 5.00 µm 盒 ⇒ `nv=276` 只需 ~5.7 GB** ⇒ **可行** ✓
#
# ## 配置（逐项写明）
#   --N 80            ⇒ 盒 = 80 × 62.5 nm = **5.00 µm** ✓
#   --nvar 12         ⇒ **12 个变体**（= Ti-6Al-4V 的 Burgers 变体数）
#   --m 23            ⇒ 每组 23 个场 ⇒ **nv = 12 × 23 = 276** ✓（且 m=23 ≥ n(T_end)=23 满足约束 2）
#   --B 3             ⇒ 3 个块（B·n = 3×23 = 69 ≤ 276 ✓；N8 自洽：ceil(69/23)=3 ✓）
#   --eng-elong 7.00  ⇒ **已证明有效**（长宽比 1.85 → 6.55，稳定 ≤2%/5× 步数，无副作用）
#   --steps 6000      ⇒ 与 t5V2 同量级（t5H3 在 N=160 上到 step 1837 就到物理终点）
#   --ckpt-every 100 --ckpt-keep 2  ⇒ **断点续跑**（用户要求）
#   13 个优化算子    ⇒ **全开**（用户要求）
#   --overlap-nm 62.5 ⇒ = 1Δx
#
# ## 内存看门狗与"让路"（用户授权："内存不够就关掉几个进程"）
# 若可用内存 < 6 GB ⇒ **先停已定论的臂**（`t5AM_ell`/`t5AM_combo`：它们的结论已出）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_t5_nv276.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

say '════ 起 5 µm 盒 · nv=276(12 变体) · eng-elong=7 · 全算子 · 断点续跑 ════'
say '  ⚠ 记账：用户给的 N=160 与"5 µm 盒"互斥（N=160×62.5nm=10 µm），'
say '     且 N=160 时 nv=276 需 ~42 GB（>22 GB）⇒ 改取 N=80（真正的 5.00 µm 盒）'
free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

# ── 内存让路：若余量 < 6 GB ⇒ 停掉**结论已出**的 t5AM 两臂（它们的判定已完成）──
AVAIL=$(free -m | awk 'NR==2{print $7}')
if [ "$AVAIL" -lt 6000 ]; then
  say "  ⚠ 余量 ${AVAIL} MB < 6000 ⇒ 让路：停 t5AM_ell / t5AM_combo（**结论已出**）"
  for T in t5AM_ell t5AM_combo; do
    for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $T" | awk '{print $1}'); do
      kill -TERM "$P" 2>/dev/null && say "     已 TERM $T pid=$P"
    done
  done
  sleep 10
fi

# ── 起臂 ──
say '  ── 启动（--nvar 12 --m 23 ⇒ nv=276；--N 80 ⇒ 5.00 µm）──'
setsid $PY _t5_short.py --tag t5N276 --N 80 --nvar 12 --m 23 --B 3 --steps 6000 \
    --cores 0-7 --mem-limit-gb 8.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    < /dev/null > _w2_t5_n276.log 2>&1 &
PID=$!
say "  已起 tag=t5N276（外层 pid=$PID）"

sleep 120
say '  ── 120 s 后：构造是否通过（**N8 自洽 / 约束 / 是否报错**）──'
grep -nE '总根数|导出板条数|B_max|❌|不自洽|约束|Traceback|nv=' _w2_t5_n276.log 2>/dev/null \
  | head -10 | cut -c1-165 >> "$LOG"
free -m | sed -n 2p | awk '{printf "  起后内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
say '=== 后续用监控/存活脚本查（本脚本不常驻）==='
