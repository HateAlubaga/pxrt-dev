#!/bin/bash
# differential regression: baseline runtime (what is deployed in the game) vs the working copy, per-package trace hashes
cd /c/Users/Admin/pxrt_dev/harness
export HARNESS_BOOT=1 HARNESS_TRACE=1 HARNESS_NOGC=1
L="/c/Program Files (x86)/by Decepticon/Worms Armageddon/jelly/lualibs"
rm -rf /c/Users/Admin/pxrt_dev/base_rt; mkdir -p /c/Users/Admin/pxrt_dev/base_rt; cp "$L"/pxrt*.lua "$L"/pxboot.lua /c/Users/Admin/pxrt_dev/base_rt/
HARNESS_BASE='C:\Users\Admin\pxrt_dev\base_rt' HARNESS_OUT='C:\Users\Admin\pxrt_dev\out\res_base.jsonl' py -3.10 harness_all.py > /c/Users/Admin/pxrt_dev/diff_base.txt 2>&1
HARNESS_OUT='C:\Users\Admin\pxrt_dev\out\res_new.jsonl' py -3.10 harness_all.py > /c/Users/Admin/pxrt_dev/diff_new.txt 2>&1
echo finished > /c/Users/Admin/pxrt_dev/diff_done.txt
