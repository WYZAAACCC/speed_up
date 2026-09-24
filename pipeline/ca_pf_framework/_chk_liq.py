import numpy as np, os
H = "/mnt/f/speed_up/pipeline/ca_pf_framework"
d = np.load(os.path.join(H, "meltpool_growth_gid.npz"))
s0 = d["snaps"][0]; dx = float(d["dx"])
nx, ny, nz = s0.shape
liq = (s0 == 0)
ii, jj, kk = np.where(liq)
print("液相胞 =", int(liq.sum()))
print("包围盒 (胞): x %d..%d  y %d..%d  z %d..%d" % (ii.min(), ii.max(), jj.min(), jj.max(), kk.min(), kk.max()))
cc = np.array([liq.shape[0]/2, liq.shape[1]/2, liq.shape[2]-1])
dist = np.sqrt((ii-cc[0])**2 + (jj-cc[1])**2 + (kk-cc[2])**2) * dx * 1e6
print("到(域中心,顶面)距离 um: min %.0f  中位 %.0f  p95 %.0f  max %.0f" % (
    dist.min(), np.median(dist), np.percentile(dist, 95), dist.max()))
far = dist > (np.median(dist) * 2.0)
print("远离主池的液相胞 = %d 个 (%.0f%% 的液相)" % (int(far.sum()), 100.0*far.mean()))
if far.any():
    print("  它们的: x %d..%d y %d..%d z %d..%d" % (
        ii[far].min(), ii[far].max(), jj[far].min(), jj[far].max(), kk[far].min(), kk[far].max()))
    print("  它们最近的固相邻居 gid 示例:", np.unique(s0[np.clip(ii[far],0,nx-1), np.clip(jj[far],0,ny-1), np.clip(kk[far],0,nz-1)])[:5])