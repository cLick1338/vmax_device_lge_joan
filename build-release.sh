#!/bin/bash
# Vmax
set -eo pipefail

cd "$(dirname "$(realpath "$0")")/../../.."
export LINEAGE_BUILDTYPE=RELEASE
python3 device/lge/joan/release.py keys
source build/envsetup.sh
source vendor/lineage/vars/aosp_target_release
lunch "lineage_joan-${aosp_target_release}-${JOAN_BUILD_VARIANT:-userdebug}"
export BUILD_NUMBER="${BUILD_NUMBER:-$(date -u +%Y%m%d%H%M%S)}"
m "-j${JOAN_BUILD_JOBS:-8}" target-files-package otatools
python3 device/lge/joan/release.py sign \
    "$OUT/obj/PACKAGING/target_files_intermediates/lineage_joan-target_files.zip" \
    "$OUT/release"
