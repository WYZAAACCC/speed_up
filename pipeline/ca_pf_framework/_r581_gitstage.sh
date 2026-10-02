#!/bin/bash
# _r581_gitstage.sh --- ★★★ 安全暂存：**只暂存"显式点名的文本文件"**，绝不碰数据
#
# ## 为什么不能用 `git add -A`
# 实测（`_r581_gitplan.sh`）：**未跟踪文件 14,796 个**，其中
# **>1 MB 的有 743 个、合计 5.13 GB**（含 7 个 **157 MB 的 `seeds.npz`**）
# ⇒ `git add -A` 会把 5 GB 数据灌进 .git ⇒ **必须只按名单暂存**。
#
# ## 名单规则（**只收文本、只收本项目本轮新写的**）
# ① `git add -u` ⇒ 所有**已跟踪·被改**的文件（实测 29 个，最大 0.82 MB，全是文本）
# ② 显式加入：`pipeline/ca_pf_framework/` 下**本轮新写**的 `_r581_*.{py,sh}` /
#    `R581_*.md` / `GOAL_*.md`（**按模式匹配，但排除 `_exp/`、`_r580_backup/`、日志**）
# ③ **绝不加入**：`_exp/**`、`*.npz`、`*.csv`(数据)、`_w2_*`(日志)、`_r580_backup/**`
set -u
cd /mnt/f/speed_up || exit 1
MODE="${1:-dry}"

echo "NOW = $(date '+%F %T')   模式=$MODE"
echo
echo '════ ① 先 `git add -u`（已跟踪·被改）════'
git add -u
echo "  已暂存：$(git diff --cached --name-only | wc -l) 个"
echo
echo '════ ② 显式加入本轮的文本脚本/文档（**排除数据与日志**）════'
n=0
for f in pipeline/ca_pf_framework/_r581_*.py \
         pipeline/ca_pf_framework/_r581_*.sh \
         pipeline/ca_pf_framework/R581_*.md \
         pipeline/ca_pf_framework/GOAL_*.md \
         pipeline/ca_pf_framework/_r580_snapshot.sh \
         pipeline/ca_pf_framework/_r580_rollback.sh; do
  [ -f "$f" ] || continue
  case "$f" in
    *_exp/*|*_r580_backup/*|*_w2_*) continue ;;
  esac
  s=$(stat -c%s "$f")
  # ★ 硬闸：单文件 >512 KB 的文本也不收（防意外）
  if [ "$s" -gt 524288 ]; then
    printf '  ⚠ **跳过（>512KB）** %-58s %8.1f KB\n' "$f" "$(echo "$s/1024" | bc -l)"
    continue
  fi
  git add -- "$f" 2>/dev/null && n=$((n + 1))
done
echo "  显式加入：$n 个"
echo
echo '════ ③ ★ 安全检查：暂存区里有没有"大文件/数据文件" ════'
bad=0
git diff --cached --name-only | while read -r f; do
  case "$f" in
    *.npz|*.npy|*.png|*.jpg|*.so|*.xml) echo "  ❌ **数据/二进制**：$f"; bad=1 ;;
  esac
  [ -f "$f" ] || continue
  s=$(stat -c%s "$f")
  [ "$s" -gt 1048576 ] && printf '  ❌ **>1MB**：%-58s %.2f MB\n' "$f" "$(echo "$s/1048576" | bc -l)"
done
echo "  （以上为空 ⇒ 安全）"
echo
echo '════ ④ 暂存区汇总 ════'
printf '  文件数：%s\n' "$(git diff --cached --name-only | wc -l)"
printf '  总体积：%.2f MB\n' \
  "$(git diff --cached --name-only | while read -r f; do [ -f "$f" ] && stat -c%s "$f"; done \
     | awk '{s+=$1} END {printf "%.2f", s/1048576}')"
echo
echo '  ── 按目录聚合（前 12）──'
git diff --cached --name-only | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn | head -12 | sed 's/^/    /'
echo
if [ "$MODE" = "commit" ]; then
  echo '════ ⑤ 提交 ════'
  MSG="${2:-R581 stage checkpoint}"
  git commit -q -m "$MSG" && echo "  ✅ 已提交：$(git log --oneline -1)"
else
  echo '  （dry 模式：**未提交**。要提交请传 commit "<消息>"）'
fi
echo
echo '════ ⑥ 提交后的仓库体积 ════'
du -sh .git 2>/dev/null | sed 's/^/  /'
