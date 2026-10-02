#!/bin/bash
# _r580_snapshot.sh <tag> [备注...] --- ★ 原始代码保险：把"当前这一版引擎源码"整体快照下来。
#
# ## 为什么要文件级快照，而不是 git
# 实测：`git log --oneline -1` = **fe550c27 R48**，而工作区已经在 **R579**
# ⇒ 工作区**领先 HEAD 约 500 轮**。`git checkout` / `git stash` 会抹掉几百轮工作
# ⇒ **git 不是可用的回滚点**。故一律用文件级快照 + SHA256 校验。
# ⚠ 本脚本**不写 git**（不 commit / 不 tag / 不 stash），以免扰动仓库历史。
#
# ## 用法
#   bash _r580_snapshot.sh baseline_R579 "本轮开工前的已验证基线"
#   bash _r580_snapshot.sh L1_D_before "L1 车道改 adv.extend 之前"
#
# ## 产物
#   _r580_backup/<tag>_<YYYYmmdd_HHMMSS>/
#       <7 个源文件>
#       SHA256SUMS           （`sha256sum -c` 可直接校验）
#       MANIFEST.txt         （时间、tag、备注、宿主指纹、各文件 sha256+行数）
set -u
cd "$(dirname "$0")" || exit 1

TAG="${1:-}"
shift || true
NOTE="${*:-（无备注）}"
if [ -z "$TAG" ]; then
  echo "用法: bash _r580_snapshot.sh <tag> [备注...]" >&2
  exit 2
fi

# ★ 必须快照的文件集合：三个引擎文件 + 它们 import 的兄弟模块 + builder
FILES=(
  windowB_surface.py
  windowB_pf3d.py
  windowB_par.py
  windowB_lath.py
  windowB_acct.py
  windowB_pf.py
  _bk_exp.py
)

TS=$(date '+%Y%m%d_%H%M%S')
DEST="_r580_backup/${TAG}_${TS}"
mkdir -p "$DEST" || exit 1

MISS=0
for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then
    cp -p "$f" "$DEST/$f" || MISS=1
  else
    echo "  ⚠ 缺文件：$f（跳过，但会记进 MANIFEST）" >&2
    echo "MISSING $f" >> "$DEST/MANIFEST.txt"
  fi
done

# SHA256SUMS（在 DEST 里生成，路径相对 ⇒ 可从 DEST 直接 -c 校验）
( cd "$DEST" && sha256sum ./*.py > SHA256SUMS 2>/dev/null )

{
  echo "=============================================================="
  echo "tag        : $TAG"
  echo "时间       : $(date '+%F %T %z')"
  echo "备注       : $NOTE"
  echo "仓库       : $(cd ../.. && pwd)"
  echo "目录       : $DEST"
  echo "--------------------------------------------------------------"
  echo "宿主指纹（_r576_hostfp.py，若可用）："
  HFP=$(/root/miniconda3/envs/ml/bin/python _r576_hostfp.py 2>/dev/null | tr '\n' ' ')
  echo "  ${HFP:-（未取到）}"
  echo "--------------------------------------------------------------"
  echo "文件（sha256 前 16 位 / 字节数 / 行数）："
  for f in "${FILES[@]}"; do
    if [ -f "$DEST/$f" ]; then
      H=$(sha256sum "$DEST/$f" | cut -c1-16)
      B=$(stat -c%s "$DEST/$f")
      L=$(wc -l < "$DEST/$f")
      printf '  %-24s %s  %9d B  %6d 行\n' "$f" "$H" "$B" "$L"
    fi
  done
  echo "=============================================================="
} >> "$DEST/MANIFEST.txt"

echo "★ 快照完成：$DEST"
echo "  校验： (cd $DEST && sha256sum -c SHA256SUMS)"
tail -n +2 "$DEST/MANIFEST.txt" | sed 's/^/  /' | head -20
