root = r'C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm'


def patch(path, old, new):
    s = open(path, newline='', encoding='utf-8').read()
    if new.strip() in s:
        print('already', path)
        return
    assert s.count(old) == 1, path
    nl = '\r\n' if '\r\n' in s else '\n'
    s = s.replace(old, old + nl + new)
    open(path, 'w', newline='', encoding='utf-8').write(s)
    print('patched', path)


patch(root + r'\CMakeLists.txt', '        src/Sprites.cpp src/Sprites.h', '        src/PxWeaponArt.cpp src/PxWeaponArt.h')
line = r'    <ClCompile Include="C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm\src\Sprites.cpp" />'
patch(root + r'\build\wkJellyWorm.vcxproj', line, line.replace('Sprites.cpp', 'PxWeaponArt.cpp'))
