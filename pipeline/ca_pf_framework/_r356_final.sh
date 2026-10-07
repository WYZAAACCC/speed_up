#!/usr/bin/env bash
# _r356_final.sh -- 收尾核对
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
echo "=== 新工具语法 ==="
for f in _r352_pairprobe.py _r353_larr_ident.py _r349_f2geom.py _r350_f2inert.py \
         _r348_dtjson.py _r334_c1diag.py _r335_overlap.py _r338_sdfgrad.py \
         _r341_truedist.py; do
  /root/miniconda3/envs/ml/bin/python -m py_compile "$f" && echo "  ok   $f" || echo "  FAIL $f"
done
echo
echo "=== ledger 卫生 ==="
echo "  行数            : $(wc -l < R30_AUDIT_LEDGER.md)"
echo "  含制表符行数    : $(grep -c -P '\t' R30_AUDIT_LEDGER.md || true)"
echo "  §172 引用次数   : $(grep -c '§172' R30_AUDIT_LEDGER.md || true)"
echo "  撤回/更正标记数 : $(grep -c -E '已被 .§17[0-9]. 撤回|本条已撤回|已撤回（' R30_AUDIT_LEDGER.md || true)"
echo
echo "=== summary 卫生 ==="
echo "  行数            : $(wc -l < AUDIT_SUMMARY_R76.md)"
echo "  含制表符行数    : $(grep -c -P '\t' AUDIT_SUMMARY_R76.md || true)"
echo
echo "=== 本轮新增/修改的源码文件 mtime ==="
ls -l --time-style=+%m-%d_%H:%M _bk_exp.py windowB_surface.py windowB_lath.py 2>&1
