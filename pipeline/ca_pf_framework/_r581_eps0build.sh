#!/bin/bash
# _r581_eps0build.sh --- ★★★★★ 查 `eps0` 是**怎么造的**（决定 `_pair_normals` 能否记忆化）
#   判据：若 `eps0[k]` 由 `vmap[k]`（变体）**唯一决定** ⇒ 同变体的场**必然**逐位相同 ⇒ 可记忆化。
cd "$(dirname "$0")" || exit 1
OUT=_w2_r581_eps0build.txt
{
  echo "=== 时间：$(date '+%F %T') ==="
  echo
  echo '## ① `_bk_exp.py` 里 `eps0` 是怎么造出来并传进引擎的'
  grep -n "eps0" _bk_exp.py 2>/dev/null | head -30
  echo
  echo '## ② `windowB_surface.py` 里 `eps0` 的**构造/来源**'
  grep -n "eps0" windowB_surface.py 2>/dev/null | head -30
  echo
  echo '## ③ 找 `eps0_of` / `strain_of_variant` 这类"由变体派生"的函数'
  grep -n "def .*eps0\|def .*strain\|eps0_of\|bain\|Bain" windowB_surface.py windowB_pf3d.py 2>/dev/null | head -20
} > "$OUT" 2>&1
cat "$OUT"
