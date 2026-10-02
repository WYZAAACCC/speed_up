#!/bin/bash
# _r581_wdswap.sh --- ★★★★★ 换掉**正在跑的旧看门狗**，起**修好的**那条
#
# ## 为什么必须先把旧的杀掉（**不是"多此一举"**）
# bash 是**按需读脚本**的：一个**已在运行**的 `bash _r581_memguard.sh` 进程
# **会在下一轮循环时从文件的当前偏移继续读** ⇒ 我刚把文件改对了，
# **旧进程可能**中途读到新代码**** ⇒ 它就会**突然开始按 1800 MB 正确工作** ⇒
# **立刻 kill 掉全部 `_bk_exp.py`**（**包括两条跑了 116 min 的 N=160 臂**）。
# ⇒ **必须先把旧进程停掉，再起新的。**
#
# ## 阈值怎么选
# * goal 说「<1.5 GB 报警」⇒ **1500 MB**；
# * **修好单位之后，1500 就是**真的 1.5 GB****（旧版要 1.8 MB 才动）；
# * 当前 `available` ≈ 5 GB ⇒ **不会误触发** ✓。
set -u
cd "$(dirname "$0")" || exit 1
LOG=_w2_r581_wdswap.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say "=== R581-R160：换看门狗（旧的带单位 bug，且可能中途读到新代码）==="
say "现在跑着的 memguard："
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '_r581_memguard' | grep -v grep | sed 's/^/  /' | tee -a "$LOG"

# ① 杀掉旧的全部 memguard（**只杀看门狗，不碰 _bk_exp**）
for p in $(pgrep -f '_r581_memguard.sh' 2>/dev/null); do
  kill -TERM "$p" 2>/dev/null && say "  TERM 旧看门狗 pid=$p"
done
sleep 2
for p in $(pgrep -f '_r581_memguard.sh' 2>/dev/null); do
  kill -9 "$p" 2>/dev/null && say "  KILL 旧看门狗 pid=$p"
done
# 连它外面那层 bash -lc 也清掉
for p in $(pgrep -f 'bash _r581_memguard' 2>/dev/null); do
  kill -9 "$p" 2>/dev/null && say "  KILL 外层 pid=$p"
done
sleep 2
say "确认已无 memguard："
ps -eo pid,args --no-headers 2>/dev/null | grep '_r581_memguard' | grep -v grep | sed 's/^/  /' | tee -a "$LOG" || true
echo "  （以上为空即已清干净）" | tee -a "$LOG"

# ② 确认臂都还在（换看门狗**不该**碰到它们）
say "换之前先数臂："
bash _r581_arms.sh 2>/dev/null | sed -n '4,9p' | tee -a "$LOG"

# ③ 起修好的看门狗：1500 MB、8 h、KILL=1
say "起修好的看门狗：阈值 1500 MB（**现在是**真**的 1500 MB**）、8 h、KILL=1"
nohup setsid bash _r581_memguard.sh 1500 8 1 > _w2_r581_memguard_outer.log 2>&1 < /dev/null &
sleep 4
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '_r581_memguard.sh 1500' | grep -v grep | sed 's/^/  /' | tee -a "$LOG"
say "=== R581-R160 WDSWAP DONE ==="
