# pxrt_dev — ProjectX on Lua for Worms Armageddon

Development workspace for running ProjectX (PX) weapon/scheme scripts on Worms Armageddon 3.8.1
without the original ProjectX module. PX scripts (`.pxc`/`.pxl`) are transpiled to Lua and run on
the `pxrt` Lua runtime inside the [wkJellyWorm](https://github.com/HateAlubaga/wkJellyWorm) WormKit module.

This is a working directory, not a polished package: many one-off patch and scan scripts are kept
because they record how the runtime got where it is.

## Layout

| Path | What |
| --- | --- |
| `px_pipeline/pxc2lua.py` | PX to Lua transpiler (`pxast.py` parser, `pxbake.py`, `pxlayout.py`, `pxclasses.py`) |
| `pxrt_core.lua`, `pxrt_e_*.lua`, `pxrt_engine.lua` | Lua runtime: PX classes, structs, hooks, terrain, quads, game glue |
| `pxboot.lua` | Runtime boot script loaded by the jelly package |
| `pxgen.py`, `pxdeploy.py`, `pxsbornik.py`, `pxquarantine.py` | Package generation, deploy into the game dir, bundle ("sbornik") builder, quarantine of broken packages |
| `harness/` | Offline harness: runs every generated package against a mock of the wkJellyWorm DLL API (`mock_dll.lua`, `run.lua`); `harness_all.py` runs all packages in parallel, `bench.py` measures per-frame cost |
| `audit/` | Per-package audit notes |
| `re/`, `re_*.py`, `re_*.md`, `tools/` | Reverse-engineering helpers and notes for WA 3.8.1 (weapon launch struct, terrain, rotated sprites, worm rendering) |
| `errlog_stack.py` | Maps stack dwords in a WA `ERRORLOG.TXT` to module + offset |
| `re/symxlate.py`, `re/oldfn.py` | Symbolize offsets in an old wkJellyWorm.dll without symbols, using a fresh `/MAP` build of the current source |
| `ehtest/` | Standalone repro of the 2026-10-10 crash (`STATUS_INVALID_UNWIND_TARGET` 0xC0000029): Lua error longjmp across SEH-handled native calls. `run_matrix.ps1` runs old/new code under `/EHsc` and `/EHa`. The old variant needs `ehtest/old_inc/sol/` (`sol.hpp`, `config.hpp`, `forward.hpp` from wkJellyWorm commit 9fc9940) |
| `mt/` | Native tests for wkJellyWorm pieces (music, online music, integration) |
| `paths.py` | Hard-coded local paths (`DEV`, `GAME`, `JELLY`); edit for your machine |

## Not in this repository

Kept locally only, because they are other people's work:

- Worms Armageddon disassembly listings (`rs/`, `wr/`, `*.asm`).
- The ProjectX script corpus and libraries (`px_pipeline/px/`, `px_pipeline/pxl/`, `corpus.json`),
  the ProjectX wiki dump (`px_pipeline/pxwiki/`) and the Lua generated from them (`px_pipeline/testout/`).

Build output, snapshots and `*.bak*` files are also ignored.

## Requirements

- Python 3.10 (`py -3.10`), with `lupa` for the harness.
- Visual Studio 2022 (Win32) for `ehtest/` and `mt/`.
- Worms Armageddon 3.8.1 with wkJellyWorm for in-game use.
