#!/bin/bash
# _r581_p2q.sh --- ★ 排队等某臂跑完再起下一臂（避免三臂同时抢内存带宽）。
#
# 用法: bash _r581_p2q.sh <等待的tag> <新tag> <额外参数...>
# 例:   bash _r581_p2q.sh p2_b3 p2_b5ov "--m 4 --B 5 --overlap-nm 62.5 --cores 4-7"
#
# ## 为什么
# R581-R3 发现 **S4（`--nuc-overlap-nm` 默认 0）直接接在引擎的 `attach_overlap` 上**，
# 而本长跑走的正是 `attach` 通道 ⇒ 块内界面会有 29–62% 的位置留 β 膜（阶梯错位伪影）。
# ⇒ 必须补一个**修好 S4** 的臂来复核 C3。
# 但三臂同时跑会抢内存带宽、把在跑的两臂一起拖慢 ⇒ **排队**。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
WAIT_TAG="$1"; NEW_TAG="$2"; shift 2
LOG=_w2_r581_p2q.log

echo "[$(date '+%F %T')] 排队：等 $WAIT_TAG 跑完，再起 $NEW_TAG（参数：$*）" | tee -a "$LOG"
# ★★ 等待条件（**第一版有坑，留痕**）：
#   第一版写的是 `pgrep -f "tag $WAIT_TAG\b"`。它**能**匹配（`p2_b3` 那条确实在等），
#   但**链式排队会断**：当 WAIT_TAG 是"另一个还没起来的排队臂"时（如 `p2_b5ov`），
#   它**本来就不存在** ⇒ 循环立刻退出 ⇒ **后一个臂提前起跑**。
#   实测后果：`p2_b5ps` 在 `p2_b5ov` 还没起的时候就跑了（三臂同时占 ~14 GB）。
#   ⇒ 现在的写法用 `[[:space:]]` 锚定 tag 的右边界（pgrep 的 ERE 里可靠），
#     并且在起跑前**再查一次**内存，不够就等。
_wait_proc() {
  pgrep -f -- "--tag $1[[:space:]]" > /dev/null 2>&1
}
# ★★ **两阶段等待**（第一版只有"等它消失"⇒ 链式排队会断，留痕）：
#   阶段 1：等目标**出现**（最多 `APPEAR_MIN` 分钟）—— 因为它可能自己还在排队；
#   阶段 2：等它**消失**。
#   ⚠ 若阶段 1 超时 **不会**静默继续，而是**明确报错退出**（不许"看起来排上了、其实没有"）。
APPEAR_MIN="${R581Q_APPEAR_MIN:-180}"
if ! _wait_proc "$WAIT_TAG"; then
  echo "[$(date '+%F %T')] $WAIT_TAG 还没出现 ⇒ 进入阶段 1（最多等 ${APPEAR_MIN} min）" | tee -a "$LOG"
  for _ in $(seq 1 "$APPEAR_MIN"); do
    _wait_proc "$WAIT_TAG" && break
    sleep 60
  done
  if ! _wait_proc "$WAIT_TAG"; then
    echo "[$(date '+%F %T')] ❌ $WAIT_TAG 等了 ${APPEAR_MIN} min 仍未出现 ⇒ **拒绝起 $NEW_TAG**" \
      | tee -a "$LOG"
    echo "    （防"看起来排上了、其实没有"。请人工确认上游作业）" | tee -a "$LOG"
    exit 3
  fi
fi
echo "[$(date '+%F %T')] $WAIT_TAG 已出现 ⇒ 进入阶段 2（等它跑完）" | tee -a "$LOG"
while _wait_proc "$WAIT_TAG"; do
  sleep 30
done
echo "[$(date '+%F %T')] $WAIT_TAG 已结束，30 s 后起 $NEW_TAG" | tee -a "$LOG"
sleep 30
# ★ 起跑前的内存闸：可用内存 < 阈值就继续等（防把 WSL 逼到 swap/卡死）
MIN_MB="${R581Q_MINMB:-6000}"
for _ in $(seq 1 60); do
  AV=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
  [ "$AV" -ge "$MIN_MB" ] && break
  echo "  [$(date '+%F %T')] MemAvailable=${AV} MB < ${MIN_MB} MB ⇒ 再等 60 s" | tee -a "$LOG"
  sleep 60
done
free -m | sed -n 2p | tee -a "$LOG"
$PY _r581_p2.py --run --tag "$NEW_TAG" "$@" 2>&1 | tail -25 | tee -a "$LOG"
echo "[$(date '+%F %T')] $NEW_TAG 完成" | tee -a "$LOG"
