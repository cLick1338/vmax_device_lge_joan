#
# Copyright (C) 2020-2021 The LineageOS Project
#
# SPDX-License-Identifier: Apache-2.0
#

import common


def FullOTA_InstallEnd(info):
    boot_write = 'package_extract_file("boot.img", "/dev/block/bootdevice/by-name/boot");'
    if info.script.script.count(boot_write) != 1:
        raise ValueError("Expected exactly one joan boot image write")
    index = info.script.script.index(boot_write)
    info.script.script[index] = (
        'if getprop("vmax.ota.preserve_boot") == "1" then\n'
        '  ui_print("Preserving current boot image");\n'
        'else\n  ' + boot_write + '\nendif;')
    common.ZipWriteStr(info.output_zip, "META-INF/com/android/vmax-preserve-boot", "1")
    info.script.AppendExtra('assert(run_program("/tmp/install/bin/device_check.sh") == 0);');
