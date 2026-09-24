# -*- coding: utf-8 -*-
import io, sys
B = '/root/bench/ExaCA-master/src/'
# 1) 解析时不缩放（保存物理 V）
p = B + 'CAinputs.hpp'; s = io.open(p, encoding='utf-8').read()
old = """            const double scale = domain.deltat / domain.deltax;   // m/s -> cells/step
            auto hx = Kokkos::View<float *, Kokkos::HostSpace>("tabx_h", xs.size());
            auto hv = Kokkos::View<float *, Kokkos::HostSpace>("tabv_h", vs.size());
            for (size_t i = 0; i < xs.size(); i++) {
                hx(i) = xs[i];
                hv(i) = vs[i] * static_cast<float>(scale);
            }"""
new = """            // 注意：这里【不】缩放。parseIRF 在 domain.deltat/deltax 赋值之前被调用
            // （CAinputs.hpp: parseIRF=63, domain.deltat=110），缩放放到 normalize() 里做。
            auto hx = Kokkos::View<float *, Kokkos::HostSpace>("tabx_h", xs.size());
            auto hv = Kokkos::View<float *, Kokkos::HostSpace>("tabv_h", vs.size());
            for (size_t i = 0; i < xs.size(); i++) {
                hx(i) = xs[i];
                hv(i) = vs[i];
            }"""
if old not in s: print('!! CAinputs 锚点'); sys.exit(1)
io.open(p, 'w', encoding='utf-8').write(s.replace(old, new)); print('CAinputs 已改')

# 2) normalize 里做 dt/dx 归一
p = B + 'CAinterfacialresponse.hpp'; s = io.open(p, encoding='utf-8').read()
old = """        else if (_inputs.function[phase_num] == _inputs.exponential) {
            // Normalize only the leading and last coefficient: V = A*e^(Bx) + C
            _inputs.A[phase_num] *= static_cast<float>(deltat / deltax);
            _inputs.C[phase_num] *= static_cast<float>(deltat / deltax);
        }"""
new = """        else if (_inputs.function[phase_num] == _inputs.exponential) {
            // Normalize only the leading and last coefficient: V = A*e^(Bx) + C
            _inputs.A[phase_num] *= static_cast<float>(deltat / deltax);
            _inputs.C[phase_num] *= static_cast<float>(deltat / deltax);
        }
        else if (_inputs.function[phase_num] == _inputs.table) {
            // 查表式：表里是物理 V[m/s]，这里按 dt/dx 归一成 胞/步
            const float sc = static_cast<float>(deltat / deltax);
            auto hv = _inputs.tab_v[phase_num];
            auto hv_host = Kokkos::create_mirror_view(hv);
            Kokkos::deep_copy(hv_host, hv);
            for (int i = 0; i < static_cast<int>(hv_host.extent(0)); i++)
                hv_host(i) *= sc;
            Kokkos::deep_copy(hv, hv_host);
        }"""
if old not in s: print('!! normalize 锚点'); sys.exit(1)
io.open(p, 'w', encoding='utf-8').write(s.replace(old, new)); print('normalize 已改')