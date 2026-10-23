# -*- coding: utf-8 -*-
r"""
IP 盲盒 · ② 盒子 360° 转盘：透明背景，72 帧（每 5°）+ 1 张正面主图（Blender 3.6 / 4.x）
用法：Blender → 顶部「Scripting/脚本」→ 文本→打开 本文件 → 改下面 BASE → ▶ 运行脚本
输出：<项目>\渲染\单盒转盘\frame_00.png … frame_71.png
改了文件后，Blender 里要点 文本→重新载入，否则跑的还是旧代码。
"""
import bpy, bmesh, math, os
from mathutils import Vector

# ==================== 只需要改这里 ====================
BASE       = r"D:\我的盲盒项目"   # 项目文件夹，里面要有：盒面\  3D模型\  （渲染\ 会自动建）
QUICK_TEST = False                  # True = 先用小图低采样试跑几帧，看构图没问题再改回 False 正式渲染
USE_GPU    = True                   # 有独立显卡（NVIDIA/AMD/Apple）时用显卡渲染
# =====================================================
BASE = os.environ.get("BLINDBOX_BASE", BASE)
QUICK_TEST = QUICK_TEST or os.environ.get("BLINDBOX_QUICK") == "1"
FACES      = os.path.join(BASE, "盒面")
FACE_FILES = {"front": "正面.png", "back": "背面.png", "left": "左侧面.png",
              "right": "右侧面.png", "top": "顶面.png", "bottom": "底面.png"}
ASSETS     = BASE
MODELS_DIR = os.path.join(BASE, "3D模型")
OUT_DIR    = os.path.join(BASE, "渲染")
def _first_glb():
    fs = sorted(f for f in os.listdir(MODELS_DIR) if f.lower().endswith(".glb")) if os.path.isdir(MODELS_DIR) else []
    return os.path.join(MODELS_DIR, fs[0]) if fs else ""

BOX_W, BOX_D, BOX_H = 0.065, 0.065, 0.099   # 盒子尺寸（米）
ADD_SECOND_BOX = False
ADD_BAG        = False
ADD_FIGURE     = False
FIGURE_GLB     = ""
RES_X, RES_Y   = (400, 500) if QUICK_TEST else (1600, 2000)
SAMPLES        = 16 if QUICK_TEST else 160
TURNTABLE      = False
RENDER_NOW     = True

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.lights, bpy.data.cameras):
        for b in list(block):
            if b.users == 0:
                block.remove(b)

def set_in(node, names, value):
    """兼容不同 Blender 版本的 Principled BSDF 输入名"""
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return node.inputs[n]
    return None

def inp(node, name):
    for i in node.inputs:
        if i.identifier == name.replace(" ", "_") or i.name == name or i.identifier == name:
            return i
    raise KeyError(name)

def get_bsdf(m):
    """按类型找原理化BSDF节点，不受界面语言影响；找不到就新建"""
    m.use_nodes = True
    nt = m.node_tree
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    return b

def load_img(path, non_color=False):
    if not os.path.exists(path):
        raise FileNotFoundError("找不到图片：" + path)
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    return img

def mat_card(name, img_path, rough=0.58, coat=0.06):
    """印刷卡纸 + 一层薄塑封膜的反光"""
    m = bpy.data.materials.new(name); bsdf = get_bsdf(m); nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = load_img(img_path)
    tex.interpolation = 'Cubic'
    nt.links.new(tex.outputs[0], inp(bsdf,"Base Color"))
    set_in(bsdf, ["Roughness"], rough)
    set_in(bsdf, ["Coat Weight", "Clearcoat"], coat)
    set_in(bsdf, ["Coat Roughness", "Clearcoat Roughness"], 0.25)
    set_in(bsdf, ["Specular IOR Level", "Specular"], 0.25)
    # 极轻的纸纹凹凸
    noise = nt.nodes.new("ShaderNodeTexNoise"); set_in(noise, ["Scale"], 900.0); set_in(noise, ["Detail"], 6.0)
    bump = nt.nodes.new("ShaderNodeBump"); set_in(bump, ["Strength"], 0.04)
    nt.links.new(noise.outputs[0], inp(bump,"Height")); nt.links.new(bump.outputs[0], inp(bsdf,"Normal"))
    return m

