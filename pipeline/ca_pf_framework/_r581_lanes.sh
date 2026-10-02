#!/bin/bash
# _r581_lanes.sh --- ★ goal 成功判据⑧：**车道表**（跑什么 / 绑哪几核 / 起止时间）
#                    + 批次期间的 **load average** 与各道占用实测。
#
# 为什么必须单独产出：判据⑧ 要的是"**并行是真的**"的**证据**，不是"我说我并行了"。
cd "$(dirname "$0")" || exit 1
OUT=_w2_r581_lanes.log
{
echo "=============================================================================="
echo "R581 车道表  ——  生成于 $(date '+%F %T')"
echo "=============================================================================="
echo
echo "── 1. 机器规模 ──"
echo -n "  逻辑核 = "; nproc
echo -n "  CPU 型号 = "; awk -F: '/model name/{print $2; exit}' /proc/cpuinfo | sed 's/^ *//'
echo "  ── load average（1/5/15 min）与运行队列 ──"
awk '{printf "  loadavg = %s %s %s   运行中/总进程 = %s/%s\n", $1,$2,$3,$4,$5}' /proc/loadavg
echo "  ── 内存 ──"
free -m | sed -n '2p' | awk '{printf "  总 %s MB  已用 %s MB  可用 %s MB\n",$2,$3,$7}'
echo
echo "── 2. 当前在跑的仿真臂（实测）──"
ps -eo pid,etime,pcpu,rss,psr,args --no-headers 2>/dev/null | grep '_bk_exp.py' | grep -v grep | \
while read -r pid etime pcpu rss psr rest; do
  t=$(echo "$rest" | awk '{for(i=1;i<=NF;i++) if($i=="--tag") print $(i+1)}')
  ov=$(echo "$rest" | awk '{for(i=1;i<=NF;i++) if($i=="--nuc-overlap-nm") print $(i+1)}')
  printf '  tag=%-10s pid=%-7s 已跑=%-9s CPU=%-5s RSS=%5.2fGB 最后所在核=%s  overlap=%s\n' \
    "$t" "$pid" "$etime" "$pcpu" "$(echo "$rss/1048576" | bc -l)" "$psr" "${ov:-默认0}"
done
echo
echo "  ── 各进程**实际允许**的核（`taskset -pc`）──"
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  t=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="--tag") print $(i+1)}')
  printf '  pid=%-7s tag=%-10s ' "$p" "$t"
  taskset -pc "$p" 2>/dev/null | sed 's/^.*: //' || echo '?'
done
echo
echo "  ── 各进程**实际在用**的核（按 /proc/<pid>/stat 的累计 jiffies 排序，取前 8）──"
for p in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
  t=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="--tag") print $(i+1)}')
  # 采样两次 utime+stime，看这段时间里进程消耗了多少 CPU 时间
  a=$(awk '{print $14+$15}' /proc/$p/stat 2>/dev/null)
  sleep 2
  b=$(awk '{print $14+$15}' /proc/$p/stat 2>/dev/null)
  [ -n "$a" ] && [ -n "$b" ] && \
    printf '  tag=%-10s 2 秒内消耗 %5d jiffies ⇒ 约 **%.2f 核**\n' \
      "$t" "$((b-a))" "$(echo "($b-$a)/200" | bc -l)"
done
echo
echo "── 3. 核占用热图（mpstat，1 次采样）──"
if command -v mpstat > /dev/null 2>&1; then
  mpstat -P ALL 1 1 2>/dev/null | tail -n +4 | \
    awk '$2 ~ /^[0-9]+$/ {printf "  cpu%-3s %%usr=%-6s %%sys=%-6s %%idle=%s\n",$2,$3,$5,$NF}'
else
  echo "  （无 mpstat；用 /proc/stat 两次采样代替）"
  read -r _ u1 n1 s1 i1 w1 _ < /proc/stat
  sleep 2
  read -r _ u2 n2 s2 i2 w2 _ < /proc/stat
  tot1=$((u1+n1+s1+i1+w1)); tot2=$((u2+n2+s2+i2+w2))
  dt=$((tot2-tot1)); du=$((u2-u1)); ds=$((s2-s1)); di=$((i2-i1))
  awk -v dt="$dt" -v du="$du" -v ds="$ds" -v di="$di" -v n="$(nproc)" \
    'BEGIN{printf "  全机 2 秒：usr %.1f%%  sys %.1f%%  idle %.1f%% ⇒ 有效并行度 ≈ **%.2f / %d 核**\n", \
       100*du/dt, 100*ds/dt, 100*di/dt, (du+ds)/dt, n}'
fi
echo
echo "── 4. 本批次的**车道表**（人工维护，脚本只复核进程是否真的在）──"
cat <<'TBL'
  | 车道 | 内容 | 绑核 | 起 | 止 | 状态 |
  |---|---|---|---|---|---|
  | **主线程** | 合并/回归/文档/量具 | — | R581 起 | 进行中 | 🚧 |
  | **L1** | `adv.extend` EDT 合一 | 8-15 | 09:0x | 09:2x | ✅ 1.650× |
  | **L2** | `el.e0.stream` 分块 | 8-15 | 09:3x | 09:5x | ✅ 1.611× |
  | **L4** | `_bbox_pad` 逐轴 any | 12-15 | 10:2x | 10:2x | ✅ 15.362× |
  | **L5** | `argmin2` 复用 | 8-15 | 09:5x | 10:1x | ✅ 3.353× |
  | **L6** | C 扩展融合核 | 8-15 | 10:0x | 10:2x | ✅ 3.338× |
  | **收口** | 能开尽开 vs 全默认 | 8-15 | 10:2x | 10:3x | ✅ 1.232× |
  | **P2 臂 A** | `p2_b5` N=160 B=5 | **0-3** | 08:4x | 进行中 | 🚧 |
  | **P2 臂 B** | `p2_b3` N=160 B=3 | **4-7** | 08:4x | 进行中 | 🚧 |
  | **修复臂 1** | `p2_b5ov`（S4） | 4-7（排队） | — | — | ⏳ |
  | **修复臂 2** | `p2_b5ps`（S4+N13） | 4-7（排队） | — | — | ⏳ |
TBL
echo
echo "── 5. 判据：'并行是真的' 的自检 ──"
NA=$(pgrep -f '_bk_exp.py' 2>/dev/null | wc -l)
LA=$(awk '{print $1}' /proc/loadavg)
echo "  在跑臂数 = $NA ；loadavg(1min) = $LA"
awk -v n="$NA" -v l="$LA" 'BEGIN{
  if (n>=1 && l>=n*0.8) printf "  ⇒ ✅ 负载 %.2f ≥ 臂数 %d × 0.8 ⇒ **并行是真的**\n", l, n;
  else printf "  ⇒ ⚠ 负载 %.2f < 臂数 %d × 0.8 ⇒ 需查（可能被打断/在 I/O）\n", l, n}'
} 2>&1 | tee "$OUT"
echo
echo "（完整输出已写入 $OUT）"
