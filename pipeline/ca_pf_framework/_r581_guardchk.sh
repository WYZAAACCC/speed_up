#!/bin/bash
# _r581_guardchk.sh --- 守卫到底在不在？直接、不绕弯地查。
cd "$(dirname "$0")" || exit 1
echo "=== $(date '+%F %T') 守卫检查 ==="
echo "--- 1. ps 里找（不用 pgrep，避免模式问题）---"
ps -eo pid,ppid,etime,args --no-headers 2>/dev/null | grep softguard | grep -v grep
ps -eo pid,ppid,etime,args --no-headers 2>/dev/null | grep memguard | grep -v grep
echo "--- 2. 计数 ---"
NS=$(ps -eo args --no-headers 2>/dev/null | grep softguard | grep -v grep | wc -l)
NM=$(ps -eo args --no-headers 2>/dev/null | grep memguard | grep -v grep | wc -l)
echo "  softguard 进程数 = $NS"
echo "  memguard  进程数 = $NM"
echo "--- 3. 日志尾部（能看到它最后一次心跳就说明活着）---"
echo "  [softguard]"; tail -3 _w2_r581_softguard.log 2>&1 | sed 's/^/    /'
echo "  [memguard ]"; tail -3 _w2_r581_memguard.log 2>&1 | sed 's/^/    /'
echo "--- 4. 当前内存 ---"
free -m | sed -n 2p | awk '{printf "  可用 %s MB（阈值：softguard 2600 / memguard 1800）\n",$7}'
echo "--- 5. 在跑的臂 ---"
ps -eo pid,args --no-headers 2>/dev/null | grep _bk_exp.py | grep -v grep | \
  awk '{for(i=1;i<=NF;i++) if($i=="--tag") printf "  tag=%s pid=%s\n",$(i+1),$1}' | sort -u
echo "--- 6. 判据 ---"
if [ "$NS" -ge 1 ] && [ "$NM" -ge 1 ]; then
  echo "  ⇒ ✅ 两个守卫都在"
else
  echo "  ⇒ ❌ **有守卫不在了** ⇒ 需要重起（见下面的命令）"
  echo "      bash _r581_memguard.sh 1800 5 &"
  echo "      bash _r581_softguard.sh p2_b5ps 2600 4 &"
fi
echo "--- 7. 顺序链（_r581_chain.sh）---"
NC=$(ps -eo args --no-headers 2>/dev/null | grep _r581_chain | grep -v grep | wc -l)
echo "  进程数 = $NC"
ps -eo pid,etime,args --no-headers 2>/dev/null | grep _r581_chain | grep -v grep | sed 's/^/    /'
echo "  链日志尾部（**第二条判据**）："
tail -3 _w2_r581_chain.log 2>/dev/null | sed 's/^/    /'
echo "  ⚠ 记账：ps|grep 会假报'没有' —— 实测发生过两次"
echo '     （`pgrep -af '"'"'softguard|memguard'"'"'` 与 `ps | grep chain` 都报空，而进程其实活着）'
echo "     ⇒ 判据必须交叉两条：① ps 数进程；② 该脚本的日志尾部有没有在动。"
echo "  ⚠ 本脚本第一版把反引号写在双引号 echo 里 ⇒ **被当成命令替换执行了**（输出里混进"
echo "     grep 的 Usage 与 ps 的表头）。已改成单引号 —— 与 AGENTS §3.9 的"
echo "     「Windows/PowerShell 破坏引号」同类：**脚本里的引号必须自己先验一遍**。"
