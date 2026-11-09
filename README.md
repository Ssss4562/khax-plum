# khax-plum — SMC/EL3 bridge модуль для Яндекс Станции Лайт 2 (plum, A113X)

Mодуль ядра, открывающий из Linux вызовы SMC в EL3 (BL31) через debugfs-ноду
`/sys/kernel/debug/hax/smc`. Нужен для тёплого рестарта в U-Boot fastboot
(PSCI SYSTEM_RESET reason=4) и прочих EL3-экспериментов.

Формат записи в ноду: до четырёх hex-аргументов — `arg0 arg1 arg2 arg3` (`sscanf "%llx %llx %llx %llx"`).

## Пример: вход в fastboot

    echo "84000009 4" > /sys/kernel/debug/hax/smc

- `0x84000009` — PSCI SYSTEM_RESET (SMC32)
- `4` — reason ("fastboot")

Подробный гайд: см. репозиторий/гайд «Яндекс Станция Лайт 2 — fastboot и bootchain» (fastboot-community-guide).

## Сборка

    make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KERNEL=<путь к дереву ядра устройства> modules

## Параметры insmod (важно!)

`kmalloc`, `kfree`, `flush_dcache_area` — адреса символов ядра, зависят от сборки:

    cat /proc/kallsyms | grep -E " (kmalloc|kfree|flush_dcache_area)$"

Для сток-прошивки 01.01.261021.115427:

    insmod khax.ko kmalloc=0xffffff8009196f98 kfree=0xffffff8009197f58 \
           flush_dcache_area=0xffffff8009099140 sonos_blob_encdec=0

## Дисклеймер

Только для собственных устройств, на свой страх и риск. Сломаешь — разборка/USB Burning Tool.
