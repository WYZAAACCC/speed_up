import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
s = io.open(P, encoding="utf-8").read()
old = """        self.fs = np.zeros(self.shape)              # 亚网格固相分数
        self.c_sol = np.full(self.shape, C0_V)      # 固相成分
        self.A_liq = np.full(self.shape, C0_V)      # (1-fs)*c_L（主守恒量）
        self.c_liq = np.full(self.shape, C0_V)      # 局部液相成分（Window C 输入）
        self.cl = np.full(self.shape, C0_V)
        self.c_cell = np.full(self.shape, C0_V)     # 体平均成分（质量守恒）"""
new = """        _shp = (nx, ny, nz)
        self.fs = np.zeros(_shp)                    # 亚网格固相分数
        self.c_sol = np.full(_shp, C0_V)            # 固相成分
        self.A_liq = np.full(_shp, C0_V)            # (1-fs)*c_L（主守恒量）
        self.c_liq = np.full(_shp, C0_V)            # 局部液相成分（Window C 输入）
        self.cl = np.full(_shp, C0_V)
        self.c_cell = np.full(_shp, C0_V)           # 体平均成分（质量守恒）"""
if old not in s:
    print("!! 未找到"); raise SystemExit(1)
io.open(P, "w", encoding="utf-8").write(s.replace(old, new))
print("fixed")