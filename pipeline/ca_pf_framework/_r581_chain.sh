#!/bin/bash
# _r581_chain.sh --- ★ **顺序链**：等指定的臂全部跑完 ⇒ 过内存闸 ⇒ 起下一个 ⇒ 再等 ⇒ 再起。
#
# ## 为什么要有它（R581-R10 的实测教训）
# R8 我看到"机器 89.9% idle"就**提前起了第三个臂**，结果 R10 内存掉到
# **可用 2491 MB**（三臂 RSS 合计 18.69 GB），已经**低于 softguard 的 2600 MB 阈值**、
# 逼近 memguard 的 1800 MB（那会**一次杀掉三臂**）。
# ⇒ 被迫**中途停掉最年轻的臂**才保住跑到 step 470/500 的两臂。
#
# **教训（已写成 P23）**：**"还有多少核闲着"不是判据；"还有多少内存"才是。**
#   `a ≈ 19 B/胞·nv`（VmHWM 口径）⇒ N=160/nv=48 单臂峰值 **5–7 GB**，
#   **三臂就是 18–21 GB**，已经贴着 WSL 的 24 GB 上限。
#   ⇒ **N=160 的臂最多同时跑 2 个。**
#
# 用法: bash _r581_chain.sh <最小可用内存MB> "<tag1>" "<tag2>" ...
#   例: bash _r581_chain.sh 9000 p2_b5 p2_b3 p2_b5ov p2_b5ps
#   会**依次**：等 p2_b5、p2_b3 都结束 → 起 p2_b5ov → 等它结束 → 起 p2_b5ps
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
MIN_MB="${1:?用法: bash _r581_chain.sh <最小可用MB> <tag...>}"; shift
TAGS=("$@")
LOG=_w2_r581_chain.log
: > "$LOG"

# 每个 tag 对应的参数（**写死，避免外层 PowerShell 破坏参数**）
args_of() {
  case "$1" in
    p2_b5)    echo "--N 160 --m 4 --B 5  --cores 0-3" ;;
    p2_b3)    echo "--N 160 --m 4 --B 3  --cores 4-7" ;;
    p2_b5ov)  echo "--N 160 --m 4 --B 5 --overlap-nm 62.5 --cores 0-3" ;;
    p2_b5ps)  echo "--N 160 --m 4 --B 5 --overlap-nm 62.5 --periodic-seed 1 --cores 4-7" ;;
    *)        echo "" ;;
  esac
}

running() { ps -eo args --no-headers 2>/dev/null | grep "_bk_exp.py" | grep -q -- "--tag $1 "; }

echo "[$(date '+%F %T')] 顺序链启动：${TAGS[*]}；内存闸 = ${MIN_MB} MB" | tee -a "$LOG"

for T in "${TAGS[@]}"; do
  # ---- 阶段 1：等它（如果已经在跑）/ 或直接起（如果不在跑且不在队列里）----
  if running "$T"; then
    echo "[$(date '+%F %T')] $T 已在跑 ⇒ 等它结束" | tee -a "$LOG"
    while running "$T"; do sleep 30; done
    echo "[$(date '+%F %T')] $T 已结束" | tee -a "$LOG"
    continue                     # 已经在跑的臂不用再起
  fi
  # 若这个 tag 已经有**完成**的产物（series.csv 行数 > 100），说明跑过了 ⇒ 跳过
  S="_exp/_bk_p2/dry_${T}/series.csv"
  if [ -f "$S" ] && [ "$(wc -l < "$S")" -gt 100 ]; then
    echo "[$(date '+%F %T')] $T 已有完成产物（$(wc -l < "$S") 行）⇒ 跳过" | tee -a "$LOG"
    continue
  fi
  # ---- 阶段 2：等**所有**在跑的臂结束（内存闸的前提）----
  # ⚠⚠ **第一版在这里死循环（留痕）**：我写 `ps -eo args | grep -q "_bk_exp.py"` ——
  #   而 **`grep` 自己的命令行里就含 `_bk_exp.py`** ⇒ **grep 匹配到自己** ⇒ 条件恒真
  #   ⇒ 链**永远卡在这一步**（实测：11:39:50 之后 3 分钟无进展，机器已全空）。
  #   与 AGENTS §3.10（`pkill -f` 杀掉自己）**同一类**。
  # ⇒ 修法：**`grep -v grep`**；计数也用同一条（不许两处写法不一致）。
  _n_arms() {
    ps -eo args --no-headers 2>/dev/null | grep "_bk_exp.py" | grep -vc grep
  }
  while [ "$(_n_arms)" -gt 0 ]; do
    sleep 30
  done
  # ---- 阶段 3：内存闸 ----
  for _ in $(seq 1 120); do
    AV=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
    [ "$AV" -ge "$MIN_MB" ] && break
    echo "  [$(date '+%F %T')] MemAvailable=${AV} MB < ${MIN_MB} MB ⇒ 等 60 s" | tee -a "$LOG"
    sleep 60
  done
  echo "[$(date '+%F %T')] 内存闸通过（可用 $(awk '/MemAvailable/{print $2}' /proc/meminfo) MB）" | tee -a "$LOG"
  # ---- 阶段 4：起跑 ----
  A=$(args_of "$T")
  if [ -z "$A" ]; then echo "  ❌ 不知道 $T 的参数 ⇒ 跳过" | tee -a "$LOG"; continue; fi
  echo "[$(date '+%F %T')] ▶ 起 $T ：$A" | tee -a "$LOG"
  # ⚠ 前台阻塞（用 pwsh 工具的 run_in_background 承载），跑完才继续
  $PY _r581_p2.py --run --tag "$T" $A 2>&1 | tail -20 | tee -a "$LOG"
  echo "[$(date '+%F %T')] ■ $T 完成" | tee -a "$LOG"
done
echo "[$(date '+%F %T')] 顺序链全部完成" | tee -a "$LOG"
