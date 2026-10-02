#!/bin/bash
# _r580_rollback.sh <tag> [--apply] [--no-regress] --- ★ 原始代码保险：从文件级快照恢复。
#
# ## 为什么不用 git
# 实测：`git log --oneline -1` = **fe550c27 R48**，而工作区已经在 **R579**
# ⇒ 领先 HEAD 约 500 轮。`git checkout` / `git stash` 会抹掉几百轮工作。
# 故一律用 `_r580_snapshot.sh` 的文件级快照 + SHA256 相互校验。
# ⚠ 本脚本**不写 git**（不 commit / 不 tag / 不 stash / 不 checkout）。
#
# ## 用法
#   bash _r580_rollback.sh afterP1              # 只看差异（dry-run，默认）
#   bash _r580_rollback.sh afterP1 --apply      # 真恢复（先自动给"当前状态"再打一份快照）
#
# ## 流程（--apply）
#   1) 定位 `_r580_backup/<tag>*`（必须唯一，多个就报错并列出，绝不猜）
#   2) `sha256sum -c SHA256SUMS` 校验快照自身完整 —— **不符就拒绝恢复**
#   3) ★ 先把"当前工作区"打一份快照（tag = `<tag>_rollback_from_<ts>`）
#      ⇒ 连"回滚"这个动作本身也可回滚
#   4) 只覆盖快照里存在的文件；快照里没有的文件一律不动
#   5) 复验：工作区里每个恢复文件的 sha256 必须等于快照里的
#   6) 除非 --no-regress，跑一次逐位回归确认"恢复出来的代码真的能跑"
#   7) 全过程追加写 `_r580_rollback_log.txt`
set -u
cd "$(dirname "$0")" || exit 1

TAG="${1:-}"
shift || true
APPLY=0; REGRESS=1
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;;
    --no-regress) REGRESS=0 ;;
    *) echo "未知参数：$a" >&2; exit 2 ;;
  esac
done
if [ -z "$TAG" ]; then
  echo "用法: bash _r580_rollback.sh <tag> [--apply] [--no-regress]" >&2
  echo "现有快照：" >&2
  ls -1d _r580_backup/*/ 2>/dev/null | sed 's|_r580_backup/||; s|/$||' | sed 's/^/  /' >&2
  exit 2
fi

LOG="_r580_rollback_log.txt"
log() { echo "$*" | tee -a "$LOG"; }

# ---- 1) 定位快照（必须唯一） ----------------------------------------------
mapfile -t HITS < <(ls -1d _r580_backup/"${TAG}"*/ 2>/dev/null | sed 's|/$||')
if [ "${#HITS[@]}" -eq 0 ]; then
  echo "✗ 找不到快照 tag='${TAG}'。现有：" >&2
  ls -1d _r580_backup/*/ 2>/dev/null | sed 's/^/  /' >&2
  exit 3
fi
if [ "${#HITS[@]}" -gt 1 ]; then
  echo "✗ tag='${TAG}' 匹配到 ${#HITS[@]} 个快照，拒绝猜测，请给更完整的 tag：" >&2
  printf '  %s\n' "${HITS[@]}" >&2
  exit 3
fi
SNAP="${HITS[0]}"
log "=============================================================="
log "[$(date '+%F %T')] rollback tag='${TAG}' snap='${SNAP}' apply=${APPLY}"

# ---- 2) 快照自身完整性 ----------------------------------------------------
if [ ! -f "$SNAP/SHA256SUMS" ]; then
  log "✗ 快照缺 SHA256SUMS ⇒ 拒绝恢复（无法证明快照是完整的）"
  exit 4
fi
if ! ( cd "$SNAP" && sha256sum -c SHA256SUMS >/dev/null 2>&1 ); then
  log "✗ 快照 SHA256SUMS 校验失败 ⇒ 拒绝恢复。明细："
  ( cd "$SNAP" && sha256sum -c SHA256SUMS 2>&1 ) | sed 's/^/    /' | tee -a "$LOG"
  exit 4
fi
log "  ✓ 快照 SHA256 校验通过（$(wc -l < "$SNAP/SHA256SUMS") 个文件）"

# ---- 3) 差异清单 ----------------------------------------------------------
mapfile -t SNAPF < <(cd "$SNAP" && ls -1 *.py 2>/dev/null)
if [ "${#SNAPF[@]}" -eq 0 ]; then
  log "✗ 快照里没有任何 .py ⇒ 拒绝恢复"; exit 4
fi
DIFFN=0
for f in "${SNAPF[@]}"; do
  if [ ! -f "$f" ]; then
    log "  [新增] $f  （工作区没有，恢复会创建它）"; DIFFN=$((DIFFN+1)); continue
  fi
  if cmp -s "$SNAP/$f" "$f"; then
    log "  [同  ] $f"
  else
    log "  [不同] $f  当前=$(sha256sum "$f" | cut -c1-16)  快照=$(sha256sum "$SNAP/$f" | cut -c1-16)"
    DIFFN=$((DIFFN+1))
  fi
done
log "  差异文件数：$DIFFN / ${#SNAPF[@]}"

if [ "$APPLY" -ne 1 ]; then
  log "  （dry-run，未改动任何文件。要真恢复请加 --apply）"
  exit 0
fi
if [ "$DIFFN" -eq 0 ]; then
  log "  工作区与快照已一致，无需恢复。"
  exit 0
fi

# ---- 4) 先给"当前工作区"留一份（让回滚本身也可回滚）------------------------
CURTAG="rollback_from_${TAG}"
log "  → 先给当前工作区打快照：$CURTAG"
if ! bash _r580_snapshot.sh "$CURTAG" "回滚到 ${TAG} 之前的自动留档" >/dev/null 2>&1; then
  log "✗ 当前状态快照失败 ⇒ 拒绝继续（否则回滚将不可逆）"
  exit 5
fi
NEWSNAP=$(ls -1d _r580_backup/"${CURTAG}"*/ 2>/dev/null | tail -1 | sed 's|/$||')
log "  ✓ 当前状态留档于：${NEWSNAP:-（未取到！）}"
if [ -z "$NEWSNAP" ]; then log "✗ 留档目录未取到 ⇒ 拒绝继续"; exit 5; fi

