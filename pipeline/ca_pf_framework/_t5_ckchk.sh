#!/bin/bash
# _t5_ckchk.sh --- ★★★ 长跑**健康与检查点新鲜度**的核查（30 h 长跑的关键风险）
#
# ## 为什么这条值得单独查
# * 若**检查点没在写**，跑 30 h 后一旦被杀 ⇒ **全部丢失**；
# * 若**日志不再增长**，说明进程卡住（而不是"慢"）；
# * 若**内存逼近上限**，WSL 可能整机卡死（§3.12）。
# ⇒ 这三条是"长跑能不能活到里程碑"的**充分必要条件**。
cd "$(dirname "$0")" || exit 1
T=${1:-t5H3}
D="_exp/_bk_t5/dry_$T"
echo "NOW = $(date '+%F %T')    臂 = $T"
echo
echo '════ ① 进程 ════'
ps -eo pid,etime,rss,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' \
  | awk '{printf "  pid=%s 已跑=%s RSS=%.2f GB\n", $1, $2, $3/1048576}'
echo
echo '════ ② ★ 检查点新鲜度（关键）════'
for f in "$D"/ckpt/*.npz; do
  [ -f "$f" ] || continue
  printf '  %-34s %8.1f MB   写出于 %s（%.1f 分钟前）\n' \
    "$(basename "$f")" "$(echo "scale=1; $(stat -c%s "$f")/1048576" | bc)" \
    "$(stat -c%y "$f" | cut -c1-19)" \
    "$(echo "scale=1; ($(date +%s) - $(stat -c%Y "$f"))/60" | bc)"
done
echo "  （--ckpt-every 20 ⇒ 每 20 步写一次；按 ~19 s/步 ⇒ 每 ~6 分钟应刷新）"
echo
echo '════ ③ 日志是否在增长 ════'
L="_w2_t5_short_$T.log"
printf '  %s：%s 字节，末次修改 %s（%.1f 分钟前）\n' "$L" \
  "$(stat -c%s "$L")" "$(stat -c%y "$L" | cut -c1-19)" \
  "$(echo "scale=1; ($(date +%s) - $(stat -c%Y "$L"))/60" | bc)"
echo
echo '════ ④ 内存余量（WSL 卡死风险）════'
free -m | sed -n 2p | sed 's/^/  /'
echo "  判据：余量应 > 3 GB；两臂 N=160 的配置上限是 22 GB（P23）"
echo
echo '════ ⑤ 产物体积 ════'
du -sh "$D" 2>/dev/null | sed 's/^/  /'
ls -1 "$D"/snap_*.npz 2>/dev/null | wc -l | sed 's/^/  snap 个数: /'
