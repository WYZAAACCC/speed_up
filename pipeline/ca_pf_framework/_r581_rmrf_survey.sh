#!/bin/bash
# _r581_rmrf_survey.sh --- 盘点全仓"**rm -rf 打在运行目录上**"的脚本（goal 硬禁令）
cd "$(dirname "$0")" || exit 1
echo "NOW = $(date '+%F %T')"
echo
echo '════ ① 命中 `rm -rf` 且参数里含 `_exp` / `dry_` / `_bk_` 的 .sh ════'
n=0
for f in $(grep -rl 'rm -rf' --include='*.sh' . 2>/dev/null); do
  # 只看**真会执行**的行（排除注释）
  hit=$(grep -n 'rm -rf' "$f" 2>/dev/null | grep -v '^[0-9]*: *#' \
        | grep -E '_exp|dry_|_bk_' || true)
  [ -n "$hit" ] || continue
  n=$((n + 1))
  echo "  ── $f ──"
  printf '%s\n' "$hit" | head -3 | cut -c1-118 | sed 's/^/      /'
done
echo
echo "  ⇒ 命中脚本数：**$n**"
echo
echo '════ ② 对照：仓库里有没有现成的"安全删除"写法可复用 ════'
grep -rln 'superseded' --include='*.sh' . 2>/dev/null | head -8 | sed 's/^/  /'
echo
echo '════ ③ `_r30_regress.sh` 那一行的原文 ════'
grep -n 'rm -rf' _r30_regress.sh 2>/dev/null | sed 's/^/  /'
