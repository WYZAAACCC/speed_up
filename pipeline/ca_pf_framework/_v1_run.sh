#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework
/root/miniconda3/envs/ml/bin/python _v1_patch.py
rm -rf _v1_out; mkdir -p _v1_out
# 任务清单（56 个 worker）
: > _v1_tasks.txt
for i in $(seq 0 0);  do echo "t1_octahedron:$i" >> _v1_tasks.txt; done
for i in $(seq 0 2);  do echo "t2_velocity:$i"   >> _v1_tasks.txt; done
for i in $(seq 0 3);  do echo "t3_aniso_law:$i"  >> _v1_tasks.txt; done
for i in $(seq 0 5);  do echo "t4_gb_locus:$i"   >> _v1_tasks.txt; done
for i in $(seq 0 19); do echo "t5_wc_pairs:$i"   >> _v1_tasks.txt; done
for i in $(seq 0 7);  do echo "t6_elimination:$i" >> _v1_tasks.txt; done
for i in $(seq 0 5);  do echo "t7_nucleation:$i" >> _v1_tasks.txt; done
for i in $(seq 0 7);  do echo "t8_dx_conv:$i"    >> _v1_tasks.txt; done
wc -l _v1_tasks.txt
echo "=== 启动 16 路并行 $(date +%H:%M:%S)"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  xargs -a _v1_tasks.txt -P 16 -I{} env OMP_NUM_THREADS=1 /root/miniconda3/envs/ml/bin/python _v1_worker.py {}
echo "=== 全部结束 $(date +%H:%M:%S)"
ls _v1_out | wc -l