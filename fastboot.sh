#!/bin/sh
# Тёплый SMC-рестарт в fastboot (PSCI SYSTEM_RESET, reason=4).
# USB PHY остаётся в device-mode -> U-Boot fastboot-гаджет поднимается нормально.
K=/data/khax.ko
grep -q '^khax ' /proc/modules 2>/dev/null || \
  insmod "$K" kmalloc=0xffffff8009196f98 kfree=0xffffff8009197f58 \
           flush_dcache_area=0xffffff8009099140 sonos_blob_encdec=0 2>/dev/null
if [ ! -e /sys/kernel/debug/hax/smc ]; then
  echo "khax smc node missing" >&2
  exit 1
fi
echo "84000009 4" > /sys/kernel/debug/hax/smc
sleep 1
echo "fastboot reset issued"
