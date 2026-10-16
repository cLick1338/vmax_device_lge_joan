#Vmax
# render.py -- <out pattern> [start-end | f1,f2,...]
import sys, bpy
args = sys.argv[sys.argv.index("--") + 1:]
cp = bpy.context.preferences.addons["cycles"].preferences
cp.compute_device_type = "OPTIX"
cp.refresh_devices()
for d in cp.devices:
    d.use = d.type == "OPTIX"
    print("DEVICE", d.type, d.name, d.use)
sc = bpy.context.scene
sc.cycles.device = "GPU"
sc.render.filepath = args[0]
spec = args[1] if len(args) > 1 else ""
if "," in spec or (spec and "-" not in spec):
    for f in map(int, spec.split(",")):
        sc.frame_set(f)
        sc.render.filepath = args[0].replace("###", f"{f:03d}")
        bpy.ops.render.render(write_still=True)
else:
    if spec:
        sc.frame_start, sc.frame_end = map(int, spec.split("-"))
    bpy.ops.render.render(animation=True)
