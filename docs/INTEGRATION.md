# Cross-partition integration findings

Static reference candidates only. No runtime causality, checkvintf, codec enumeration, SELinux decision or hardware verification.

Stock product/system_ext may be separate logical mounts. Read /proc/mounts on-device before choosing a system-side target.

## Prioritized hardware wiring

### media

Vendor/odm provider manifest declaration exists; compatibility-matrix requirements and system software services are not counted as hardware providers. Do not duplicate device HALs into framework VINTF. Service startup, binder connection and framework logs still required.

- `android.hardware.media.omx` 1.0 — `/vendor/etc/vintf/manifest.xml`
- `android.hardware.media.c2` 1.1 — `/vendor/etc/vintf/manifest/manifest_media_c2_V1_1_default.xml`
### fingerprint

Vendor/odm provider manifest declaration exists; compatibility-matrix requirements and system software services are not counted as hardware providers. Do not duplicate device HALs into framework VINTF. Service startup, binder connection and framework logs still required.

- `android.hardware.biometrics.fingerprint` 2.1 — `/vendor/etc/vintf/manifest/android.hardware.biometrics.fingerprint@2.1-service.xml`
### usb_otg

Vendor/odm provider manifest declaration exists; compatibility-matrix requirements and system software services are not counted as hardware providers. Do not duplicate device HALs into framework VINTF. Service startup, binder connection and framework logs still required.

- `android.hardware.usb` 1.3 — `/vendor/etc/vintf/manifest/android.hardware.usb@1.2-service-mediatekv2.xml`
### media

Stock XML advertises MediaTek hardware video codecs. Existing vendor configuration alone does not prove registration or encoding; do not override base software limits, codec ranking, or performance properties.


## Explicit imports/includes not supplied by the GSI

- `/system_ext/etc/init/hw/meta_init.system.rc` → `/system_ext/etc/init/hw/vendor_init_as_system.rc` (mount topology and init action semantics need review)
- `/system_ext/etc/init/hw/meta_init.system.rc` → `/system_ext/etc/init/hw/init.aee.rc` (mount topology and init action semantics need review)
- `/system_ext/etc/init/hw/meta_init.system.rc` → `/system/etc/init/hwservicemanager.rc` (mount topology and init action semantics need review)
- `/system_ext/etc/init/hw/meta_init.system.rc` → `/system/etc/init/android.hidl.allocator@1.0-service.rc` (mount topology and init action semantics need review)
- `/system_ext/etc/init/hw/meta_init.system.rc` → `/system_ext/etc/init/aee_aed.rc` (mount topology and init action semantics need review)
- `/system_ext/etc/init/hw/meta_init.system.rc` → `/system_ext/etc/init/aee_aed64.rc` (mount topology and init action semantics need review)
- `/system_ext/etc/init/hw/meta_init.system.rc` → `/system_ext/etc/init/mobile_log_d.rc` (mount topology and init action semantics need review)
- `/system_ext/etc/init/hw/meta_init.system.rc` → `/system_ext/etc/init/emdlogger.rc` (mount topology and init action semantics need review)
- `/vendor/etc/init/hw/factory_init.rc` → `/system_ext/etc/init/hw/vendor_init_as_system.rc` (mount topology and init action semantics need review)
- `/vendor/etc/init/hw/factory_init.rc` → `/system_ext/etc/init/hw/init.aee.rc` (mount topology and init action semantics need review)
- `/vendor/etc/init/hw/factory_init.rc` → `/system/etc/init/update_verifier.rc` (mount topology and init action semantics need review)
- `/vendor/etc/init/hw/factory_init.rc` → `/system/etc/init/hwservicemanager.rc` (mount topology and init action semantics need review)
- `/vendor/etc/init/hw/factory_init.rc` → `/system/etc/init/android.hidl.allocator@1.0-service.rc` (mount topology and init action semantics need review)
- `/vendor/etc/init/hw/init.mt6768.rc` → `/system_ext/etc/init/hw/init.aee.rc` (mount topology and init action semantics need review)
- `/vendor/etc/init/hw/init.mt6768.usb.rc` → `/system_ext/etc/init/hw/init.usb.rc` (mount topology and init action semantics need review)
- `/vendor/etc/init/hw/multi_init.rc` → `/system_ext/etc/init/aee_aed.rc` (mount topology and init action semantics need review)
- `/vendor/etc/init/hw/multi_init.rc` → `/system_ext/etc/init/aee_aed64.rc` (mount topology and init action semantics need review)

## Conflicting stock property values

- `/vendor/build.prop`: `ro.product.first_api_level`: line 43 = 31, line 653 = 34, line 656 = 34. Never infer active API level from last-value parsing.

Full HAL declarations, architecture-aware unresolved ELF candidates, codec limits and exact reference hashes are in `integration.json`. APEX-contained libraries and runtime linker namespaces are not yet fully inventoried. No compatibility patches are approved by this report.
