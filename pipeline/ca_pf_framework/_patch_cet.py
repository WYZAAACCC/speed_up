import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
s = io.open(P, encoding="utf-8").read()
old = '''    def nucleate_bulk(self, T, dT_mean, dT_sigma, N_max, dt):
        """体形核（CET）：连续形核谱 dN/ddT = Gaussian，中心 dT_mean，总密度 N_max [1/m3]。"""
        from scipy.special import erf as _erf
        dT = np.clip(T_LIQ - T, 0.0, None)'''
new = '''    def nucleate_bulk(self, T, dT_mean, dT_sigma, N_max, dt, c_l=None, m_L=None):
        """体形核（CET）：连续形核谱 dN/ddT = Gaussian，中心 dT_mean，总密度 N_max [1/m3]。

        【2026-09-23 物理修法】驱动量可切到【成分过冷】(MATH_FRAMEWORK §4.2(b) 的判据
        \"成分过冷 ΔT_CS > ΔT_n\")：
            给了 c_l 与 m_L 时，用【局部液相线】T_L = T_LIQ + m_L (c_l - c_0)，
            驱动量 dT = clip(T_L - T, 0, inf)。
        ⇒ 这样在【热前沿之前】被溶质富集的液体里也会形核 —— 这才是 LPBF 里
          等轴晶/细晶带（CET）的物理来源；纯热过冷版本只能在热前沿【之后】形核，
          等于把 CET 退化掉了。
        """
        from scipy.special import erf as _erf
        if c_l is not None and m_L is not None:
            T_L = T_LIQ + m_L * (np.asarray(c_l) - C0_V)     # 局部液相线（线性化）
            dT = np.clip(T_L - T, 0.0, None)
        else:
            dT = np.clip(T_LIQ - T, 0.0, None)'''
assert old in s, "nucleate_bulk anchor"
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched nucleate_bulk -> constitutional option")