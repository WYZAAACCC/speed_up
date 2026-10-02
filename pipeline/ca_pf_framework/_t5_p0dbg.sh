#!/bin/bash
# _t5_p0dbg.sh --- 第 78 轮：跑一次**带插桩**的续跑短测，直接读出 `P0` 之谜
#
# ## 协议
#   A 臂：跑 20 步（`T5_P0DBG=1`，存帧）⇒ `--resume` 续到 40 步（`T5_P0DBG=1`）
#   B 臂：一次跑完 40 步（`T5_P0DBG=1`）
#   ⇒ 直接对比两臂的 `[P0DBG]` 逐行输出。
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export T5_P0DBG=1
COMMON="--N 96 --nvar 12 --m 6 --B 3 --cores 16-19 --mem-limit-gb 4.0 --every 20 \
        --snap-every 200 --pair-every 50 --ckpt-every 20 --overlap-nm 62.5 --therm-hist linear"

echo '════ 语法 ════'
$PY -m py_compile _bk_exp.py && echo '  ✅ _bk_exp.py SYNTAX_OK（真跑过）'
echo
echo '════ A 臂：20 步 ════'
$PY _t5_short.py --tag dA --steps 20 $COMMON --archive-old > _w2_t5_dbg_A1.log 2>&1
echo "  exit=$?"
echo '════ A 臂续跑：--resume 到 40 步 ════'
$PY _t5_short.py --tag dA --steps 40 $COMMON \
   --resume _exp/_bk_t5/dry_dA/ckpt > _w2_t5_dbg_A2.log 2>&1
echo "  exit=$?"
echo '════ B 臂：一次跑完 40 步 ════'
$PY _t5_short.py --tag dB --steps 40 $COMMON --archive-old > _w2_t5_dbg_B.log 2>&1
echo "  exit=$?"
echo
echo '════ ★ 插桩输出对照（这才是要看的）════'
for t in dA dB; do
  for suf in A1 A2 B; do
    f="_w2_t5_dbg_${t}_${suf}.log"
    [ -f "$f" ] || continue
    n=$(grep -c '\[P0DBG\]' "$f" 2>/dev/null)
    [ "$n" = "0" ] && continue
    echo "  ── $f（$n 行）──"
    grep '\[P0DBG\]' "$f" | sed 's/^/     /'
  done
done
