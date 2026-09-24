import json, os
src = '/mnt/f/speed_up/bench/exaca/Inp_SmallDirSolidification.json'
d = json.load(open(src))
d['MaterialFileName'] = '/root/bench/run/Inconel625.json'
d['GrainOrientationFile'] = '/root/bench/run/GrainOrientationVectors.csv'
d['Printing']['PathToOutput'] = '/root/bench/run/'
d['Printing']['OutputFile'] = 'Exa_SmallDirS'
json.dump(d, open('/mnt/f/speed_up/bench/exaca/Inp_SmallDirS_abs.json', 'w'), indent=1)
# 双晶 200^3 也做一份（先不跑，备用）
src2 = '/mnt/f/speed_up/bench/exaca/Inp_TwoGrainDirSolidification.json'
d2 = json.load(open(src2))
d2['MaterialFileName'] = '/root/bench/run/Inconel625.json'
d2['GrainOrientationFile'] = '/root/bench/run/GrainOrientationVectors.csv'
d2['Printing']['PathToOutput'] = '/root/bench/run/'
d2['Printing']['OutputFile'] = 'Exa_TwoGrainDirS'
json.dump(d2, open('/mnt/f/speed_up/bench/exaca/Inp_TwoGrain_abs.json', 'w'), indent=1)
print('OK')