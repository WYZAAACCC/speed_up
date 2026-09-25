cd /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose
for d in ak3_p1c_kcw_W10_A*/; do
  if [ -f "$d/p1c_ak3_out.csv" ]; then
    echo "$d 行数=$(wc -l < $d/p1c_ak3_out.csv) 末行=$(tail -1 $d/p1c_ak3_out.csv)"
  else
    echo "$d 无 csv"
  fi
done
echo "MOOSE 进程: $(ps -eo args | grep -c '[p]hase_field-opt')"