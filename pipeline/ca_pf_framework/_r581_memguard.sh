#!/bin/bash
# _r581_memguard.sh --- 系统级内存看门狗（**R160 修单位；R162 改成有界杀**）
#
# ## 历史（两次修正，都留档）
# * **R160**：旧版拿 `MemAvailable` 的 **kB** 去比 **MB** 阈值 ⇒ 阈值放大 1024 倍 ⇒ **从不触发**（P41）。
#   修法：单位写进变量名（`LIM_MB`/`AV_MB`）+ 在读的地方换算一次；并加 `KILL=0|1` 使报警**可被反向测试**。
# * **R162**：R161 里它**真的触发了一次**，然后**一刀切杀了 4 条 `_bk_exp.py`**
#   （含两条 **117 min** 的 N=160 臂）。**实测发现那两条其实**只到 step 0****（见 R161 §1.90），
#   损失极小 —— **但"杀全部"这个设计本身是错的**：
#   **它不区分"哪条最值钱"，也不在杀一条之后**重测**** ⇒ 可能为省 1 GB 而毁掉 10 小时。
#
# ## 本版（R162）的两条改进
# 1. **按 RSS **从大到小**逐个杀，**每杀一个就重测**** ⇒ 一旦回到阈值以上就**立刻停手**；
# 2. **支持 `PROTECT`（要保的 tag 列表）** ⇒ 明确标了"值钱"的臂**不会被它杀**
#    （**宁可杀小臂、也不碰大臂** —— 因为"值钱"不是机器能判断的，必须由人标注）。
#
# ## 用法
#   bash _r581_memguard.sh <阈值MB> <最长小时> [KILL] [PROTECT_TAGS]
#   例：bash _r581_memguard.sh 1500 8 1 "p2_m20 p2_m12"
#   自检：bash _r581_memguard.sh 999999 0.02 0        # 阈值必然越界 ⇒ 应看到报警（只报不杀）
#
# ## ⚠ 仍要说清它**不能**做什么
# * 它**仍然会杀**（KILL=1 时）—— **`PROTECT` 之外的**都会被考虑；
# * **`KILL=1` 的真杀分支没有反向测试过**（**会杀人，不能测**）⇒ 只靠代码审查；
# * **它救的是"整机卡死"**（AGENTS §3.12），**不是"保住每一条臂"**。
set -u
cd "$(dirname "$0")" || exit 1
LIM_MB="${1:-1500}"
HOURS="${2:-8}"
KILL="${3:-1}"
PROTECT="${4:-}"                     # ★ 空格分隔的 tag 列表，例如 "p2_m20 p2_m12"
LOG=_w2_r581_memguard.log
END=$(( $(date +%s) + $(printf '%.0f' "$(echo "$HOURS * 3600" | bc -l)") ))
echo "[$(date '+%F %T')] memguard 启动：阈值 ${LIM_MB} MB，最长 ${HOURS} h，KILL=${KILL}，PROTECT='${PROTECT}'" | tee -a "$LOG"

avail_mb()     { awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo; }
swap_used_mb() { awk '/SwapTotal/{t=$2} /SwapFree/{f=$2} END{printf "%d", (t-f)/1024}' /proc/meminfo; }

# 列出 (rss_kb pid tag)，按 rss **降序**；跳过 PROTECT 里的 tag
list_by_rss() {
  for P in $(pgrep -f '_bk_exp.py' 2>/dev/null); do
    C=$(tr '\0' ' ' < "/proc/$P/cmdline" 2>/dev/null)
    T=$(printf '%s' "$C" | sed -n 's/.*--tag \([^ ]*\).*/\1/p')
    R=$(awk '/VmRSS/{print $2}' "/proc/$P/status" 2>/dev/null)
    [ -z "${R:-}" ] && continue
    skip=0
    for pt in $PROTECT; do [ "$T" = "$pt" ] && skip=1; done
    [ "$skip" = "1" ] && continue
    echo "$R $P ${T:-?}"
  done | sort -rn
}

WARN=0
while [ "$(date +%s)" -lt "$END" ]; do
  AV_MB=$(avail_mb)
  if [ "$AV_MB" -lt "$LIM_MB" ]; then
    WARN=$((WARN+1))
    echo "[$(date '+%F %T')] ⚠⚠ available=${AV_MB} MB < ${LIM_MB} MB（第 $WARN 次）；swap_used=$(swap_used_mb) MB" | tee -a "$LOG"
    if [ "$KILL" = "1" ]; then
      # ★ 逐个杀 + 每杀一个重测（R162 的核心改动）
      for line in $(list_by_rss | awk '{print $2":"$1":"$3}'); do
        PID=${line%%:*}; rest=${line#*:}; RSSKB=${rest%%:*}; TAG=${rest#*:}
        AV_NOW=$(avail_mb)
        if [ "$AV_NOW" -ge "$LIM_MB" ]; then
          echo "    ✅ available 已回到 ${AV_NOW} MB（≥ ${LIM_MB}）⇒ **停手**" | tee -a "$LOG"
          break
        fi
        echo "    ↑ 杀 tag=${TAG} pid=${PID} rss=$((RSSKB/1024))MB（当前 available=${AV_NOW} MB）" | tee -a "$LOG"
        kill -TERM "$PID" 2>/dev/null || true
        sleep 5
        kill -9 "$PID" 2>/dev/null || true
        sleep 3
      done
      # 保护名单提示（**即使没杀到它，也记一笔**）
      if [ -n "$PROTECT" ]; then
        echo "    （PROTECT='${PROTECT}' 里的臂**未被考虑**）" | tee -a "$LOG"
      fi
    else
      echo "   （KILL=0 ⇒ 只报不杀）" | tee -a "$LOG"
    fi
    sleep 20
    AV2_MB=$(avail_mb)
    echo "[$(date '+%F %T')]    处理后 available=${AV2_MB} MB" | tee -a "$LOG"
    if [ "$AV2_MB" -lt "$LIM_MB" ]; then
      echo "  ❌ 仍不足（且已无可杀的、或全在 PROTECT 里）⇒ 退出（需人工介入）" | tee -a "$LOG"
      exit 2
    fi
  fi
  sleep 20
done
echo "[$(date '+%F %T')] memguard 正常退出（跑满 ${HOURS} h，触发 ${WARN} 次）" | tee -a "$LOG"
