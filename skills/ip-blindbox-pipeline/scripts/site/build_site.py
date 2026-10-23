# -*- coding: utf-8 -*-
"""
把 Blender 渲染图拼成可开盒的盲盒网页。

用法：python build_site.py <项目文件夹>
需要：pip install pillow numpy
读取：<项目>/config.json
      <项目>/渲染/单盒转盘/frame_*.png          （② 盒子转盘的输出）
      <项目>/渲染/公仔转盘/<模型名>/正面.png、f_*.png  （③ 公仔转盘的输出）
输出：<项目>/网页/index.html + <项目>/网页/figs/*.webp（两者放在一起，双击 index.html 就能玩）
"""
import base64, glob, io, json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))


def uri(im, q):
    b = io.BytesIO(); im.save(b, 'WEBP', quality=q, method=5)
    return 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode()


def alpha_bbox(paths, thr=20):
    x0 = y0 = 10 ** 9; x1 = y1 = 0
    for p in paths:
        a = np.asarray(Image.open(p).convert('RGBA'))[..., 3]
        ys, xs = np.nonzero(a > thr)
        if len(xs):
            x0, x1, y0, y1 = min(x0, xs.min()), max(x1, xs.max()), min(y0, ys.min()), max(y1, ys.max())
    return x0, y0, x1, y1