def make_box(name, loc, rot_z):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    ob = bpy.context.active_object; ob.name = name
    ob.scale = (BOX_W, BOX_D, BOX_H)
    bpy.ops.object.transform_apply(scale=True)
    me = ob.data
    mats = {k: mat_card(f"{name}_{k}", os.path.join(FACES, f)) for k, f in FACE_FILES.items()}
    order = ["front", "back", "left", "right", "top", "bottom"]
    for k in order: me.materials.append(mats[k])
    uv = me.uv_layers.active or me.uv_layers.new()
    hw, hd, hh = BOX_W/2, BOX_D/2, BOX_H/2
    for p in me.polygons:
        n = p.normal
        if   n.y < -0.5: k = "front"
        elif n.y >  0.5: k = "back"
        elif n.x < -0.5: k = "left"
        elif n.x >  0.5: k = "right"
        elif n.z >  0.5: k = "top"
        else:            k = "bottom"
        p.material_index = order.index(k)
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            if   k == "front":  u, w = (v.x+hw)/BOX_W, (v.z+hh)/BOX_H
            elif k == "back":   u, w = (hw-v.x)/BOX_W, (v.z+hh)/BOX_H
            elif k == "right":  u, w = (v.y+hd)/BOX_D, (v.z+hh)/BOX_H
            elif k == "left":   u, w = (hd-v.y)/BOX_D, (v.z+hh)/BOX_H
            elif k == "top":    u, w = (v.x+hw)/BOX_W, (v.y+hd)/BOX_D
            else:               u, w = (v.x+hw)/BOX_W, (hd-v.y)/BOX_D
            uv.data[li].uv = (u, w)
    bev = ob.modifiers.new("圆角", 'BEVEL'); bev.width = 0.0011; bev.segments = 4; bev.limit_method = 'NONE'
    bpy.ops.object.shade_smooth()
    try: bpy.ops.object.shade_auto_smooth(angle=math.radians(30))
    except Exception:
        try: me.use_auto_smooth = True; me.auto_smooth_angle = math.radians(30)
        except Exception: pass
    ob.location = (loc[0], loc[1], BOX_H/2 + loc[2])
    ob.rotation_euler = (0, 0, math.radians(rot_z))
    return ob

def make_bag():
    W, H, A = 0.060, 0.090, 0.012
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=90, y_subdivisions=135, size=1, location=(0, 0, 0))
    ob = bpy.context.active_object; ob.name = "锡箔袋"
    ob.scale = (W, H, 1); bpy.ops.object.transform_apply(scale=True)
    ob.rotation_euler = (math.radians(90), 0, 0); bpy.ops.object.transform_apply(rotation=True)
    top_seal, bot_seal = 80/660, 30/660
    for v in ob.data.vertices:
        u = (v.co.x + W/2) / W; t = (v.co.z + H/2) / H
        vb = (t - bot_seal) / (1 - top_seal - bot_seal)
        if 0 < vb < 1 and 0 < u < 1:
            h = A * (math.sin(math.pi*u) ** 0.5) * (math.sin(math.pi*vb) ** 0.45)
            v.co.y -= h
            v.co.x *= (1 - 4.0*h)            # 鼓起来时两边往里收
    sol = ob.modifiers.new("厚度", 'SOLIDIFY'); sol.thickness = 0.0005
    tx = bpy.data.textures.new("褶皱", 'CLOUDS'); tx.noise_scale = 0.004; tx.noise_depth = 6
    dis = ob.modifiers.new("褶皱", 'DISPLACE'); dis.texture = tx; dis.strength = 0.0016; dis.mid_level = 0.5
    bpy.ops.object.shade_smooth()
    m = bpy.data.materials.new("锡箔"); m.use_nodes = True
    bsdf = get_bsdf(m); nt = m.node_tree
    col = nt.nodes.new("ShaderNodeTexImage"); col.image = load_img(os.path.join(ASSETS, "锡箔袋_印刷.jpg"))
    mr = nt.nodes.new("ShaderNodeTexImage"); mr.image = load_img(os.path.join(ASSETS, "锡箔袋_材质.png"), non_color=True)
    sep = nt.nodes.new("ShaderNodeSeparateColor") if "ShaderNodeSeparateColor" in dir(bpy.types) else nt.nodes.new("ShaderNodeSeparateRGB")
    nt.links.new(col.outputs[0], inp(bsdf,"Base Color"))
    nt.links.new(mr.outputs[0], sep.inputs[0])
    nt.links.new(sep.outputs[1], inp(bsdf,"Roughness"))   # G = 粗糙度
    nt.links.new(sep.outputs[2], inp(bsdf,"Metallic"))    # B = 金属度
    noise = nt.nodes.new("ShaderNodeTexNoise"); set_in(noise, ["Scale"], 260.0); set_in(noise, ["Detail"], 8.0)
    bump = nt.nodes.new("ShaderNodeBump"); set_in(bump, ["Strength"], 0.45)
    nt.links.new(noise.outputs[0], inp(bump,"Height")); nt.links.new(bump.outputs[0], inp(bsdf,"Normal"))
    ob.data.materials.append(m)
    ob.location = (-0.070, 0.006, H/2 + 0.002)
    ob.rotation_euler = (math.radians(-10), 0, math.radians(32))
    return ob

