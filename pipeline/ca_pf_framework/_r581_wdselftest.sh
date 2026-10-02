#!/bin/bash
# _r581_wdselftest.sh --- ★★★★★ **反向自检**（P41 要求）：看门狗**该报的时候真的会报**吗？
#
# ## 为什么必须做（P41）
# 旧版看门狗因为 **kB vs MB 的单位 bug**，**在 available=54 MB 时都没报过** ——
# 而它的日志**看起来完全正常**（"启动…正常退出"）。
# **⇒ 一个从不触发的阈值脚本 = 假的安全感** ⇒ **必须反向测一次**。
#
# ## 怎么测（**安全**）
# 用一个**必然越界**的阈值（999999 MB）跑一次，且 **KILL=0（只报不杀）** ⇒
#   * **应看到** `⚠⚠ available=… MB < 999999 MB` 的报警行；
#   * **应看到** `（KILL=0 ⇒ 只报不杀）`；
#   * **不应有任何进程被杀**（本条由"跑完再数一遍臂"确认）。
#
# ## 判据（**预先写死**）
# | 现象 | 判定 |
# |---|---|
# | 出现 `⚠⚠ available=` 行 | ✅ **报警通路通** |
# | 出现 `KILL=0 ⇒ 只报不杀` | ✅ **动作与检测解耦** |
# | **臂的数量不变** | ✅ **自检没有副作用** |
# | **没出现报警行** | ❌ **看门狗仍是死的** ⇒ 不许用它 |
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '── 自检前的臂 ──'
n0=$(pgrep -cf '_bk_exp.py' 2>/dev/null || echo 0)
bash _r581_arms.sh 2>/dev/null | sed -n '4,10p'
echo
echo '── ★ 反向自检：阈值 999999 MB（必然越界）、KILL=0（只报不杀）、跑 ~70 s ──'
out=$(timeout 150 bash _r581_memguard.sh 999999 0.02 0 2>&1)
echo "$out" | head -8 | sed 's/^/    /'
echo
echo '── 判据核对 ──'
if printf '%s' "$out" | grep -q '⚠⚠ available='; then
  echo '  ✅ 报警通路通（出现了 ⚠⚠ available= 行）'
else
  echo '  ❌ **没有报警行 ⇒ 看门狗仍是死的**'
fi
if printf '%s' "$out" | grep -q 'KILL=0 ⇒ 只报不杀'; then
  echo '  ✅ 检测与动作解耦（KILL=0 生效）'
else
  echo '  ⚠ 没看到 KILL=0 的行'
fi
echo
echo '── 自检后的臂（应与之前**数量相同**）──'
n1=$(pgrep -cf '_bk_exp.py' 2>/dev/null || echo 0)
bash _r581_arms.sh 2>/dev/null | sed -n '4,10p'
echo
if [ "$n0" = "$n1" ]; then
  echo "  ✅ 臂数不变（$n0 → $n1）⇒ 自检无副作用"
else
  echo "  ❌ 臂数变了（$n0 → $n1）⇒ 自检有副作用，必须查"
fi
