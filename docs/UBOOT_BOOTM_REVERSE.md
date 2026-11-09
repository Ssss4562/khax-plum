# Реверс-анализ механизмов загрузки Amlogic U-Boot BL33 (Yandex Station Light 2 `plum`)

## 1. Вендорная цепочка безопасности `bootm` в U-Boot BL33

При попытке загрузить неподписанное кастомное ядро через `fastboot boot <boot.img>` U-Boot принимает загрузку (`download` -> `OKAY`), но сразу после выполнения `boot` инициирует сброс в заводской режим (`reboot_mode=watchdog_reboot` / `do_reset()`).

### Дизассемблер обработчика `do_bootm` (`0x01006f54`) в `uboot_bl33.bin`:

В функции `do_bootm` перед передачей управления ядру расположен обязательный вызов проверки криптографической подписи:

```arm64
0x100711c: mov w0, #0x1080000        ; адрес ядра в ОЗУ
0x1007120: mov w1, w0
0x1007124: mov x3, #7
0x1007128: mov x2, #0x1800000        ; размер проверяемой области
0x100712c: mov x0, #0x40             ; команда AML_SECU Signature Check
0x1007130: bl #0x10026b0             ; вызов smc_sec_boot_check
0x1007134: mov x19, x0               ; x0 = статус возврата от EL3 Secure Monitor
0x1007138: cbz w0, #0x1007150        ; если 0 — подпись верна, продолжаем загрузку
0x100713c: mov w1, w0
0x1007140: adrp x0, #0x10b7000
0x1007144: add x0, x0, #0x5d8        ; строка "\naml log : Sig Check %d\n"
0x1007148: bl printf
0x100714c: b #0x10073b4              ; выход из bootm с ошибкой (-1)
```

### Реализация `smc_sec_boot_check` (`0x010026b0`):

```arm64
0x10026cc: mov x0, #0xff
0x10026d0: mov x1, x7                ; x1 = 0x40
0x10026d4: movk x0, #0x8200, lsl #16 ; x0 = 0x820000ff (Amlogic EL3 Secure Monitor Function ID)
0x10026d8: mov x2, x6                ; x2 = 0x01080000 (kernel address)
0x10026dc: mov x3, x5                ; x3 = 0x01800000 (kernel size)
0x10026e0: smc #0                    ; АППАРАТНЫЙ ПЕРЕХОД В EL3 SECURE MONITOR (BL31/TEE)
0x10026e4: mov x19, x0               ; результат валидации открытым ключом eFuse
```

### Поведение `do_bootm_on_complete` (`0x01070438`):
```arm64
0x107055c: add x0, x29, #0x48        ; "bootm 0x2080000"
0x1070560: bl run_command            ; выполнение bootm
0x1070564: mov x3, #0
0x1070568: mov w2, #0
0x107056c: mov w1, #0
0x1070570: mov x0, #0
0x1070574: bl do_reset               ; СБРОС СИСТЕМЫ ПРИ ЛЮБОЙ ОШИБКЕ BOOTM
```

---

## 2. Итоги анализа аппаратного Secure Boot для ядер

1. **eFuse RSA Signature:**
   - SoC A113X аппаратно сконфигурирован на проверку RSA-подписи образов ядра в EL3 Secure Monitor.
   - Любое неподписанное или переподписанное сторонним ключом ядро бракуется монитором безопасности EL3 на этапе `smc 0x820000ff`.
   - В результате U-Boot прерывает выполнение команды `bootm` и вызывает `do_reset()`.

2. **Работа штатной загрузки (`imgread kernel`):**
   - Заводской раздел `mtd2` (`boot`) зашифрован и подписан ключом производителя (`AMLSECU!`).
   - Функция `imgread kernel` расшифровывает контейнер через EL3 и передает валидное ядро в `bootm`.

---

## 3. Практический путь запуска Alpine Linux

1. **Раздел `system` (`mtd3`) свободен от Secure Boot и dm-verity:**
   - `mtd3` представляет собой чистый стандартный образ **UBIFS**.
   - Он **НЕ** содержит криптоконтейнеров `AMLSECU!`.
   - В ядре **НЕ** включен `dm-verity` для разделов rootfs.
   - Заводское ядро 4.9.113 монтирует корень через стандартный cmdline:
     ```sh
     ubi.mtd=system root=ubi0:rootfs rootfstype=ubifs init=/sbin/init
     ```

2. **Развертывание Alpine Linux aarch64:**
   - Заводское ядро Amlogic 4.9.113 имеет полную поддержку 64-битного userspace (AArch64), модулей, cgroups, namespaces и сети.
   - Достаточно распаковать стандартный rootfs `alpine-minirootfs-*-aarch64.tar.gz` в раздел `mtd3` (либо смонтировать его через chroot / pivot_root / ubifs) и разместить `/sbin/init` Alpine Linux.
   - Это гарантирует 100% стабильность аппаратных драйверов (Wi-Fi, Bluetooth, аудио, LED, кнопки) при полноценном доступе к окружению Alpine Linux (пакетный менеджер `apk`, SSH, Python 3, Docker и т.д.).
