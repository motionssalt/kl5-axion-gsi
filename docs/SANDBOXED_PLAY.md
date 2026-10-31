# Sandboxed Google Play — NOT enabled

**No sandboxed Play implementation, APK injection or working store screenshot is claimed.** Phase 6 is gated until a real compatibility build has been released after patched-image emulator boot. The installer option stays absent while compatibility is unproven.

## Preliminary source findings

Official GrapheneOS documentation describes ordinary unprivileged Google Play apps supported by an OS compatibility layer, installed with the GrapheneOS App Store:
- https://grapheneos.org/usage#sandboxed-google-play
- https://github.com/GrapheneOS/platform_packages_apps_GmsCompat
- https://github.com/GrapheneOS/platform_frameworks_base
- https://github.com/GrapheneOS/Apps
- https://github.com/GrapheneOS/platform_external_GmsCompatConfig
- https://github.com/GrapheneOS/platform_packages_apps_GmsCompat/releases (GmsCompatConfig releases originate here; only config-holder and text config changes apply)

The official Apps client repository is **GrapheneOS/Apps**, not the nonexistent `platform_packages_apps_Apps` path. Framework source contains `core/java/com/android/internal/gmscompat/`, including GmsHooks, GmsCompatApp/Lib, GmsCompatConfig, PlayStoreHooks, Binder/AIDL interfaces and related client/system-service code. This is not a standalone APK feature.

During provisioning, the inspected framework and GmsCompat repositories exposed default branch `17`, not a directly available Android 16 branch. **Those current defaults must not be transplanted into Android 16.** Phase 6 code attempts explicit Android 16 pin discovery only after the prior release gate; a missing branch is a blocker. An exact historical Android 16 tag/commit set and matching interfaces still need to be identified.

## Framework/system work still required

A valid port must map every GrapheneOS GmsCompat framework callsite against the exact AxionOS bootclasspath/framework/services binaries, package/permission behavior, Binder/config interface versions, installer/store permission and package-visibility integration, process/application hooks, network/location/notification behavior, SELinux integration and signing/hidden-API constraints. It must preserve base optimizations and ART/dexpreopt/boot-image compatibility. Dynamic config delivery and signature trust must match the pinned app and framework code.

No rigorous binary-framework transformer/recompiler or proof of those interfaces exists in this pipeline. Replacing framework.jar/services.jar with a different ROM's binaries, adding privileged Google packages, granting broad permissions, dropping in GmsCompat APK alone or using Xposed would not meet the request and is not done. Building Android from source is explicitly out of scope.

## Honest fallback

The compatibility GSI can ship without Google integration. Keep vanilla operation and use independently obtained ordinary applications/web apps as appropriate. A separately reviewed microG setup may address some app APIs but is **not** sandboxed Google Play and is not installed or represented as equivalent. Simply installing Play Services/Store APKs on this vanilla GSI is not a supported compatibility-layer fallback.

To mark this phase successful would require matched Android 16 pins, a reproducible framework patch set, a passed compatibility self-test, and real emulator screenshots/logs showing the store and Play Services installation as unprivileged apps. None is currently available.
