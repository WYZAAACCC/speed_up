#!/bin/bash
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R1_REINIT_AUDIT.md
git add pipeline/ca_pf_framework/R1_ADVANCE_PARALLEL.md
git add pipeline/ca_pf_framework/_r1_reinit_band.py pipeline/ca_pf_framework/_r1_reinit_deg.py \
        pipeline/ca_pf_framework/_r1_reinit_dte.py pipeline/ca_pf_framework/_r1_reinit_iters.py \
        pipeline/ca_pf_framework/_r1_reinit_mask.py pipeline/ca_pf_framework/_r1_reinit_metric.py \
        pipeline/ca_pf_framework/_r1_reinit_mkstate.py pipeline/ca_pf_framework/_r1_reinit_posctrl.py \
        pipeline/ca_pf_framework/_r1_reinit_posctrl2.py pipeline/ca_pf_framework/_r1_reinit_traj.py \
        pipeline/ca_pf_framework/_r1_reinit_when.py
git add pipeline/ca_pf_framework/_r1_exp.py pipeline/ca_pf_framework/_r1_analyze.py \
        pipeline/ca_pf_framework/_run_r1exp.sh pipeline/ca_pf_framework/_r1_peek2.sh
for d in lath1 mid1; do
  git add -f "pipeline/ca_pf_framework/_exp/$d/series.csv" \
             "pipeline/ca_pf_framework/_exp/$d/pervar.csv" \
             "pipeline/ca_pf_framework/_exp/$d/meta.json" \
             "pipeline/ca_pf_framework/_exp/$d/run.log" 2>/dev/null
done
git add _commit_msg_r1e.txt
git -c user.name=agent -c user.email=agent@local commit -F _commit_msg_r1e.txt --quiet
echo "rc=$?"
git log --oneline -1
