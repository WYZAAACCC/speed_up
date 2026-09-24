import io
P = '/mnt/f/speed_up/_ti64_cell.py'
s = io.open(P, encoding='utf-8').read()
s = s.replace("def run_mine(seed, mode):", "def run_mine(seed, mode, tiebreak='ratio'):")
s = s.replace("    ca.allow_spont = False", "    ca.allow_spont = False\n    ca.cell_tiebreak = tiebreak")
s = s.replace("mine = {m: [run_mine(s, m) for s in range(20)] for m in ('cell', 'envelope')}",
              "mine = {'cell': [run_mine(s, 'cell') for s in range(20)],\n        'envelope': [run_mine(s, 'envelope') for s in range(20)],\n        'cell_fc': [run_mine(s, 'cell', 'firstcome') for s in range(20)]}")
s = s.replace("""    b = np.array([x[k] for x in mine['cell']]); c = np.array([x[k] for x in mine['envelope']])""",
              """    b = np.array([x[k] for x in mine['cell']]); c = np.array([x[k] for x in mine['envelope']])
    d = np.array([x[k] for x in mine['cell_fc']])""")
s = s.replace("""    print('%-16s %-16s %-16s %-16s %+9.1f%%  p=%.3g' % (
        nm, '%.2f' % a.mean(), '%.2f' % b.mean(), '%.2f' % c.mean(), rel, p))""",
              """    relfc = 100*(d.mean()-a.mean())/a.mean()
    print('%-14s %-12s %-12s %-12s %-12s %+8.1f%%  (firstcome %+.1f%%)' % (
        nm, '%.2f' % a.mean(), '%.2f' % b.mean(), '%.2f' % c.mean(), '%.2f' % d.mean(), rel, relfc))""")
io.open(P, 'w', encoding='utf-8').write(s)
print('_ti64_cell.py 已扩展为三档（cell / envelope / cell+firstcome）')