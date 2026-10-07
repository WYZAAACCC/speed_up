#!/bin/bash
# _r146_chk.sh —— 块内界面自检（P1-43）接线核对 + 语法
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
echo "=== 语法 ==="
$PY -c "import ast; ast.parse(open('_bk_exp.py').read()); ast.parse(open('_bk_measure.py').read()); print('OK')"
echo
echo "=== 量具自检（确认没改坏 `_bk_measure`）==="
$PY _bk_measure.py --selftest 2>&1 | tail -3
echo
echo "=== `cov_baseline` / `cov_norm` 单测（正/负对照）==="
$PY - <<'PY'
import _bk_measure as BM
# 正对照：表里有的 L ⇒ exact=True
for L, want in ((1600e-9, 1.079), (600e-9, 0.532)):
    b, n, ex = BM.cov_baseline(L)
    print('  cov_baseline(%.0f nm) = %.3f (n=%d, exact=%s)  期望 %.3f  ⇒ %s'
          % (L*1e9, b, n, ex, want, 'PASS' if abs(b-want) < 1e-9 and ex else 'FAIL'))
# 表里没有的 L ⇒ exact=False 且取最近档
b, n, ex = BM.cov_baseline(700e-9)
print('  cov_baseline(700 nm) = %.3f (exact=%s)  ⇒ %s'
      % (b, ex, 'PASS（用最近档 600 或 800）' if (not ex and b in (0.532, 0.638)) else 'FAIL'))
# cov_norm 正/负对照
cn, b, n, ex = BM.cov_norm(0.638, 800e-9)
print('  cov_norm(0.638 @ L=800) = %.4f  ⇒ %s' % (cn, 'PASS' if abs(cn-1.0) < 1e-9 else 'FAIL'))
cn2, _, _, _ = BM.cov_norm(0.30, 800e-9)
print('  cov_norm(0.30 @ L=800) = %.4f  ⇒ %s' % (cn2, 'PASS（应明显 <0.95）' if cn2 < 0.95 else 'FAIL'))
PY
echo
echo "=== 在**真的**算例上跑一次自检（N=32、0 步，最省）==="
$PY -u _bk_exp.py --arm dry --N 32 --dx-nm 62.5 --steps 0 --every 20 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --plate-t-physical 400 \
  --laths 1,1,3,3,5,5 --multi-block --block-gap-nm 900 \
  --tag cvchk --out _exp/_bk_cvchk 2>&1 | grep -E '块内界面自检|cov_norm|β 占比|块内.*没过|精确判据' | head -8
