#!/bin/bash
cd /mnt/f/speed_up || exit 1
rm -f .git/index.lock
git add pipeline/ca_pf_framework/NUMERICAL_RULES.md pipeline/ca_pf_framework/_fill96.py \
        pipeline/ca_pf_framework/_t41_profile.py pipeline/ca_pf_framework/_chk_t21a.py \
        pipeline/ca_pf_framework/_patch_sigma_ext.py pipeline/ca_pf_framework/pf1d_moose/README.md \
        pipeline/ca_pf_framework/pf1d_moose/*.py pipeline/ca_pf_framework/pf1d_moose/*.sh \
        pipeline/ca_pf_framework/pf1d_moose/*.txt pipeline/ca_pf_framework/pf1d_moose/*.md \
        pipeline/ca_pf_framework/IMPLEMENTATION_PLAN.md
git commit -q -m "T1.2 判决：生产缺的是网格不是 ALPHA（dx 收敛令 ALPHA*=2.58→2.14，生产值 2 只差 7%）；补 NUMERICAL_RULES.md；T2.1a 全部 PASS" && git log --oneline -2
echo "=== dt4 status ==="
cd pipeline/ca_pf_framework/pf1d_moose
wc -l prod1d_A2_W2_kc1e-14_L150dt4/p1c_prod1d_out.csv 2>/dev/null
tail -n 3 _D_L150dt4_A2_W2e-6.log
ps -eo etime,args | grep 'phase_field-opt' | grep -v grep | wc -l