p = r'C:\Users\Admin\pxrt_dev\harness\run.lua'
s = open(p, encoding='utf-8', newline='').read()
old = """    for _, w in ipairs(H.worms) do
      local o, e = pcall(H.sendMessage, "CTaskWorm", w, H.TG, 2, 0, 0)
      if not o then L("worm frame: %s", tostring(e)) return false end
    end
    local o, e = pcall(H.sendMessage, "CTaskTurnGame", H.TG, nil, 2, 0, 0)
    if not o then L("tg frame: %s", tostring(e)) return false end
"""
new = """    -- engine order: the turn game gets M_FRAME first (our hook runs FirstFrame there), then it forwards to its children
    local o, e = pcall(H.sendMessage, "CTaskTurnGame", H.TG, nil, 2, 0, 0)
    if not o then L("tg frame: %s", tostring(e)) return false end
    for _, w in ipairs(H.worms) do
      local o, e = pcall(H.sendMessage, "CTaskWorm", w, H.TG, 2, 0, 0)
      if not o then L("worm frame: %s", tostring(e)) return false end
    end
"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
