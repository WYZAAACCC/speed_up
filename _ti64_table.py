import io
p = '/root/bench/ExaCA-master/src/CAinputs.hpp'
s = io.open(p, encoding='utf-8').read()
if '#include <sstream>' not in s:
    s = s.replace('#include <fstream>', '#include <algorithm>\n#include <fstream>\n#include <sstream>')
    io.open(p, 'w', encoding='utf-8').write(s)
    print('加入 <algorithm>/<sstream>')
else:
    print('已存在')
# 生成给 ExaCA 的 Ti64 两列表 + Ti64.json + 算例 JSON
import numpy as np, json
t = np.loadtxt('/mnt/f/speed_up/pipeline/ca_pf_framework/irf_ti64.csv', delimiter=',', skiprows=1)
o = np.argsort(t[:, 0])
np.savetxt('/root/bench/run/irf_ti64_table.csv', np.column_stack([t[o, 0], t[o, 1]]),
           delimiter=',', header='dT_K,V_m_per_s', comments='', fmt='%.9g')
print('表: %d 行, dT %.3f..%.3f K' % (len(t), t[o, 0].min(), t[o, 0].max()))
mat = {"function": "table", "table_file": "/root/bench/run/irf_ti64_table.csv",
       "freezing_range": float(t[o, 0].max()), "velocity_cap": True}
json.dump(mat, open('/root/bench/run/Ti64.json', 'w'), indent=1)
json.dump(mat, open('/mnt/f/speed_up/bench/exaca/Ti64.json', 'w'), indent=1)
print(json.dumps(mat))