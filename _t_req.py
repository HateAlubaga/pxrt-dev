import sys
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
from paths import *
import pxgen
from lupa.lua53 import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True, register_eval=False, encoding='utf-8')
g = lua.globals()
out = pxgen.OUT_LIBS.replace(chr(92), '/')
dev = DEV.replace(chr(92), '/')
lua.execute("package.path = '%s/?.lua;%s/?.lua'" % (out, dev))
r = lua.execute('''
local H = dofile("%s/harness/mock_dll.lua")
local msgs = {}
_G.__pxrt_logsink = function(m) msgs[#msgs+1] = m end
local ok, R = pcall(require, "pxrt")
return tostring(ok), tostring(R and type(R) == "table" and R.E ~= nil), table.concat(msgs, " | ")
''' % dev)
print(r)
