#!/bin/bash
# _r581_gate.sh --- ★★ goal 成功判据④ 的**单一入口**：
#   「数值回归 + **计数回归** 双绿，真实 `_bk_exp.py` 冒烟绿（**比全部落盘列**）」
#
# ## 为什么必须合成一个入口（而不是三份脚本各跑各的）
# 判据④ 要的是**同时**绿。分开跑就有"这份绿了那份没跑"的空间；
# 而且 `P2` 的教训正是「**数值回归全绿 ≠ 没有性能回归**」——
# 两道必须**并列**摆出来，缺哪一道都不算过。
#
# ## 三道各自在防什么（**不许合并成一道**）
# | 道 | 脚本 | 防的是 |
# |---|---|---|
# | **1 数值回归** | `_r576_regress.sh` → `_r30_regress.sh` | 数值被改坏了（归档路径逐位） |
# | **2 计数回归** | `_r581_countgate.sh` | **数值逐位相同、但算子被多跑一遍**（P2；实测占过单步 30%） |
# | **3 真实路径冒烟** | `_r581_ab2.sh`-类（比**全部落盘列**） | 诊断量被改坏（R580 的 `E_el_J` 差 3.1× 那次，`g.phi` 逐位却看不出来） |
#
# ⚠ **第 3 道在本脚本里只做"有没有可用的近期 AB 留档"的检查**（因为它要两个臂、跑得久）；
#   完整的第 3 道请跑 `_r581_L5ab.sh` / `_r581_L6ab.sh` / `_r581_final_ab.sh`。
set -u
cd "$(dirname "$0")" || exit 1
LOG=_w2_r581_gate.log
: > "$LOG"
say() { echo "$@" | tee -a "$LOG"; }

say "=============================================================================="
say "R581 GATE —— 判据④：数值回归 + 计数回归 + 真实路径冒烟   $(date '+%F %T')"
say "=============================================================================="
say "宿主指纹（P1：跨会话绝对值不可比）"
/root/miniconda3/envs/ml/bin/python _r576_hostfp.py 2>/dev/null | sed 's/^/   /' | tee -a "$LOG"

R1=1; R2=1; R3=1

say ""
say "──── 第 1 道：数值回归（归档路径逐位）────"
bash _r576_regress.sh > _w2_r581_gate_r1.log 2>&1
R1=$?
grep -nE '共有列逐位一致|FAIL|ALL PASS|windowB_pf3d|差异' _w2_r581_gate_r1.log | tail -12 | sed 's/^/   /' | tee -a "$LOG"
# `_r576_regress.sh` 自己不返回失败码 ⇒ **另外硬判**。
# ⚠⚠ **第一版判据写错了（留痕）**：我写 `grep -qE 'FAIL'` —— 而回归总结行是
#   **`FAIL = 0`**（失败**计数**），字面上含 "FAIL" ⇒ **恒判红**。
#   这正是本仓 P6「量具错了和被测量对象错了长得一模一样」的又一例：
#   回归明明是绿的（`共有列逐位一致` + `FAIL = 0` + `windowB_pf3d ALL PASS`），
#   而我的闸门报红。
# ⇒ 修法：**先取 FAIL 的数值**，再判它是否为 0；并且**要求两句正向证据都在**。
_fail_n=$(grep -oE 'FAIL *= *[0-9]+' _w2_r581_gate_r1.log | grep -oE '[0-9]+' | tail -1)
_has_ok=$(grep -cE '共有列逐位一致' _w2_r581_gate_r1.log)
_has_ap=$(grep -cE 'ALL PASS' _w2_r581_gate_r1.log)
if [ -n "$_fail_n" ] && [ "$_fail_n" = "0" ] && [ "$_has_ok" -ge 1 ] && [ "$_has_ap" -ge 1 ]; then
  R1=0
else
  R1=1
fi
say "   （判据读数：FAIL 计数=${_fail_n:-取不到}；'共有列逐位一致' 出现 ${_has_ok} 次；'ALL PASS' 出现 ${_has_ap} 次）"
say "   ⇒ 第 1 道 = $([ "$R1" = 0 ] && echo '✅ 绿' || echo '❌ 红（或判据取不到）')"

say ""
say "──── 第 2 道：计数回归（硬断言 + 两个负对照）────"
bash _r581_countgate.sh > _w2_r581_gate_r2.log 2>&1
R2=$?
grep -E '计数回归|NC-A|NC-B|✅|❌' _w2_r581_gate_r2.log | tail -12 | sed 's/^/   /' | tee -a "$LOG"
say "   ⇒ 第 2 道 = $([ "$R2" = 0 ] && echo '✅ 绿' || echo '❌ 红')"

say ""
say "──── 第 3 道：真实路径冒烟（比**全部落盘列**）────"
say "   查近期 AB 留档（完整第 3 道请跑 _r581_L5ab.sh / _r581_L6ab.sh / _r581_final_ab.sh）"
N3=$(ls -1 _w2_r581_*ab*.log _w2_r581_final.log 2>/dev/null | wc -l)
say "   找到 $N3 份 AB 留档"
for f in $(ls -1t _w2_r581_*ab*.log _w2_r581_final.log 2>/dev/null | head -3); do
  v=$(grep -hoE 'gate 4 判定：[^ ]*|逐位一致' "$f" 2>/dev/null | head -1)
  say "     $(basename "$f")  →  ${v:-（无判定行）}"
done
if [ "$N3" -ge 1 ] && grep -qhE 'PASS|逐位一致|0 差异' _w2_r581_*ab*.log _w2_r581_final.log 2>/dev/null; then
  R3=0
fi
say "   ⇒ 第 3 道 = $([ "$R3" = 0 ] && echo '✅ 有绿的留档' || echo '⚠ 没找到留档（**不等于红**，但判据④要求有）')"

say ""
say "=============================================================================="
if [ "$R1" = 0 ] && [ "$R2" = 0 ]; then
  say "✅ **双绿**：数值回归 + 计数回归都过（判据④的前两半成立）"
  [ "$R3" = 0 ] && say "✅ 第三道也有绿的留档 ⇒ **判据④ 成立**" \
                || say "⚠ 第三道缺留档 ⇒ 判据④ **未完全成立**（去跑一次 AB）"
  RC=0
else
  say "❌ **未双绿** —— 第1道=$R1 第2道=$R2 第3道=$R3"
  RC=1
fi
say "=== R581 GATE DONE $(date '+%F %T') rc=$RC ==="
exit $RC
