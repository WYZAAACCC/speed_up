#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== _n_law / n_ath_tgt / _alpha / _Tnow definitions ==="
grep -n '_n_law\|n_ath_tgt *=\|_alpha *=\|_Tnow *=\|_Bt *=\|n_ath_ev *=' _bk_exp.py | cut -c1-170
echo
echo "=== loop head context 2540-2610 ==="
sed -n '2540,2570p' _bk_exp.py | cut -c1-140
