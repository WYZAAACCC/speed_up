#!/bin/bash
# _t5_fix2.sh --- ★★★★★ 修复臂 2：满足引擎自己的**一致性条件** `nv ≥ B·n(T_end)`
#
# ## 为什么上一版修法错了（**记账**）
# `_t5_fix1.sh` 用的是「nvar 12→4、m 4→12」（nv 仍 48）⇒ 我当时的理由是"内存中性、单变体能容纳更多"。
# **但引擎的启动横幅自己写明了真正的要求**：
#   总根数 = B · n(T_end) = 5 × 23 = **115 根**
#   ⚠ **要真拿到 115 根，`--laths` 必须至少 115 个（当前 nv=48）**
# ⇒ **真正的一致性条件是 `nv ≥ B · n(T_end)`**，与"分布"无关。
# ⇒ 本脚本按这个条件选配置。
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LG=_w2_t5_fix2.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LG"; }

say '════ ① 停旧 B 臂（t5L0）—— **只 kill，不删数据** ════'
for p in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep 'tag t5L0' | awk '{print $1}'); do
  kill -TERM "$p" 2>/dev/null && say "  TERM $p（tag=t5L0）"
done
sleep 6
for p in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep 'tag t5L0' | awk '{print $1}'); do
  kill -9 "$p" 2>/dev/null && say "  KILL $p"
done
sleep 3
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | awk '{printf "  剩余 pid=%s 已跑=%s\n", $1, $2}'
[ -z "$(ps -eo args --no-headers 2>/dev/null | grep '[_]bk_exp.py')" ] && say '  ✅ 已全部停止'
say '  ── 旧臂数据**都在**（不删，可 --resume）──'
for t in t5L62 t5L0; do du -sh "_exp/_bk_t5/dry_$t" 2>/dev/null | sed 's/^/    /'; done

say '════ ② 一致性检查：nv ≥ B·n(T_end) ════'
$PY - <<'PYEOF'
n = 23            # n(T_end) = floor(α_KM·(M_s−T_end))，α_KM 是用户输入、不动
print('  n(T_end) = %d（固定；α_KM 是用户给的物理输入，不动）' % n)
print('  %-6s %-10s %-8s %s' % ('B', '需要 nv', '给 nv', '判定'))
for B, nv in ((5, 48), (3, 72), (2, 48)):
    need = B * n
    print('  %-6d %-10d %-8d %s' % (B, need, nv, '✅ 够' if nv >= need else '❌ **不够**'))
print()
print('  ⇒ 本跑取：**B=3、nv=72（nvar=12 × m=6）** ⇒ 需要 69 ≤ 72 ✓')
PYEOF

say '════ ③ 起修复臂：N=160 / nvar=12 / m=6（nv=72）/ B=3 ════'
say "  内存：$(free -m | awk '/Mem:/{printf "用 %d MB / 余 %d MB", $3, $7}')"
$PY _t5_short.py --tag t5G3 \
   --N 160 --nvar 12 --m 6 --B 3 --steps 6000 --cores 0-7 --mem-limit-gb 14.0 \
   --overlap-nm 62.5 --every 20 --snap-every 40 --pair-every 50 \
   --ckpt-every 20 --ckpt-keep 2 --archive-old > _w2_t5_fix2_A.log 2>&1 &
NP=$!
say "  ★ 修复臂 pid=$NP（tag=t5G3，核 0-7，nv=72，B=3）"
sleep 90
say '  ── 90 s 后 ──'
ps -eo pid,etime,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | awk '{printf "    pid=%s 已跑=%s\n", $1, $2}'
free -m | sed -n 2p | sed 's/^/    /'
say '  ── ★ 引擎横幅里的一致性行（必须出现"当前 nv=72"且不再警告不够）──'
grep -E '总根数|必须至少|几何上界|N8 自动推导' _w2_t5_short_t5G3.log 2>/dev/null | sed 's/^/    /'
say '=== FIX2 LAUNCHED ==='
