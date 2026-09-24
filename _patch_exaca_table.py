# -*- coding: utf-8 -*-
'''_patch_exaca_table.py --- 给 ExaCA 增加 "table" 形式界面响应（读 CSV: dT[K], V[m/s]）'''
import io, sys
B = '/root/bench/ExaCA-master/src/'
def edit(fn, pairs):
    p = B + fn
    s = io.open(p, encoding='utf-8').read()
    for old, new, tag in pairs:
        if old not in s:
            print('!! %s: 未找到 %s' % (fn, tag)); sys.exit(1)
        if s.count(old) != 1:
            print('!! %s: %s 不唯一(%d)' % (fn, tag, s.count(old))); sys.exit(1)
        s = s.replace(old, new)
        print('   %s: %s OK' % (fn, tag))
    io.open(p, 'w', encoding='utf-8').write(s)

# ---- 1) CAinputdata.hpp: enum + 表视图 ----
edit('CAinputdata.hpp', [(
'''    enum IRFtypes {
        cubic = 0,
        quadratic = 1,
        power = 2,
        exponential = 3,
    };''',
'''    enum IRFtypes {
        cubic = 0,
        quadratic = 1,
        power = 2,
        exponential = 3,
        table = 4,     // 2026-09-24 本机新增：查表式界面响应（dT[K], V[m/s]）
    };
    // 查表数据（每相一份）；表里的 V 在解析时已乘 dt/dx 归一为 "胞/步"
    Kokkos::View<float *> tab_x[2];
    Kokkos::View<float *> tab_v[2];''', 'enum+views')])

# ---- 2) CAinputs.hpp: 解析 table 形式 ----
edit('CAinputs.hpp', [(
'''        irf.A[phase_num] = irf_phase_data["coefficients"]["A"];
        irf.B[phase_num] = irf_phase_data["coefficients"]["B"];
        irf.C[phase_num] = irf_phase_data["coefficients"]["C"];
        std::string functionform = irf_phase_data["function"];''',
'''        std::string functionform = irf_phase_data["function"];
        if (functionform == "table") {
            // ---- 新增：查表式界面响应。材料文件给 "table_file": "<csv 路径>"，CSV 两列 dT[K],V[m/s] ----
            std::string tabfile = irf_phase_data["table_file"];
            std::ifstream tf(tabfile);
            if (!tf.is_open())
                throw std::runtime_error("Error: cannot open IRF table file " + tabfile);
            std::vector<float> xs, vs;
            std::string line;
            while (std::getline(tf, line)) {
                if (line.empty() || line[0] == '#')
                    continue;
                std::replace(line.begin(), line.end(), ',', ' ');
                std::istringstream iss(line);
                float a, b;
                if (!(iss >> a >> b))
                    continue;
                xs.push_back(a);
                vs.push_back(b);
            }
            if (xs.size() < 2)
                throw std::runtime_error("Error: IRF table needs at least 2 rows");
            const double scale = domain.deltat / domain.deltax;   // m/s -> cells/step
            auto hx = Kokkos::View<float *, Kokkos::HostSpace>("tabx_h", xs.size());
            auto hv = Kokkos::View<float *, Kokkos::HostSpace>("tabv_h", vs.size());
            for (size_t i = 0; i < xs.size(); i++) {
                hx(i) = xs[i];
                hv(i) = vs[i] * static_cast<float>(scale);
            }
            irf.tab_x[phase_num] = Kokkos::create_mirror_view_and_copy(Kokkos::DefaultExecutionSpace(), hx);
            irf.tab_v[phase_num] = Kokkos::create_mirror_view_and_copy(Kokkos::DefaultExecutionSpace(), hv);
            irf.function[phase_num] = irf.table;
            irf.freezing_range[phase_num] = irf_phase_data["freezing_range"];
            if (irf_phase_data.contains("velocity_cap"))
                irf.velocity_cap[phase_num] = irf_phase_data["velocity_cap"];
            return;
        }
        irf.A[phase_num] = irf_phase_data["coefficients"]["A"];
        irf.B[phase_num] = irf_phase_data["coefficients"]["B"];
        irf.C[phase_num] = irf_phase_data["coefficients"]["C"];''', 'parse table')])

# ---- 3) CAinterfacialresponse.hpp: normalize 跳过 + compute 插值 ----
edit('CAinterfacialresponse.hpp', [(
'''    float compute(const float loc_u_uncapped, const int phase_num = 0) const {
        float V;
        float loc_u;''',
'''    float compute(const float loc_u_uncapped, const int phase_num = 0) const {
        float V;
        float loc_u;
        // 新增：查表式（V 已在解析时按 dt/dx 归一）
        if (_inputs.function[phase_num] == _inputs.table) {
            auto hx = _inputs.tab_x[phase_num];
            auto hv = _inputs.tab_v[phase_num];
            const int n = hx.extent(0);
            if (loc_u_uncapped <= hx(0))
                return Kokkos::fmax(0.0f, hv(0));
            if (loc_u_uncapped >= hx(n - 1))
                return Kokkos::fmax(0.0f, hv(n - 1));
            int i = 0;
            while (i < n - 2 && hx(i + 1) < loc_u_uncapped)
                i++;
            const float x0 = hx(i), x1 = hx(i + 1), v0 = hv(i), v1 = hv(i + 1);
            return Kokkos::fmax(0.0f, v0 + (v1 - v0) * (loc_u_uncapped - x0) / Kokkos::fmax(x1 - x0, 1e-20f));
        }''', 'compute table')])
print('三个文件已打补丁')