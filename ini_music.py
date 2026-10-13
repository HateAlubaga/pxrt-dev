import re, shutil, time, sys

INI = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\wkJellyWorm.ini'

raw = open(INI, 'rb').read()
text = raw.decode('utf-8', errors='surrogateescape')
crlf = '\r\n' in text
t = text.replace('\r\n', '\n')

m = re.search(r'^\[music\]\n(.*?)(?=^\[|\Z)', t, re.S | re.M)
assert m, '[music] section not found'
old = m.group(1)


def val(key, default):
    mm = re.search(r'^' + key + r'=(.*)$', old, re.M | re.I)
    return mm.group(1).strip() if mm else default


enabled = val('Enabled', '1')
am = val('AutoplayMatch', '1')
al = val('AutoplayLobby', '0')
vol = val('Volume', '70')
loop = val('Loop', '1')
shuf = val('Shuffle', '1')
track = val('Track', r'jelly\music')
# keep a custom Track (file, folder, url); the old default folder becomes the new default source
if track.lower() in (r'jelly\music', 'jelly/music', ''):
    track = 'modarchive'
radio = val('Radio', '1')
maxkb = val('MaxSizeKB', '3072')
keep = val('CacheKeep', '40')
maxid = val('ModArchiveMaxId', '215000')

new = f'''; Tracker music (.xm .it .mod .s3m .stm .669 .mtm .far .ult .okt .med .amf ...), played by wkJellyWorm.
; Chat commands (network lobby and in match):
;   /music new         download a NEW random track from modarchive.org and play it right now (also: /music n)
;   /music next        online source: a new track; folder source: next file
;   /music mod <id>    play Mod Archive module number <id>
;   /music play [file|url|folder|N|cache]   /music stop|pause|resume   /music vol N   /music list   /music cache
;   /music status      /music reload (re-read this section)
; Log for debugging: jelly\\music.log
Enabled={enabled}
; 1 = start playing when a match starts (also replays)
AutoplayMatch={am}
; 1 = start playing when you enter a network lobby (it keeps playing into the match)
AutoplayLobby={al}
; modarchive = a NEW random track from modarchive.org every time (downloaded once, kept in jelly\\cache\\music).
; No internet: a random already downloaded track, or a file from jelly\\music.
; Other values: a folder (= playlist of every tracker file inside), one file, or an http(s) URL.
Track={track}
; Track=modarchive only: 1 = when a track ends the next NEW one is downloaded (endless radio),
; 0 = repeat the track (see Loop).
Radio={radio}
; Modules bigger than this many KB are skipped. Typical modules are 20-600 KB.
MaxSizeKB={maxkb}
; How many downloaded modules stay in jelly\\cache\\music (oldest are deleted).
CacheKeep={keep}
; Random Mod Archive ids are drawn from 1..this number (the archive has about 215000 modules).
ModArchiveMaxId={maxid}
; 0..100
Volume={vol}
; 1 = repeat the track (or the whole playlist) when Track is a file, folder or URL
Loop={loop}
; 1 = random order when Track is a folder
Shuffle={shuf}

'''
t2 = t[:m.start(1)] + new + t[m.end(1):]
if t2 == t:
    print('nothing to change')
    sys.exit(0)
if crlf:
    t2 = t2.replace('\n', '\r\n')
bak = INI + '.bak_claude_' + time.strftime('%Y%m%d_%H%M%S')
shutil.copy2(INI, bak)
open(INI, 'wb').write(t2.encode('utf-8', errors='surrogateescape'))
print('ok, backup', bak)
