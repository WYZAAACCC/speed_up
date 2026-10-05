#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t10PRT2_b3_1005_1213.log
[ -f "$L" ] || L=_w2_t5_short_t10B9.log
echo "=== 文件：$L （大小 $(stat -c%s "$L") B）==="
echo
echo "── ① 冷速 / 温度钟 / KM 律（生效值）──"
grep -aE "冷速|时钟起点|T_start|T_end|α_KM|alpha_KM|导出板条数|总根数|C-3|C-5" "$L" 2>/dev/null | head -14 | tr -d '\r' | cut -c1-165 | sed 's/^/  /'
echo
echo "── ② 形核开关（生效值）──"
grep -aE "nuc-shape|nuc_shape|ellipsoid|nuc-init|nuc-sites-refill|fresh-every|block-target|block-parallel|occ-guard|supercrit|periodic-seed|overlap|eng-elong|plate" "$L" 2>/dev/null | head -14 | tr -d '\r' | cut -c1-165 | sed 's/^/  /'
echo
echo "── ③ banner 里的完整参数行（前 40 行里找）──"
head -60 "$L" 2>/dev/null | tr -d '\r' | cut -c1-165 | sed 's/^/  /'
echo
echo "── ④ 与 D4′ 相关：盒/网格/N ──"
grep -aE "N=|dx=|盒|µm|um " "$L" 2>/dev/null | head -8 | tr -d '\r' | cut -c1-165 | sed 's/^/  /'
