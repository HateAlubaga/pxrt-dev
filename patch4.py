p = r'C:\Users\Admin\pxrt_dev\pxrt_e_consts.lua'
s = open(p, encoding='utf-8').read()
s = s.replace("WAction_None = 0, WAction_Bounce = 1, WAction_Homing = 2, WAction_Dig = 3,",
              "WAction_None = 0, WAction_Homing = 1, WAction_Bounce = 2, WAction_Roam = 3, WAction_Dig = 4,")
s = s.replace("WAT_TrackMovement = 0, WAT_Fast = 1, WAT_TrackSpeed = 2, WAT_Slow = 3, WAT_Medium = 4, WAT_Rotation = 5,\n    WAT_HSpeed = 6,",
              "WAT_TrackSpeed = 0, WAT_Rotation = 1, WAT_TrackMovement = 2, WAT_HSpeed = 3, WAT_Slow = 4, WAT_Medium = 5,\n    WAT_Fast = 6,")
open(p, 'w', encoding='utf-8', newline='\n').write(s)
