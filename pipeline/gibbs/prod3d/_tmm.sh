#!/bin/bash
set +u
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work || exit 1
rm -rf mminmax; mkdir -p mminmax; cd mminmax
sed "s/\r$//" /mnt/f/speed_up/pipeline/gibbs/prod3d/_test_minmax.i > case.i
echo "m_min = min(1,2c)+c^2 ; m_max = max(c,0.5)+c^2 ; m_if = if(c<0.5,2c,1)+c^2"
echo "??: c<0.5 ? min=2c => dmin/dc=2 ; max=0.5 => dmax/dc=0 ; if ? 2c => dif/dc=2"
echo "      c>=0.5 ? min=1 => 0 ; max=c => 1 ; if ? 1 => 0"
echo "      ??: ? c^2 ?? 2c"
for v in 0.1 0.5 1.0; do
  /root/projects/gibbs/gibbs-opt -i case.i ICs/c_ic/value=$v Outputs/file_base=o > lg.txt 2>&1
  echo "--- c = $v"
  head -1 o.csv
  tail -1 o.csv
  grep -m1 -E "\*\*\* ERROR" lg.txt
done
