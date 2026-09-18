#!/bin/bash
# =============================================================================
# D 版（2a + 2b + 温度/取向特征）全链路 smoke test
#
#   1. 短算例跑 MOOSE         —— 需要 moose 环境
#   2. extract.py 出数据集     —— 需要 moose 环境（netCDF4）
#   3. check_tier2_data.py    —— 需要 moose 环境（import extract -> netCDF4）
#   4. 训练冒烟                —— 需要 ml 环境（torch）
#   5. 回放冒烟                —— 需要 ml 环境
#
# 【为什么必须中途切环境】实测两个环境互不包含对方：
#     moose: netCDF4 OK,  无 torch
#     ml   : torch 2.13.0, 无 netCDF4
# 上一版脚本全程只激活了一个环境，结果后三步全因缺模块而崩。
#
# 【为什么用 setsid】上一版用 `nohup ... &` 后台启动，MOOSE 在 setup 阶段
# 被 SIGHUP 打死（退出码 129，run.log 只留下 "Setting Up"）。
# 现在用 setsid --wait 让它脱离控制终端，脚本本身也由外层保持存活。
# =============================================================================
source /root/miniconda3/etc/profile.d/conda.sh

SRC=/mnt/f/speed_up/pipeline
D=/root/work/s1d_smoke
END_TIME=${END_TIME:-8e-5}          # 40 步 @ dt=2e-6
FAIL=0

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

echo "############ 0. 准备 ############"
sed 's/\r$//' "$SRC/stage1_meltpool_d.i" > in.i
sed -i "s/^  end_time = .*/  end_time = $END_TIME/" in.i
sed -i 's/file_base = stage1d$/file_base = stage1d_smoke/' in.i
grep -n "end_time\|file_base" in.i
cp "$SRC/columnar_seeds.csv" .
for f in extract.py feat_spec.py gen_aniso.py check_tier2_data.py \
         train_rollout_batched.py replay_transfer.py; do
  sed 's/\r$//' "$SRC/$f" > "$f"
done

# ---------------------------------------------------------------------------
echo
echo "############ 1. MOOSE 短算例（end_time=$END_TIME）############"
conda activate moose
START=$(date +%s)
setsid --wait /root/moose/modules/phase_field/phase_field-opt -i in.i > run.log 2>&1
RC=$?
echo "退出码 $RC，耗时 $(( $(date +%s) - START )) s"
grep -a "Finished Setting Up" run.log
printf "  收敛步数: "; grep -ac "Solve Converged" run.log
if [ $RC -ne 0 ] || ! grep -aq "Solve Converged" run.log; then
  echo "**MOOSE 失败**，run.log 尾部："
  tail -15 run.log
  FAIL=1
fi
echo "末行状态："
tail -2 in_out.csv 2>/dev/null | cut -c1-130

# ---------------------------------------------------------------------------
echo
echo "############ 2. extract.py ############"
if [ -s stage1d_smoke.e ]; then
  python3 extract.py stage1d_smoke.e --out ./ds_smoke --stride 1 2>&1 | tail -22
else
  echo "**没有 Exodus 输出，跳过**"; FAIL=1
fi
if [ -s ./ds_smoke/faces.csv ]; then
  echo "第二档列样例（表头尾部）："
  head -1 ./ds_smoke/faces.csv | rev | cut -c1-95 | rev
  echo "第二档列样例（首行尾部）："
  sed -n 2p ./ds_smoke/faces.csv | rev | cut -c1-95 | rev
else
  echo "**数据集为空**"; FAIL=1
fi

# ---------------------------------------------------------------------------
echo
echo "############ 3. 第二档数据核验 ############"
if [ -s ./ds_smoke/faces.csv ]; then
  python3 check_tier2_data.py ./ds_smoke || FAIL=1
else
  echo "（无数据，跳过）"
fi

# ---------------------------------------------------------------------------
# 后面两步要 torch，切到 ml 环境
echo
echo "############ 4. 训练冒烟（ml 环境）############"
conda activate ml
if [ -s ./ds_smoke/faces.csv ]; then
  python3 train_rollout_batched.py ./ds_smoke --epochs 6 --W 16 --K 8 \
      --out ./smoke.pt 2>&1 | tail -24 || FAIL=1
  [ -s ./smoke.pt ] || { echo "**没有产出模型**"; FAIL=1; }
else
  echo "（无数据，跳过）"; FAIL=1
fi

# ---------------------------------------------------------------------------
echo
echo "############ 5. 回放冒烟 ############"
if [ -s ./smoke.pt ]; then
  # 注意：replay_transfer.py 收**位置参数** (ds_dir model)，不是 --ckpt
  python3 replay_transfer.py ./ds_smoke ./smoke.pt 2>&1 | tail -22 || FAIL=1
else
  echo "（无模型，跳过）"; FAIL=1
fi

# ---------------------------------------------------------------------------
echo
echo "############ 汇总 ############"
if [ $FAIL -eq 0 ]; then echo "全链路 smoke test 通过"; else echo "**有步骤失败，见上面标记**"; fi
exit $FAIL
