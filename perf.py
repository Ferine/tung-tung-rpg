import ctypes, capture, sys
core = capture.Core()
core.lib.retro_get_memory_data.restype = ctypes.c_void_p
core.lib.retro_get_memory_data.argtypes = [ctypes.c_uint]
core.load('tungtung.sfc')
ptr = core.lib.retro_get_memory_data(2)
syms={}
for line in open('tungtung.sym'):
    p=line.split()
    if len(p)==2:
        try: syms[p[1]]=int(p[0],16)
        except ValueError: pass
def u16(n): return int.from_bytes(bytes(ctypes.string_at(ptr+syms[n]-0x7e0000,2)),'little')
def pk(n,c=1): return bytes(ctypes.string_at(ptr+syms[n]-0x7e0000,c))
def fps(label):
    a=u16('frameCounter'); core.run(60)
    print("%-22s %d/60" % (label, u16('frameCounter')-a))
core.press([]); core.run(90); fps("TITLE")
core.press(['start']); core.run(6); core.press([]); core.run(140); fps("FIELD idle")
core.press(['down']); core.run(30); fps("FIELD walking")
core.press(['down']); core.run(240)
for i in range(8):
    core.press(['up' if i%2 else 'down']); core.run(80)
core.press([]); core.run(40)
print("state", pk('gameState').hex())
fps("BATTLE active")
# open a menu
for i in range(240):
    core.run(1)
    if pk('tccs_src/battle.asm_bstate')[0]==2: break
fps("BATTLE command menu")
core.press(['down']); core.run(4); core.press([]); core.run(4)
core.press(['a']); core.run(4); core.press([]); core.run(10)
print("bstate", pk('tccs_src/battle.asm_bstate')[0])
fps("BATTLE skill list")
