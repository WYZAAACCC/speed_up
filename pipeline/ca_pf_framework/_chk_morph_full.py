#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_morph_full.py --- 生产末态组织的**多维度几何/特征测定 + 文献比对**。

用法：python3 _chk_morph_full.py results_boxB_mob_beta350_final.npz

维度：
  M1  变体分数与存活数            vs 文献：沉积态常见少数变体主导
  M2  连通性（块数 / 主块占比）     vs 一个变体畴应为一整块
  M3  界面密度 S_v -> 板片厚 t     vs 板条宽 0.25-0.9 um（另一套 0.1-2）
  M4  变体畴长径比                vs 板条 10-30（集束/群 1-3）
  M5  界面配对矩阵（自协调富集）    vs 相容对应占优
  M6p **变体-母相界面法向 vs 惯习面** vs {334}_beta 型 => 夹角应 << 随机
  M6c 变体-变体界面法向 vs 相容法向  vs 同上
  M7  界面法向分布的**取向集中度**   vs 刻面 => 强集中
  M8  同变体内的**板条平行度**      vs 板条平行堆叠
  M9  板条间距（沿法向的自相关）    vs 文献 ~1 um
  M10 惯习面是否属 {334} 家族      vs {334}_beta
"""
import json
import sys
import numpy as np
from scipy import ndimage as ndi

d = np.load(sys.argv[1] if len(sys.argv) > 1 else 'results_boxB_mob_beta350_final.npz')
reg = d['reg']
N = int(d['N']); dx = float(d['dx']); L = N * dx; V = L ** 3
f = float(d['f'])
ncmp = d['ncmp'] if 'ncmp' in d.files else None
npref = d['npref'] if 'npref' in d.files else None
nv = 12
print('=== 末态组织多维测定 ===  N=%d dx=%.3f um L=%.1f um f=%.4f' % (N, dx * 1e6, L * 1e6, f))
out = dict(N=N, dx=dx, f=f)

rng = np.random.default_rng(0)
ns = rng.normal(size=(2000, 3)); ns /= np.linalg.norm(ns, axis=1)[:, None]

cnt = np.bincount(reg.ravel(), minlength=nv + 1).astype(float)
alive = [v for v in range(1, nv + 1) if cnt[v] > 0]
# ---- M1 ----
print('\n[M1] 变体分数（占全盒）+ 存活数')
for v in alive:
    print('     V%-2d %.4f' % (v, cnt[v] / N ** 3))
print('     母相 %.4f ; 存活 %d/12' % (cnt[0] / N ** 3, len(alive)))
print('     文献：沉积态常见 1-5 个变体主导【未核实·需检索】')
out['M1_alive'] = len(alive)
out['M1_frac'] = {('V%d' % v): float(cnt[v] / N ** 3) for v in alive}

# ---- M2 连通性 ----
print('\n[M2] 连通性（26 邻域）')
tot_blk, main_share = 0, []
for v in alive:
    lab, nb = ndi.label(reg == v, structure=np.ones((3, 3, 3)))
    sz = np.bincount(lab.ravel())[1:]
    big = int(sz.max()); tot = int(sz.sum())
    tot_blk += int(nb); main_share.append(big / max(tot, 1))
    if nb > 1:
        print('     V%-2d 块数=%3d 主块=%d/%d (%.4f) >20胞块=%d'
              % (v, nb, big, tot, big / max(tot, 1), int((sz > 20).sum())))
print('     总块数 %d ; 主块占比中位 %.4f' % (tot_blk, np.median(main_share)))
out['M2_total_blocks'] = tot_blk
out['M2_main_share_med'] = float(np.median(main_share))

# ---- M3 界面密度 ----
bonds = 0
for ax in range(3):
    bonds += int((reg != np.roll(reg, -1, axis=ax)).sum())
Sv = bonds * dx ** 2 / V
print('\n[M3] S_v(格点键) = %.4e 1/m => 板片厚 t=2f/S_v = %.3f um' % (Sv, 2 * f / Sv * 1e6))
print('     文献：板条宽 0.25-0.9 um（另一套 0.1-2）；片层间距 ~1 um')
out['M3_Sv'] = Sv; out['M3_t_plate'] = 2 * f / Sv

# ---- M4 长径比 ----
X, Y, Z = np.meshgrid(*(np.arange(N) for _ in range(3)), indexing='ij')
print('\n[M4] 变体畴惯性张量半轴比（长:短）')
m4 = {}
for v in alive:
    m = (reg == v); n = int(m.sum())
    if n < 50:
        continue
    p = np.stack([X[m], Y[m], Z[m]], 1).astype(float); p -= p.mean(0)
    ev = np.sort(np.clip(np.linalg.eigvalsh(np.cov(p.T)), 1e-30, None))[::-1]
    m4[v] = (ev[0] / ev[2]) ** .5
    print('     V%-2d 长:中:短 = 1 : %.2f : %.2f => 长:短 %.1f'
          % (v, (ev[1] / ev[0]) ** .5, (ev[2] / ev[0]) ** .5, m4[v]))
print('     文献：板条 10-30；集束/群 1-3')
out['M4'] = m4
out['M4_med'] = float(np.median(list(m4.values()))) if m4 else float('nan')

# ---- M5 配对 ----
pair = {}
for ax in range(3):
    a, b = reg, np.roll(reg, -1, axis=ax)
    sel = (a != b); ka, kb = a[sel], b[sel]
    for x, y in zip(ka.ravel(), kb.ravel()):
        if x == 0 or y == 0:
            continue
        kk = (min(x, y), max(x, y)); pair[kk] = pair.get(kk, 0) + 1
tot = sum(pair.values()) or 1
print('\n[M5] 界面配对（变体-变体）top-6')
for kk, vv in sorted(pair.items(), key=lambda t: -t[1])[:6]:
    print('     V%d-V%-2d %6.2f%%' % (kk[0], kk[1], 100 * vv / tot))
out['M5_top'] = {'%d-%d' % kk: float(vv / tot)
                 for kk, vv in sorted(pair.items(), key=lambda t: -t[1])[:6]}

# ---- M6p 变体-母相界面法向 vs 惯习面 ----
print('\n[M6p] **变体-母相界面法向 vs npref[k]（惯习面）**')
par = ndi.binary_dilation(reg == 0, iterations=2)
angs, rnds = [], []
for v in alive:
    if cnt[v] < 200 or npref is None:
        continue
    chi = ndi.gaussian_filter((reg == v).astype(float), 1.5)
    gr = np.array(np.gradient(chi, dx))
    bnd = (chi > 0.2) & (chi < 0.8) & par
    nn = np.moveaxis(gr, 0, -1)[bnd]
    nrm = np.linalg.norm(nn, axis=1)
    nn = nn[nrm > 1e-30] / nrm[nrm > 1e-30][:, None]
    if nn.shape[0] == 0:
        continue
    ndv = npref[v - 1]
    angs.append(np.degrees(np.arccos(np.clip(np.abs(nn @ ndv), 0, 1))))
    rnds.append(np.degrees(np.arccos(np.clip(np.abs(ns @ ndv), 0, 1))))
# ★ 记账（板条级 RVE 诊断暴露）：M6p 的**中位数**在"宽面占比 < 50%"时会被非宽面
#   （侧面/棱）拉高，不是好指标。主判据用 **宽面占比** M6q = P(|n.npref| > 0.8)
#   （随机各向同性给 0.200）。
ALLN = []
for v in alive:
    if cnt[v] < 200 or npref is None:
        continue
    chi = ndi.gaussian_filter((reg == v).astype(float), 1.5)
    gr = np.array(np.gradient(chi, dx))
    bnd = (chi > 0.2) & (chi < 0.8) & par
    nn = np.moveaxis(gr, 0, -1)[bnd]
    nrm = np.linalg.norm(nn, axis=1)
    nn = nn[nrm > 1e-30] / nrm[nrm > 1e-30][:, None]
    if nn.shape[0]:
        ALLN.append(np.abs(nn @ npref[v - 1]))
if ALLN:
    C6 = np.concatenate(ALLN)
    q = float((C6 > 0.8).mean())
    side = float((C6 < 0.3).mean())
    print('[M6q] 主判据 宽面占比 P(|n.npref|>0.8) = %.3f (随机 0.200) ; 侧面 P(<0.3) = %.3f' % (q, side))
    out['M6q_wide'] = q
    out['M6q_side'] = side
if angs:
    A = np.concatenate(angs); R = np.concatenate(rnds)
    print('     中位 %.1f deg (随机 %.1f)  p25 %.1f  n=%d' %
          (np.median(A), np.median(R), np.percentile(A, 25), A.size))
    print('     文献：板条/孪晶界面沿 {334}_beta 型惯习面 => 应显著小于随机')
    out['M6p_med'] = float(np.median(A)); out['M6p_rnd'] = float(np.median(R))
    out['M6p_p25'] = float(np.percentile(A, 25))
else:
    out['M6p_med'] = float('nan')

# ---- M6c 变体-变体 ----
print('\n[M6c] 变体-变体界面法向 vs 配对相容法向')
angsc = []
for kk, vv in pair.items():
    if vv < 30 or ncmp is None:
        continue
    ncl = ncmp[kk[0], kk[1]]
    if not np.isfinite(ncl).all():
        continue
    chi = ndi.gaussian_filter((reg == kk[0]).astype(float), 1.5)
    gr = np.array(np.gradient(chi, dx))
    bnd = (chi > 0.2) & (chi < 0.8)
    nn = np.moveaxis(gr, 0, -1)[bnd]
    nrm = np.linalg.norm(nn, axis=1)
    nn = nn[nrm > 1e-30] / nrm[nrm > 1e-30][:, None]
    if nn.shape[0] == 0:
        continue
    angsc.append(np.degrees(np.arccos(np.clip(np.abs(nn @ ncl), 0, 1))))
ac = np.concatenate(angsc) if angsc else np.array([np.nan])
print('     中位 %.1f deg (随机 %.1f)  n=%d'
      % (np.median(ac), 59.8, ac.size))
out['M6c_med'] = float(np.median(ac))

# ---- M7 取向集中度 ----
print('\n[M7] 界面法向的取向集中度（所有非母相界面）')
normals = []
for v in alive:
    chi = ndi.gaussian_filter((reg == v).astype(float), 1.5)
    gr = np.array(np.gradient(chi, dx))
    bnd = (chi > 0.35) & (chi < 0.65)
    nn = np.moveaxis(gr, 0, -1)[bnd]
    nrm = np.linalg.norm(nn, axis=1)
    nn = nn[nrm > 1e-30] / nrm[nrm > 1e-30][:, None]
    if nn.shape[0]:
        normals.append(nn)
if normals:
    NM = np.concatenate(normals)
    # 取向张量 Q = <n n^T>；各向同性给 1/3；集中度高则最大特征值 -> 1
    Q = NM.T @ NM / NM.shape[0]
    ev = np.sort(np.linalg.eigvalsh(Q))[::-1]
    print('     <n n^T> 特征值 = %.3f %.3f %.3f（各向同性=0.333；集中度 %.2f）'
          % (ev[0], ev[1], ev[2], ev[0] / 0.3333))
    out['M7_eig'] = [float(x) for x in ev]
    out['M7_conc'] = float(ev[0] / 0.33333)

# ---- M8 板条平行度 ----
print('\n[M8] 同变体内法向离散度（板条平行度；越小越平行）')
par_spread = {}
for v in alive:
    if cnt[v] < 500:
        continue
    chi = ndi.gaussian_filter((reg == v).astype(float), 1.5)
    gr = np.array(np.gradient(chi, dx))
    bnd = (chi > 0.35) & (chi < 0.65)
    nn = np.moveaxis(gr, 0, -1)[bnd]
    nrm = np.linalg.norm(nn, axis=1)
    nn = nn[nrm > 1e-30] / nrm[nrm > 1e-30][:, None]
    if nn.shape[0] < 100:
        continue
    Qv = nn.T @ nn / nn.shape[0]
    ev = np.sort(np.linalg.eigvalsh(Qv))[::-1]
    par_spread[v] = float(ev[0])
    print('     V%-2d 主取向占比 %.3f' % (v, ev[0]))
out['M8'] = par_spread
if par_spread:
    print('     文献：板条在集束内平行堆叠 => 主取向占比应显著高于 1/3')

# ---- M9 板条间距 ----
print('\n[M9] 板条间距（沿主取向的界面自相关）')
out['M9'] = {}
if normals:
    NM = np.concatenate(normals)
    Q = NM.T @ NM / NM.shape[0]
    ev, evec = np.linalg.eigh(Q)
    ax = evec[:, -1]
    regf = reg.astype(float)
    # 沿主轴采样界面位置
    coords = np.stack(np.meshgrid(*(np.arange(N) for _ in range(3)), indexing='ij'), -1)
    proj = np.einsum('ijk,l->ijkl', np.ones(1), ax) if False else (coords @ ax)
    # 用变体指示场的界面位置在投影轴上的分布
    for v in alive:
        if cnt[v] < 500:
            continue
        chi = ndi.gaussian_filter((reg == v).astype(float), 1.5)
        gr = np.array(np.gradient(chi, dx))
        bnd = (chi > 0.4) & (chi < 0.6)
        if bnd.sum() < 50:
            continue
        pj = (coords @ ax)[bnd]
        h, e = np.histogram(pj, bins=80)
        cent = 0.5 * (e[:-1] + e[1:])
        hm = h - h.mean()
        ac = np.correlate(hm, hm, 'full')[len(hm) - 1:]
        ac /= max(ac[0], 1e-30)
        pk = int(np.argmax(ac[3:])) + 3
        spacing = 2 * np.abs(cent[pk]) if pk < len(cent) else float('nan')
        out['M9']['V%d' % v] = float(spacing)
        break
print('     V%d 主取向间距 ~ %.3f um' % (alive[0], out['M9'].get('V%d' % alive[0], float('nan'))))
print('     文献：板条间距 ~1 um')

# ---- M10 {334} 家族 ----
print('\n[M10] 惯习面是否属 {334}_beta 家族')
c334 = np.array([[3, 3, 4], [3, 3, -4], [3, -3, 4], [-3, 3, 4],
                 [3, 4, 3], [3, 4, -3], [4, 3, 3], [4, -3, 3],
                 [3, -4, 3], [4, 3, -3], [-3, 4, 3], [4, -3, -3]], float)
c334 /= np.linalg.norm(c334, axis=1)[:, None]
if angs:
    A = np.concatenate(angs)
    # 用每个变体的 npref 反查它与 {334} 家族的夹角
    for v in alive:
        if npref is None:
            break
        c = np.abs(c334 @ npref[v - 1])
        print('     V%-2d npref 与 {334} 家族最小夹角 %.1f deg' %
              (v, np.degrees(np.arccos(np.clip(c.max(), 0, 1)))))
    print('     文献：alpha\' 惯习面常报 {334}_beta / {344}_beta 型【未核实】')
json.dump(out, open(sys.argv[1].replace('_final.npz', '') + '_morph.json', 'w'), indent=1)
print('\n已存 %s_morph.json' % sys.argv[1].replace('_final.npz', ''))
