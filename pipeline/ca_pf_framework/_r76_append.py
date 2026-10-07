import io
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
dst = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
src = os.path.join(HERE, '_r76_ledger_new.md')
old = io.open(dst, encoding='utf-8').read()
new = io.open(src, encoding='utf-8').read()
assert '## §87 R76' not in old, '§87 已存在，先检查'
with io.open(dst, 'a', encoding='utf-8') as f:
    f.write(new)
after = io.open(dst, encoding='utf-8').read()
print('before lines=%d  after lines=%d  (+%d)'
      % (old.count('\n'), after.count('\n'), after.count('\n') - old.count('\n')))
for k in ('## §87 R76', '## §88 R76', '## §89 R76', '## §90 R76'):
    print('  %-14s present=%s' % (k, k in after))
