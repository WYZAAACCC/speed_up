#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== n_ath_tgt += 1 occurrences: BEFORE (backup) vs AFTER (live) ==="
echo "--- backup ---"
grep -n 'n_ath_tgt += 1' _bk_exp.py.bak_s291rej
echo "--- live ---"
grep -n 'n_ath_tgt += 1' _bk_exp.py
echo
echo "=== live: the s291 region ==="
sed -n '2600,2625p' _bk_exp.py | cut -c1-120
echo "..."
sed -n '2700,2720p' _bk_exp.py | cut -c1-140
echo
echo "=== compile live ==="
/root/miniconda3/envs/ml/bin/python -m py_compile _bk_exp.py && echo "OK"
