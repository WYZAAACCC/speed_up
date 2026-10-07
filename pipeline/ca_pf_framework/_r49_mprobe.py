#!/usr/bin/env python3
import json
m = json.load(open('_exp/_bk_mb/dry_r49dg/meta.json'))
print('plate =', m['plate'], type(m['plate']))
print({k: m[k] for k in ('N', 'dx_nm', 'nv', 'laths') if k in m})
