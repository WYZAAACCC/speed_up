import json
import sys
d = sys.argv[1]
m = json.load(open(d + '/meta.json'))
for k in sorted(m):
    v = m[k]
    s = repr(v)
    print('%-16s %s' % (k, s[:150]))