def make_figure():
    if os.path.exists(FIGURE_GLB):
        bpy.ops.import_scene.gltf(filepath=FIGURE_GLB)
        obs = bpy.context.selected_objects
        root = obs[0]
        # 缩放到约 9 厘米高
        bpy.ops.object.select_all(action='DESELECT')
        for o in obs: o.select_set(True)
        dims = max(o.dimensions.z for o in obs) or 1
        for o in obs:
            if o.parent is None: o.scale = [s * 0.09 / dims for s in o.scale]; o.location = (0.074, -0.018, 0)
        return root
    img = load_img(os.path.join(ASSETS, "公仔_基础款_透明.png"))
    ratio = img.size[0] / img.size[1]; Hf = 0.092
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    ob = bpy.context.active_object; ob.name = "公仔"
    ob.scale = (Hf*ratio, Hf, 1); bpy.ops.object.transform_apply(scale=True)
    ob.rotation_euler = (math.radians(90), 0, 0); bpy.ops.object.transform_apply(rotation=True)
    m = bpy.data.materials.new("公仔"); m.use_nodes = True
    bsdf = get_bsdf(m); nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
    nt.links.new(tex.outputs[0], inp(bsdf,"Base Color")); nt.links.new(tex.outputs[1], inp(bsdf,"Alpha"))
    set_in(bsdf, ["Roughness"], 0.5)
    try: m.blend_method = 'HASHED'
    except Exception: pass
    ob.data.materials.append(m)
    ob.location = (0.074, -0.018, Hf/2)
    ob.rotation_euler = (0, 0, math.radians(22))
    return ob

def make_floor():
    bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, 0)); fl = bpy.context.active_object; fl.name = "桌面"
    bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0.75, 1.5)); wall = bpy.context.active_object; wall.name = "背景"
    wall.rotation_euler = (math.radians(90), 0, 0)
    m = bpy.data.materials.new("背景"); b = get_bsdf(m)
    set_in(b, ["Base Color"], (0.60, 0.55, 0.48, 1)); set_in(b, ["Roughness"], 0.7)
    fl.data.materials.append(m); wall.data.materials.append(m)

def area(name, loc, size, power, color=(1, 1, 1)):
    bpy.ops.object.light_add(type='AREA', location=loc); L = bpy.context.active_object; L.name = name
    L.data.shape = 'RECTANGLE'; L.data.size = size; L.data.size_y = size * 0.7
    L.data.energy = power; L.data.color = color
    c = L.constraints.new('TRACK_TO'); c.target = TARGET; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    return L


