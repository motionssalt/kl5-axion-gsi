# TECNO KL5 Dynamic Partition (`super`) Metadata & Layout Analysis

## 1. Physical Device & Super Metadata Overview
- **Partition:** `super`
- **First Sector:** 2048 (Offset `1,048,576` bytes / 1 MiB)
- **Super Total Size:** `8,589,934,592` bytes (exactly 8.00 GiB / 16,777,216 sectors of 512 bytes)
- **Metadata Version:** 10.2
- **Metadata Max Size:** 65,536 bytes
- **Metadata Slot Count:** 3
- **Header Flags:** None (Plain A/B dynamic partitions; **not** Virtual A/B snapshot)

---

## 2. Partition Group Table
Dynamic partitions on MT6768 TECNO KL5 are organized into slot-specific groups with hard upper bounds:

| Group Name | Maximum Size (Bytes) | Maximum Size (GiB) | Flags | Role |
| :--- | :--- | :--- | :--- | :--- |
| `default` | 0 bytes | 0 GiB | None | Default fallback group |
| `main_a` | 8,587,837,440 bytes | ~7.998 GiB | None | Dynamic group containing all slot A partitions |
| `main_b` | 8,587,837,440 bytes | ~7.998 GiB | None | Dynamic group containing all slot B partitions |

---

## 3. Stock Slot A Allocated Extents & Sizes
Stock firmware populates only slot A. The table below lists the exact linear extents allocated within the `super` block device:

| Partition Name | Group | Extents (Sectors) | Total Sectors | Size in Bytes | Size in MiB / GiB |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `product_a` | `main_a` | 2048 .. 3485336 | 3,483,288 | 1,783,443,456 B | 1.66 GiB (1,700.8 MiB) |
| `system_a` | `main_a` | 3485696 .. 5220992 | 1,735,296 | 888,471,552 B | 847.3 MiB |
| `system_ext_a` | `main_a` | 5222400 .. 9311256 | 4,088,856 | 2,093,494,272 B | 1.95 GiB (1,996.5 MiB) |
| `vendor_a` | `main_a` | 9312256 .. 10724208 | 1,411,952 | 722,919,424 B | 689.4 MiB |
| `tr_product_a` | `main_a` | 10725376 .. 10726056 | 680 | 348,160 B | 340 KiB |
| `tr_mi_a` | `main_a` | 10727424 .. 10742536 | 15,112 | 7,737,344 B | 7.38 MiB |
| `tr_theme_a` | `main_a` | 10743808 .. 10744488 | 680 | 348,160 B | 340 KiB |
| `tr_preload_a` | `main_a` | 10745856 .. 10746536 | 680 | 348,160 B | 340 KiB |
| `tr_region_a` | `main_a` | 10747904 .. 10748584 | 680 | 348,160 B | 340 KiB |
| `tr_company_a` | `main_a` | 10749952 .. 10750632 | 680 | 348,160 B | 340 KiB |
| `tr_carrier_a` | `main_a` | 10752000 .. 10752680 | 680 | 348,160 B | 340 KiB |
| **Total Slot A** | `main_a` | — | **10,738,584** | **5,498,155,008 B** | **~5.12 GiB** |

---

## 4. Slot B Analysis & Dynamic Partition Sizing
In stock firmware `super.img`:
- Every `*_b` partition is defined in group `main_b` with **0 extents** (unallocated).
- `main_b` has a total group capacity of **8,587,837,440 bytes (~8.00 GB)**.
- Flashing all 11 stock partitions to slot B requires:
  $$\sum \text{Stock Partitions} = 5,498,155,008 \text{ bytes} \approx 5.12 \text{ GiB}$$
- Remaining capacity in `main_b`:
  $$8,587,837,440 - 5,498,155,008 = 3,089,682,432 \text{ bytes} \approx 2.88 \text{ GiB free}$$
- **Conclusion:** All extracted stock images fit comfortably in `main_b`. In `fastbootd`, `fastboot flash <name>_b <image>` automatically resizes each logical partition within `main_b` to accommodate the image stream without exceeding group limits.
