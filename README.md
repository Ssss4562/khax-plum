# khax-plum — SMC/EL3 bridge модуль для Яндекс Станции Лайт 2 (plum, A113X)

Модуль ядра, открывающий из Linux вызовы SMC в EL3 (BL31) через debugfs-ноду
`/sys/kernel/debug/hax/smc`. Нужен для тёплого рестарта в U-Boot fastboot
(PSCI SYSTEM_RESET reason=4), извлечения криптоконтейнеров и прочих EL3-экспериментов.

Формат записи в ноду: до четырёх hex-аргументов — `arg0 arg1 arg2 arg3` (`sscanf "%llx %llx %llx %llx"`).

## Пример: вход в fastboot

```sh
echo "84000009 4" > /sys/kernel/debug/hax/smc
```

- `0x84000009` — PSCI SYSTEM_RESET (SMC32)
- `4` — reason ("fastboot")

Подробный гайд: см. репозиторий/гайд «Яндекс Станция Лайт 2 — fastboot и bootchain» (fastboot-community-guide).

## Дамп чистого незашифрованного ядра (mtd2) для Carliv Image Kitchen

Раздел `mtd2` (`boot`) на флешке запакован в Amlogic Secure Boot Container (`AMLSECU!`) и зашифрован RSA-1024 + AES-CBC.
Однако, поскольку Secure OS (BL32) расшифровывает ядро при старте, в работающей системе по физическому адресу `0x01080000` в DRAM находится **чистый, полностью расшифрованный ARM64 Linux Image**.

Скрипт `tools/dump_kernel.py` считывает ядро напрямую через `/dev/mem` и упаковывает его в стандартный Android `boot.img`:

```sh
# Запуск на устройстве:
python3 tools/dump_kernel.py
```

Результат:
- `/tmp/Image` — сырой исполняемый бинарник ядра Linux ARM64 (`ARMd`, ~14.3 MB).
- `/tmp/boot_decrypted.img` — стандартный Android `boot.img` v0 (с gzip-ядром и встроенным DTB), полностью совместимый с **Carliv Image Kitchen**, `unpackbootimg` и `abootimg`.

## Реверс-инжиниринг U-Boot Fastboot unlock (`check_lock`)

В U-Boot 2015 команды Fastboot (`flash`, `erase`, `getvar unlocked`) управляются функцией `check_lock` (`0x0106ff14`):
* Функция проверяет байты 4 и 5 переменной `lock`:
  * Если `lock[4] == '0'` и `lock[5] == '0'` (например, `lock=10100000`), функция возвращает `0` (**UNLOCKED**).
  * Fastboot рапортует `unlocked: yes` и снимает блокировку с команд `fastboot flash` и `fastboot erase` для разделов `boot`, `system`, `recovery`.
* **Защита eFuse:** eFuse-перемычки контролируют только начальный загрузчик (`mtd0`/`mtd1`) и команду `fastboot flashing unlock` (`FAILsecure boot device`). Прошивка разделов `mtd2` (`boot`) и `mtd3` (`system`) зависит исключительно от программного `check_lock`.

## Сборка модуля

```sh
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KERNEL=<путь к дереву ядра устройства> modules
```

## Параметры insmod (важно!)

`kmalloc`, `kfree`, `flush_dcache_area` — адреса символов ядра, зависят от сборки:

```sh
cat /proc/kallsyms | grep -E " (kmalloc|kfree|flush_dcache_area)$"
```

Для сток-прошивки 01.01.261021.115427:

```sh
insmod khax.ko kmalloc=0xffffff8009196f98 kfree=0xffffff8009197f58 \
       flush_dcache_area=0xffffff8009099140 sonos_blob_encdec=0
```

## Дисклеймер

Только для собственных устройств, на свой страх и риск.
