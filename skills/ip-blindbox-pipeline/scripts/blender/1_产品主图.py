# -*- coding: utf-8 -*-
r"""
IP 盲盒 · ① 产品主图：盒子 + 公仔 + 星空背景（Blender 3.6 / 4.x）
用法：Blender → 顶部「Scripting/脚本」→ 文本→打开 本文件 → 改下面 BASE → ▶ 运行脚本
输出：<项目>\渲染\产品图.png
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

HERO_MODEL = ""          # 摆在盒子旁边的公仔，填 3D模型 里的文件名（如 "01_基础款.glb"）；空着 = 用第一个
BOX_W, BOX_D, BOX_H = 0.065, 0.065, 0.099   # 盒子尺寸（米）：6.5 × 6.5 × 9.9 厘米
ADD_SECOND_BOX = False
ADD_BAG        = False
ADD_FIGURE     = True
FIGURE_GLB     = os.path.join(MODELS_DIR, HERO_MODEL) if HERO_MODEL else _first_glb()
RES_X, RES_Y   = (400, 500) if QUICK_TEST else (1600, 2000)
SAMPLES        = 16 if QUICK_TEST else 128
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

def import_glb_figure(path, height=0.09, gold=False):
    """导入混元3D模型：缩放到指定高度、脚底放到地面、切掉脚下的薄底座"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    obs = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in obs if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in obs:
        if o.type != 'MESH': bpy.data.objects.remove(o, do_unlink=True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active; ob.name = "公仔"
    ob.rotation_mode = 'XYZ'   # glTF 导入默认是四元数，不改的话 rotation_euler 不生效，公仔转不动
    me = ob.data
    zs = [v.co.z for v in me.vertices]; zmin, zmax = min(zs), max(zs)
    s = height / (zmax - zmin)
    for v in me.vertices:
        v.co.z -= zmin; v.co *= s
    # 切掉贴地的薄底座（只有不到 0.3% 高度那一层）
    bm = bmesh.new(); bm.from_mesh(me)
    cut = height * 0.005
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < cut], context='VERTS')
    bm.to_mesh(me); bm.free()
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
    for v in me.vertices: v.co.x -= cx; v.co.y -= cy
    me.update()
    bpy.ops.object.shade_smooth()
    # 混元导出的材质高光偏强（specular 2.0），会让黑衣服发灰，这里压回正常
    for m in me.materials:
        b = get_bsdf(m)
        set_in(b, ["Specular IOR Level", "Specular"], 0.3)
        set_in(b, ["Coat Weight", "Clearcoat"], 0.0)
    if gold:
        for m in me.materials:
            b = get_bsdf(m)
            for l in list(m.node_tree.links):
                if l.to_node == b and l.to_socket.name == "Metallic": m.node_tree.links.remove(l)
            set_in(b, ["Metallic"], 0.85); set_in(b, ["Roughness"], 0.22)
    return ob

def make_figure():
    if os.path.exists(FIGURE_GLB):
        ob = import_glb_figure(FIGURE_GLB)
        ob.location = (0.048, -0.03, 0)
        ob.rotation_euler = (0, 0, math.radians(18))
        return ob
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

STARRY_BG = True   # True = 星空背景；False = 原来的米色背景

def star_layer(nt, mapping_out, scale, size, strength):
    """一层星星：Voronoi 点 → 很小的亮点"""
    v = nt.nodes.new("ShaderNodeTexVoronoi"); set_in(v, ["Scale"], scale); set_in(v, ["Randomness"], 1.0)
    nt.links.new(mapping_out, v.inputs["Vector"])
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].position = 0.0; r.color_ramp.elements[0].color = (strength, strength, strength, 1)
    r.color_ramp.elements[1].position = size; r.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(v.outputs["Distance"], r.inputs["Fac"])
    return r.outputs["Color"]

