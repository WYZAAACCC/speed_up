import io
p = '/root/bench/ExaCA-master/src/CAinputdata.hpp'
s = io.open(p, encoding='utf-8').read()
print('--- 现有 include:'); print('\n'.join(l for l in s.split('\n')[:20] if l.startswith('#include') or l.startswith('//')))
if 'Kokkos_Core.hpp' not in s:
    # 在第一个 #include 之前插入
    i = s.index('#include')
    s = s[:i] + '#include <Kokkos_Core.hpp>\n' + s[i:]
    io.open(p, 'w', encoding='utf-8').write(s)
    print('已加入 <Kokkos_Core.hpp>')