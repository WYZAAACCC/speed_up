import io, sys
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py'
s = io.open(P, encoding='utf-8').read()
# 用标量版替换 oct_recenter（保留函数名与签名）
start = s.index('    def oct_recenter(self, gvec, csrc, xnbr, crit, s3=3.0**0.5):')
end = s.index('    def grow_envelopes(self, dt, V, front):')
new = '''    def _oct_recenter_one(self, g, csrc, xnbr, crit):
        """ExaCA src/CAinterface.hpp::createNewOctahedron 的逐胞标量实现（逐行转写）"""
        Pg = self.axes[int(g)]
        s3 = 3.0 ** 0.5
        x0 = xnbr - csrc
        pos = [(Pg[:, k] @ x0) > 0.0 for k in range(3)]
        diag = [Pg[:, k] * (2.0 * (1.0 if pos[k] else 0.0) - 1.0) for k in range(3)]
        T = [csrc + crit * diag[k] for k in range(3)]
        dd = [float(np.linalg.norm(T[k] - xnbr)) for k in range(3)]
        c01 = dd[0] < dd[1]; c12 = dd[1] < dd[2]; c20 = dd[2] < dd[0]
        ti = 2 * (int(c20) - int(c12)) * int(c20) + (int(c12) - int(c01)) * int(c12)
        mind = dd[ti]; Tc = T[ti]
        T1 = T[(ti + 1) % 3]; T2 = T[(ti + 2) % 3]
        d1 = float(np.linalg.norm(Tc - T1)); d2 = float(np.linalg.norm(Tc - T2))
        j1, j1n, j2, j2n = 0.0, d1, 0.0, d2
        if mind != 0.0:
            j1 = float((xnbr - T1) @ (Tc - T1)) / max(d1, 1e-30); j1n = d1 - j1
            j2 = float((xnbr - T2) @ (Tc - T2)) / max(d2, 1e-30); j2n = d2 - j2
        l12 = 0.5 * (min(j1, s3) + min(j1n, s3))
        l13 = 0.5 * (min(j2, s3) + min(j2n, s3))
        lnew = (2.0 ** 0.5) * max(l12, l13)
        cap = Tc - csrc
        nrm = float(np.linalg.norm(cap))
        uhat = cap / nrm if nrm > 1e-30 else np.zeros(3)
        return lnew, Tc - lnew * uhat

    def oct_recenter(self, gvec, csrc, xnbr, crit, s3=3.0**0.5):
        """逐胞标量版（正确性优先；矢量优化以后再做）"""
        M = len(gvec)
        lnew = np.empty(M); cnew = np.empty((M, 3))
        for i in range(M):
            ln, cn = self._oct_recenter_one(gvec[i], np.asarray(csrc[i], float),
                                            np.asarray(xnbr[i], float), float(crit[i]))
            lnew[i] = ln; cnew[i] = cn
        return lnew, cnew

'''
s = s[:start] + new + s[end:]
io.open(P, 'w', encoding='utf-8').write(s)
print('已替换为标量版; 行数 =', s.count(chr(10)) + 1)