def make_floor():
    bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, 0)); fl = bpy.context.active_object; fl.name = "桌面"
    bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0.75, 1.5)); wall = bpy.context.active_object; wall.name = "背景"
    wall.rotation_euler = (math.radians(90), 0, 0)
    if not STARRY_BG:
        m = bpy.data.materials.new("背景"); b = get_bsdf(m)
        set_in(b, ["Base Color"], (0.60, 0.55, 0.48, 1)); set_in(b, ["Roughness"], 0.7)
        fl.data.materials.append(m); wall.data.materials.append(m)
        return
    # 桌面：深蓝灰、带一点点反光，能映出盒子和星光
    mf = bpy.data.materials.new("夜色桌面"); bf = get_bsdf(mf)
    set_in(bf, ["Base Color"], (0.012, 0.014, 0.03, 1)); set_in(bf, ["Roughness"], 0.32)
    fl.data.materials.append(mf)
    # 背景墙：夜空渐变 + 淡淡星云 + 两层星星，全部自发光，不受灯光影响
    mw = bpy.data.materials.new("星空"); mw.use_nodes = True; nt = mw.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(em.outputs[0], out.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # 天空渐变（下亮上暗）
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    sky = nt.nodes.new("ShaderNodeValToRGB")
    sky.color_ramp.elements[0].position = 0.0; sky.color_ramp.elements[0].color = (0.035, 0.03, 0.09, 1)
    sky.color_ramp.elements[1].position = 0.6; sky.color_ramp.elements[1].color = (0.004, 0.005, 0.018, 1)
    nt.links.new(sep.outputs["Y"], sky.inputs["Fac"])
    # 星云：低频噪声，偏紫蓝
    nz = nt.nodes.new("ShaderNodeTexNoise"); set_in(nz, ["Scale"], 3.0); set_in(nz, ["Detail"], 6.0)
    nt.links.new(tc.outputs["Generated"], nz.inputs["Vector"])
    neb = nt.nodes.new("ShaderNodeValToRGB")
    neb.color_ramp.elements[0].position = 0.45; neb.color_ramp.elements[0].color = (0, 0, 0, 1)
    neb.color_ramp.elements[1].position = 0.85; neb.color_ramp.elements[1].color = (0.10, 0.04, 0.16, 1)
    nt.links.new(nz.outputs["Fac"], neb.inputs["Fac"])
    add1 = nt.nodes.new("ShaderNodeMixRGB"); add1.blend_type = 'ADD'; add1.inputs[0].default_value = 1.0
    nt.links.new(sky.outputs["Color"], add1.inputs[1]); nt.links.new(neb.outputs["Color"], add1.inputs[2])
    # 星星：细密小星 + 稀疏亮星（暖白）
    g = tc.outputs["Generated"]
    s1 = star_layer(nt, g, 120.0, 0.05, 25.0)   # 细密小星（数字越大星越多）
    s2 = star_layer(nt, g, 30.0, 0.045, 80.0)   # 稀疏亮星（会被虚化成小光斑）
    add2 = nt.nodes.new("ShaderNodeMixRGB"); add2.blend_type = 'ADD'; add2.inputs[0].default_value = 1.0
    nt.links.new(add1.outputs[0], add2.inputs[1]); nt.links.new(s1, add2.inputs[2])
    warm = nt.nodes.new("ShaderNodeMixRGB"); warm.blend_type = 'MULTIPLY'; warm.inputs[0].default_value = 1.0
    warm.inputs[2].default_value = (1.0, 0.90, 0.70, 1)
    nt.links.new(s2, warm.inputs[1])
    add3 = nt.nodes.new("ShaderNodeMixRGB"); add3.blend_type = 'ADD'; add3.inputs[0].default_value = 1.0
    nt.links.new(add2.outputs[0], add3.inputs[1]); nt.links.new(warm.outputs[0], add3.inputs[2])
    nt.links.new(add3.outputs[0], em.inputs["Color"]); set_in(em, ["Strength"], 1.0)
    wall.data.materials.append(mw)

def area(name, loc, size, power, color=(1, 1, 1)):
    bpy.ops.object.light_add(type='AREA', location=loc); L = bpy.context.active_object; L.name = name
    L.data.shape = 'RECTANGLE'; L.data.size = size; L.data.size_y = size * 0.7
    L.data.energy = power; L.data.color = color
    c = L.constraints.new('TRACK_TO'); c.target = TARGET; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    return L

# ===================== 搭场景 =====================
clear_scene()
scene = bpy.context.scene
bpy.ops.object.empty_add(location=(0.0, 0.0, BOX_H*0.50)); TARGET = bpy.context.active_object; TARGET.name = "对焦点"

make_floor()
make_box("盲盒", (-0.03, 0.005, 0), -22)
if ADD_SECOND_BOX: make_box("盲盒2", (0.005, 0.10, 0), 12)
if ADD_BAG: make_bag()
if ADD_FIGURE: make_figure()

area("主光", (-0.45, -0.40, 0.45), 0.7, 9, (1.0, 0.95, 0.88))
area("补光", (0.50, -0.30, 0.20), 0.6, 2.5, (1.0, 0.97, 0.92))
area("轮廓光", (0.15, 0.55, 0.40), 0.5, 9, (0.70, 0.80, 1.0) if STARRY_BG else (1, 1, 1))
area("顶光", (0, -0.05, 0.70), 0.8, 2)

w = scene.world or bpy.data.worlds.new("World"); scene.world = w; w.use_nodes = True
bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None) or w.node_tree.nodes.new("ShaderNodeBackground")
wo = next((n for n in w.node_tree.nodes if n.type == "OUTPUT_WORLD"), None)
if wo and not wo.inputs[0].is_linked: w.node_tree.links.new(bg.outputs[0], wo.inputs[0])
if STARRY_BG: bg.inputs[0].default_value = (0.10, 0.12, 0.26, 1); bg.inputs[1].default_value = 0.05
else: bg.inputs[0].default_value = (0.82, 0.82, 0.84, 1); bg.inputs[1].default_value = 0.12

