#!/bin/bash
# _t5_fix4.sh --- ★★★★★ 修正臂：**两个约束同时满足**（§41.2）
#
# ## 为什么还要再起一臂（**记账**）
# * 约束 1「总场数」`nv ≥ B·n = 3×23 = 69` —— `t5G3`（nv=72）**已满足**；
# * 约束 2「**每个变体组的场数**」`m ≥ 该组板条数` —— `t5G3` 是 `m = 6`（`nvar=12`）
#   ⇒ 单变体结构**到 6 根即封顶**（观测：`nslab_n` 卡在 6 + 3 次拒绝）。
# * **⇒ 本臂取 `nvar=3, m=24`：`nv = 72`（约束1 不变、内存不变），`m = 24 ≥ 23`（约束2 满足）。**
#
# ⚠ 启动方式：本脚本**末尾 `wait`**（§19.1 的教训：起完就退出会把臂一起收走），
#   并且由 pwsh 以**托管后台作业**方式跑（双保险）。
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LG=_w2_t5_fix4.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LG"; }

say '════ ① 停 t5G3（**只 kill，不删任何数据**）════'
for p in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep 'tag t5G3' | awk '{print $1}'); do
  kill -TERM "$p" 2>/dev/null && say "  TERM $p（tag=t5G3）"
done
sleep 8
for p in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep 'tag t5G3' | awk '{print $1}'); do
  kill -9 "$p" 2>/dev/null && say "  KILL $p（仍在则强杀）"
done
sleep 3
[ -z "$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py')" ] && say '  ✅ 已全部停止'
say '  ── 旧臂数据**都在**（不删、可 --resume）──'
for t in t5L62 t5L0 t5G3; do du -sh "_exp/_bk_t5/dry_$t" 2>/dev/null | sed 's/^/    /'; done

say '════ ② 两个约束的检查（**先算，再跑**）════'
$PY - <<'PYEOF' | tee -a "$LG"
n, B = 23, 3
print('  n(T_end) = %d（固定；α_KM 是用户给的物理输入）' % n)
print('  约束1 总场数      : nv >= B*n = %d' % (B * n))
print('  约束2 每变体组场数 : m  >= 该组板条数（单变体时 = n(T_end) = %d）' % n)
print()
for nvar, m in ((12, 6), (3, 24), (4, 18)):
    nv = nvar * m
    print('  nvar=%-3d m=%-3d ⇒ nv=%-4d  约束1 %s   约束2 %s'
          % (nvar, m, nv, '✅' if nv >= B * n else '❌',
             '✅' if m >= n else '❌'))
print()
print('  ⇒ **本臂取 nvar=3 / m=24**（nv=72 与 t5G3 相同 ⇒ 内存不变；m=24 >= 23 ⇒ 单组够用）')
PYEOF

say '════ ③ 起修正臂 t5H3（N=160 / nvar=3 / m=24 ⇒ nv=72 / B=3）════'
say "  内存：$(free -m | awk '/Mem:/{printf "用 %d MB / 余 %d MB", $3, $7}')"
$PY _t5_short.py --tag t5H3 \
   --N 160 --nvar 3 --m 24 --B 3 --steps 6000 --cores 0-7 --mem-limit-gb 14.0 \
   --overlap-nm 62.5 --every 20 --snap-every 40 --pair-every 50 \
   --ckpt-every 20 --ckpt-keep 2 --archive-old > _w2_t5_fix4_A.log 2>&1 &
NP=$!
say "  ★ pid=$NP（tag=t5H3）—— 本脚本会**一直等它**"
sleep 150
say '  ── 150 s 后：引擎横幅里的关键行 ──'
grep -E 'nv=|总根数|必须至少|几何上界|导出板条数' _w2_t5_short_t5H3.log 2>/dev/null | head -5 | sed 's/^/    /'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | awk '{printf "  进程 pid=%s 已跑=%s\n", $1, $2}'
wait $NP
say "  臂结束：exit=$?"
say '=== FIX4 DONE ==='