REDO = []      # 只补渲某几帧就把编号写进来，例如 [0, 1, 2]；空着 = 全部重渲（含主图）
FRAMES = 4 if QUICK_TEST else 72     # 一圈的帧数（72 帧 = 每 5° 一张，网页里再做相邻帧淡入淡出）
# ===================== 搭场景（只有一个盒子） =====================
clear_scene()
scene = bpy.context.scene
bpy.ops.object.empty_add(location=(0, 0, BOX_H*0.5)); TARGET = bpy.context.active_object; TARGET.name = "对焦点"

box = make_box("盲盒", (0, 0, 0), 0)

# 只接收阴影的透明地面：网页里盒子下面会有真实的接触阴影
bpy.ops.mesh.primitive_plane_add(size=1.2, location=(0, 0, 0)); sc = bpy.context.active_object; sc.name = "阴影地面"
try: sc.is_shadow_catcher = True
except Exception: pass

area("主光", (-0.40, -0.40, 0.45), 0.6, 8, (1.0, 0.96, 0.90))
area("补光", (0.45, -0.30, 0.20), 0.6, 3, (1.0, 0.98, 0.95))
area("轮廓光", (0.20, 0.50, 0.40), 0.5, 8, (0.72, 0.80, 1.0))      # 偏蓝，配星空背景
area("轮廓光2", (-0.30, 0.45, 0.35), 0.4, 5, (0.80, 0.72, 1.0))   # 另一侧偏紫，让盒子边缘亮一点
area("顶光", (0, 0, 0.70), 0.8, 4)
w = scene.world or bpy.data.worlds.new("World"); scene.world = w; w.use_nodes = True
bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None) or w.node_tree.nodes.new("ShaderNodeBackground")
wo = next((n for n in w.node_tree.nodes if n.type == "OUTPUT_WORLD"), None)
if wo and not wo.inputs[0].is_linked: w.node_tree.links.new(bg.outputs[0], wo.inputs[0])
bg.inputs[0].default_value = (0.85, 0.85, 0.87, 1); bg.inputs[1].default_value = 0.10

# 相机：略微俯视，与网页里盒子的默认角度一致
bpy.ops.object.camera_add(location=(0, -0.62, 0.20)); cam = bpy.context.active_object; cam.name = "相机"
cam.data.lens = 85; cam.data.sensor_width = 36; cam.data.dof.use_dof = False
c = cam.constraints.new('TRACK_TO'); c.target = TARGET; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
scene.camera = cam

# ===================== 渲染设置 =====================
scene.render.engine = 'CYCLES'
scene.cycles.samples = SAMPLES
try: scene.cycles.use_denoising = True
except Exception: pass
try: scene.cycles.denoiser = 'OPENIMAGEDENOISE'   # 固定用同一种降噪，避免有的帧带颗粒
except Exception: pass
if USE_GPU:
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for t in ('OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'):
            try:
                prefs.compute_device_type = t; prefs.get_devices()
                if any(d.type == t for d in prefs.devices):
                    for d in prefs.devices: d.use = (d.type == t)
                    scene.cycles.device = 'GPU'; break
            except Exception: continue
    except Exception: pass
scene.render.resolution_x, scene.render.resolution_y = RES_X, RES_Y
scene.render.film_transparent = True              # 透明背景
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
for vt in ('AgX', 'Filmic'):
    try: scene.view_settings.view_transform = vt; break
    except Exception: continue
scene.view_settings.exposure = -0.3
for lk in ("AgX - Medium High Contrast", "AgX - Base Contrast", "Medium High Contrast"):
    try: scene.view_settings.look = lk; break
    except Exception: continue

out = os.path.join(OUT_DIR, "单盒转盘"); os.makedirs(out, exist_ok=True)

# 1) 正面主图（网页默认展示角度）
if not REDO:
    box.rotation_euler.z = math.radians(-28)
    scene.render.filepath = os.path.join(out, "主图_正面.png")
    bpy.ops.render.render(write_still=True)

# 2) 360° 一圈：逐帧设角度渲染，转速绝对均匀
for i in (REDO or range(FRAMES)):
    print("  渲染第 %d 帧" % i)
    box.rotation_euler.z = math.radians(360.0 * i / FRAMES)
    scene.render.filepath = os.path.join(out, "frame_%02d.png" % i)
    bpy.ops.render.render(write_still=True)
print("完成！序列帧在：", out)