bpy.ops.object.camera_add(location=(0.16, -0.60, 0.16)); cam = bpy.context.active_object; cam.name = "相机"
cam.data.lens = 78; cam.data.sensor_width = 36
cam.data.dof.use_dof = True; cam.data.dof.focus_object = TARGET; cam.data.dof.aperture_fstop = 9   # 数字越小背景越虚
c = cam.constraints.new('TRACK_TO'); c.target = TARGET; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
scene.camera = cam

# ===================== 渲染设置 =====================
scene.render.engine = 'CYCLES'
scene.cycles.samples = SAMPLES
try: scene.cycles.use_denoising = True
except Exception: pass
if USE_GPU:
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for t in ('OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'):
            try:
                prefs.compute_device_type = t; prefs.get_devices()
                if any(d.type == t for d in prefs.devices):
                    for d in prefs.devices: d.use = True
                    scene.cycles.device = 'GPU'; break
            except Exception: continue
    except Exception: pass
scene.render.resolution_x, scene.render.resolution_y = RES_X, RES_Y
scene.render.film_transparent = False
scene.view_settings.exposure = -0.3
for vt in ('AgX', 'Filmic'):
    try: scene.view_settings.view_transform = vt; break
    except Exception: continue
try: scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
os.makedirs(OUT_DIR, exist_ok=True)

if RENDER_NOW:
    scene.render.filepath = os.path.join(OUT_DIR, "产品图.png")
    bpy.ops.render.render(write_still=True)
    if TURNTABLE:
        box = bpy.data.objects["盲盒"]
        for o in [o for o in bpy.data.objects if o.name in ("盲盒2", "锡箔袋", "公仔")]: o.hide_render = True
        scene.frame_start, scene.frame_end = 1, 72
        box.rotation_euler.z = math.radians(-22); box.keyframe_insert("rotation_euler", frame=1)
        box.rotation_euler.z = math.radians(-22 + 360 * 71/72); box.keyframe_insert("rotation_euler", frame=72)
        for fc in box.animation_data.action.fcurves:
            for k in fc.keyframe_points: k.interpolation = 'LINEAR'
        scene.render.filepath = os.path.join(OUT_DIR, "转盘", "frame_")
        bpy.ops.render.render(animation=True)
print("完成！图片在：", OUT_DIR)