# ---- 5) 恢复（逐个文件，失败立刻停） --------------------------------------
for f in "${SNAPF[@]}"; do
  cp -p "$SNAP/$f" "$f" || { log "✗ 恢复 $f 失败 ⇒ 中止（已恢复的保持原样，留档在 $NEWSNAP）"; exit 6; }
done
log "  ✓ 已覆盖 ${#SNAPF[@]} 个文件"

# ---- 6) 复验 sha256 -------------------------------------------------------
BAD=0
for f in "${SNAPF[@]}"; do
  A=$(sha256sum "$SNAP/$f" | cut -d' ' -f1)
  B=$(sha256sum "$f" | cut -d' ' -f1)
  if [ "$A" != "$B" ]; then log "  ✗ $f 恢复后 sha256 不符！  期望 ${A:0:16} 实得 ${B:0:16}"; BAD=1; fi
done
if [ "$BAD" -ne 0 ]; then log "✗ 复验失败"; exit 7; fi
log "  ✓ 复验：${#SNAPF[@]} 个文件 sha256 与快照逐一相符"

# ---- 7) 逐位回归（证明"恢复出来的代码真的能跑"）----------------------------
if [ "$REGRESS" -eq 1 ]; then
  if [ -f _r576_regress.sh ]; then
    log "  → 跑逐位回归 _r576_regress.sh ..."
    if bash _r576_regress.sh >"_r580_rollback_regress_$(date '+%Y%m%d_%H%M%S').log" 2>&1; then
      log "  ✓ 回归通过（证明恢复后的代码可以跑）"
    else
      log "  ✗ 回归失败！恢复出来的代码跑不通 —— 见 _r580_rollback_regress_*.log"
      exit 8
    fi
  else
    log "  ⚠ 找不到 _r576_regress.sh，跳过回归（--no-regress 同效）"
  fi
fi
log "★ 回滚完成：工作区 = ${SNAP}"
log "  若要撤销这次回滚：bash _r580_rollback.sh ${CURTAG} --apply"
log "=============================================================="
exit 0
