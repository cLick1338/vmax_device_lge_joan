#
# Copyright (C) 2018-2023 The LineageOS Project
#
# SPDX-License-Identifier: Apache-2.0
#

# Inherit some common Lineage stuff.
$(call inherit-product, vendor/lineage/config/common_full_phone.mk)

$(call inherit-product, $(SRC_TARGET_DIR)/product/product_launched_with_n_mr1.mk)

# Inherit from those products. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/non_ab_device.mk)

# Inherit from joan device
$(call inherit-product, device/lge/joan/device.mk)

# Device identifiers
PRODUCT_DEVICE := joan
PRODUCT_NAME := lineage_joan
PRODUCT_BRAND := lge
PRODUCT_MODEL := joan
PRODUCT_MANUFACTURER := LGE
PRODUCT_RELEASE_NAME := V30

PRODUCT_GMS_CLIENTID_BASE := android-om-lg

# Build number shown in About phone, no spaces allowed in the value
PRODUCT_SYSTEM_PROPERTIES += \
    ro.build.display.id=Vmax-$(TARGET_BUILD_VARIANT)-$(PLATFORM_VERSION)-$(BUILD_ID)-$(or $(BUILD_NUMBER),eng)

PRODUCT_BUILD_PROP_OVERRIDES += \
    BuildDesc="joan_global_com-user 8.0.0 OPR1.170623.026 181381736b4e9 release-keys" \
    BuildFingerprint="lge/joan_global_com/joan:8.0.0/OPR1.170623.026/181381736b4e9:user/release-keys" \
    DeviceName="joan"

PRODUCT_SYSTEM_PROPERTY_BLACKLIST += ro.product.model ro.vendor.product.model ro.product.system.model

ifneq ($(filter user userdebug,$(TARGET_BUILD_VARIANT)),)
PRODUCT_DEFAULT_DEV_CERTIFICATE := .repo/local_keys/joan/releasekey
PRODUCT_OTA_PUBLIC_KEYS := .repo/local_keys/joan/releasekey.x509.pem
endif
