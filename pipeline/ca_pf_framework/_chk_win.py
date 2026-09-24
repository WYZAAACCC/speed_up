import numpy as np, os
H = "/mnt/f/speed_up/pipeline/ca_pf_framework"
d = np.load(os.path.join(H, "meltpool_growth_gid.npz"))
snaps = d["snaps"]; ts = d["snap_t"]; dx = float(d["dx"])
nx, ny, nz = snaps[0].shape
print("模型域(全网格) = %dx%dx%d 胞 = %.0f x %.0f x %.0f um" % (
    nx, ny, nz, nx*dx*1e6, ny*dx*1e6, nz*dx*1e6))
print("")
print("每帧的【滑动窗口】(= 前沿包围盒 + 2 胞 margin, 与 active_box() 同定义):")
for k in range(len(snaps)):
    g = snaps[k]
    solid = g > 0; liquid = ~solid
    if not solid.any():
        continue
    nb = np.zeros_like(solid)
    for ax in range(3):
        for s in (+1, -1):
            a = [slice(None)]*3; b = [slice(None)]*3
            a[ax] = slice(None, -1) if s > 0 else slice(1, None)
            b[ax] = slice(1, None) if s > 0 else slice(None, -1)
            nb[tuple(a)] |= liquid[tuple(b)]
    front = solid & nb
    if not front.any():
        print("  t=%.2e  无前沿(全固相) -> active_box 退化为全域" % ts[k]); continue
    idx = np.where(front)
    ex = [(idx[0].max()-idx[0].min()+1+4), (idx[1].max()-idx[1].min()+1+4), (idx[2].max()-idx[2].min()+1+4)]
    print("  t=%.2e s  前沿胞=%6d  窗口=%3dx%3dx%3d 胞 = %5.0f x %5.0f x %5.0f um   占全域 %4.1f%%" % (
        ts[k], int(front.sum()), ex[0], ex[1], ex[2], ex[0]*dx*1e6, ex[1]*dx*1e6, ex[2]*dx*1e6,
        100.0*ex[0]*ex[1]*ex[2]/(nx*ny*nz)))