def box_frames(proj):
    fs = sorted(glob.glob(os.path.join(proj, '渲染', '单盒转盘', 'frame_*.png')))
    if not fs:
        sys.exit('找不到盒子转盘图：渲染/单盒转盘/frame_*.png（先用 Blender 跑 ② 盒子转盘）')
    x0, y0, x1, y1 = alpha_bbox(fs[::max(1, len(fs) // 12)])
    w, h = x1 - x0, y1 - y0
    W = int(max(w * 1.12, h * 1.12 * 4 / 5)); H = int(W * 5 / 4)       # 4:5 画框，盒子居中、底部留一点影子
    cx = (x0 + x1) / 2; L = int(cx - W / 2); T = int(y1 + h * 0.06 - H)
    OW, OH = 960, 1200
    yy, xx = np.mgrid[0:OH, 0:OW]
    fade = np.clip(np.minimum.reduce([xx, OW - 1 - xx, yy, OH - 1 - yy]) / (OW * 0.08), 0, 1)
    out = []
    for p in fs:
        im = Image.open(p).convert('RGBA')
        c = Image.new('RGBA', (W, H)); c.paste(im, (-L, -T), im)
        a = np.asarray(c.resize((OW, OH), Image.LANCZOS)).astype(float); a[..., 3] *= fade
        out.append(uri(Image.fromarray(a.astype('uint8'), 'RGBA'), 86))
    print('盒子转盘：', len(out), '帧')
    return out


def place(im, s, ax, y0, C):
    w, h = int(im.width * s), int(im.height * s)
    im2 = im.resize((w, h), Image.LANCZOS)
    out = Image.new('RGBA', (C, C)); out.paste(im2, (int(C / 2 - ax * s), int(28 / 800 * C - y0 * s)), im2)
    return out


def figure(proj, model, key, figs_dir, sprite=True):
    d = os.path.join(proj, '渲染', '公仔转盘', model)
    front = os.path.join(d, '正面.png')
    fr = sorted(glob.glob(os.path.join(d, 'f_*.png')))
    if not os.path.exists(front):
        sys.exit('找不到 ' + front + '（先用 Blender 跑 ③ 公仔转盘，ONLY 填 "' + model + '"）')
    ref = fr[0] if fr else front
    a = np.asarray(Image.open(ref).convert('RGBA'))[..., 3]
    ys, xs = np.nonzero(a > 140); y0, y1 = ys.min(), ys.max()
    if fr:
        cs = []
        for p in fr:
            aa = np.asarray(Image.open(p).convert('RGBA'))[..., 3]; _, xx = np.nonzero(aa > 140); cs.append((xx.min() + xx.max()) / 2)
        ax = float(np.mean(cs))          # 转轴 = 各帧中心的平均
    else:
        ax = (xs.min() + xs.max()) / 2
    s800 = (792 - 28) / (y1 - y0) / 800
    static = uri(place(Image.open(front).convert('RGBA'), s800 * 800, ax, y0, 800), 88)
    spr = None
    if sprite and fr:
        C = 560; rows = (len(fr) + 5) // 6
        sheet = Image.new('RGBA', (6 * C, rows * C))
        for i, p in enumerate(fr):
            sheet.paste(place(Image.open(p).convert('RGBA'), s800 * C, ax, y0, C), ((i % 6) * C, (i // 6) * C))
        os.makedirs(figs_dir, exist_ok=True)
        sheet.save(os.path.join(figs_dir, key + '.webp'), 'WEBP', quality=80, method=5)
        spr = {'url': 'figs/' + key + '.webp', 'n': len(fr)}
    print('公仔：', model, f'（转盘 {len(fr)} 帧）' if fr else '（只有正面图，不能转）')
    return static, spr


def icon(proj, model, S=64):
    """网站图标：第一款公仔正面图的头部，裁成正方形缩到 64px PNG。"""
    im = Image.open(os.path.join(proj, '渲染', '公仔转盘', model, '正面.png')).convert('RGBA')
    a = np.asarray(im)[..., 3]
    ys, _ = np.nonzero(a > 140); y0, y1 = ys.min(), ys.max()
    side = int((y1 - y0) * 0.48)                      # 头部大约占身高的四成，多留一点边
    _, xs = np.nonzero(a[y0:y0 + side] > 140); cx = (xs.min() + xs.max()) / 2
    head = im.crop((int(cx - side / 2), max(0, y0 - side // 20), int(cx + side / 2), max(0, y0 - side // 20) + side))
    b = io.BytesIO(); head.resize((S, S), Image.LANCZOS).save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def main():
    if len(sys.argv) < 2:
        sys.exit('用法：python build_site.py <项目文件夹>')
    proj = os.path.abspath(sys.argv[1])
    cfg = json.load(open(os.path.join(proj, 'config.json'), encoding='utf-8'))
    out_dir = os.path.join(proj, '网页'); figs_dir = os.path.join(out_dir, 'figs')
    imgs, sprites = {}, {}
    for i, f in enumerate(cfg['figures']):
        f.setdefault('key', 'f%02d' % (i + 1))
        imgs[f['key']], sp = figure(proj, f['model'], f['key'], figs_dir)
        if sp: sprites[f['key']] = sp
    hero, _ = figure(proj, cfg['egg']['model'], 'egg', figs_dir, sprite=False)
    frames = box_frames(proj)
    rate = cfg.get('hiddenRate', '1/12'); num, den = (float(x) for x in rate.split('/'))
    pub = {'id': cfg.get('id', 'blindbox'), 'figures': [{k: f[k] for k in ('key', 'name', 'desc', 'hidden') if k in f} for f in cfg['figures']],
           'egg': {'name': cfg['egg']['name'], 'line': cfg['egg'].get('line', cfg['egg']['name'] + ' 登场！')},
           'hiddenRate': num / den, 'hiddenRateText': rate}
    t = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    title = cfg['title']; hl = cfg.get('titleHighlight', '')
    rep = {'__TITLE_HTML__': title.replace(hl, '<b>' + hl + '</b>', 1) if hl else title, '__TITLE__': title,
           '__SLOGAN__': cfg.get('slogan', ''), '__INTRO__': cfg.get('intro', ''), '__EGG_NAME__': cfg['egg']['name'],
           '__ACCENT__': cfg.get('accent', '#ffc400'), '__ICON__': icon(proj, cfg['figures'][0]['model']), '__CFG__': json.dumps(pub, ensure_ascii=False),
           '__FRAMES__': json.dumps(frames), '__IMGS__': json.dumps(imgs), '__SPRITES__': json.dumps(sprites), '__HERO__': json.dumps(hero)}
    for k, v in rep.items(): t = t.replace(k, v)
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, 'index.html'); open(p, 'w', encoding='utf-8').write(t)
    print('完成：', p, '（%d KB）' % (len(t) // 1024))


if __name__ == '__main__':
    main()
