p = r'C:\Users\Admin\pxrt_dev\pxrt_e_pseudo.lua'
s = open(p, encoding='utf-8', newline='').read().replace('\r\n', '\n')
old = """  -- engine root class name of a script class
"""
new = """  ---------------------------------------------------------------------
  -- CObjList (script-owned list) and the Childs view of pseudo objects
  ---------------------------------------------------------------------
  local function listView(getList)
    local objsArr = setmetatable({}, {
      __index = function(_, i)
        if type(i) ~= "number" then return nil end
        return getList()[ti(i) + 1]
      end,
      __newindex = function(_, i, v) getList()[ti(i) + 1] = v end,
    })
    local v = setmetatable({ __cls = "CObjList" }, {
      __index = function(t, k)
        if k == "Count" then return #getList() end
        if k == "Objs" then return objsArr end
        if k == "GetObject" then return function(_, i) return getList()[ti(i) + 1] end end
        if k == "Add" then return function(_, o) local l = getList(); l[#l + 1] = o; return #l end end
        if k == "Remove" then
          return function(_, o)
            local l = getList()
            for i = #l, 1, -1 do if l[i] == o then table.remove(l, i) end end
            return 0
          end
        end
        if k == "Compact" then
          return function()
            local l = getList()
            for i = #l, 1, -1 do local o = l[i]; if o == nil or o == 0 then table.remove(l, i) end end
            return 0
          end
        end
        if k == "Clear" then return function() local l = getList(); for i = #l, 1, -1 do l[i] = nil end return 0 end end
        return 0
      end,
    })
    return v
  end
  R.builtinClasses.CObjList = function()
    local list = {}
    return listView(function() return list end)
  end
  local noKids = {}
  function R.childsOf(obj)
    local v = rawget(obj, "__childsView")
    if not v then
      v = listView(function() return rawget(obj, "__kids") or noKids end)
      rawset(obj, "__childsView", v)
    end
    return v
  end

  -- engine root class name of a script class
"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
