#!/bin/bash
I=/root/work/s1d_w/stage1_meltpool_d.i     # 最新生成的 D 版
[ -f "$I" ] || I=/mnt/f/speed_up/pipeline/stage1_meltpool_d.i
echo "审查文件: $I"
echo
echo "############ 1. 2b 相关的 Functions（梯度解析式）############"
sed -n '/\[gradTx_fn\]/,/^  \[\]/p' "$I"
sed -n '/\[gradTy_fn\]/,/^  \[\]/p' "$I"
echo
echo "############ 2. 温度场本身（做对比）############"
sed -n '/\[laser_T\]/,/^  \[\]/p' "$I"
echo
echo "############ 3. grad_Tx / grad_Ty 的 AuxVariable 声明 ############"
awk '/^\[AuxVariables\]/,/^\[\]/' "$I" | grep -A4 -E '\[grad_Tx\]|\[grad_Ty\]'
echo
echo "############ 4. grad_Tx / grad_Ty 的 AuxKernel ############"
awk '/^\[AuxKernels\]/,/^\[\]/' "$I" | grep -B1 -A6 -E 'type = FunctionAux'
echo
echo "############ 5. align4_prop / L2b / L2a / L_aniso 四个材料 ############"
for b in align4_prop L2b L2a L_aniso; do
  echo "--- $b ---"
  sed -n "/  \[$b\]/,/^  \[\]/p" "$I" | cut -c1-200
  echo
done
