# Реверс-анализ механизмов загрузки Amlogic U-Boot (Yandex Station Light 2 `plum`)

## 1. Вендорный баг в реализации `fastboot boot`

При попытке загрузить ядро через `fastboot boot <boot.img>` U-Boot возвращает `OKAY`, но затем немедленно уходит в аппаратный Watchdog Reset (`reboot_mode=watchdog_reboot`).

### Анализ дизассемблера BL33 (`uboot_bl33.bin`):

Обработчик команды `boot` в fastboot-гаджете регистрирует completion callback `do_bootm_on_complete` (адрес `0x01070438`):

```arm64
0x1070464: adrp x23, #0x10db000
0x107053c: ldr x0, [x23, #0x908]   ; x0 = 0x01000000 (адрес по умолчанию переменной loadaddr)
0x1070540: mov x1, x21              ; x1 = 0x02080000 (адрес буфера USB загрузки fastboot)
0x1070544: mov w2, w20              ; w2 = размер загруженного образа
0x1070548: bl memcpy(0x01000000, 0x02080000, size)
0x1070554: bl flush_cache
0x1070560: bl run_command("bootm ...")
0x1070574: bl do_reset              ; сброс при ошибке bootm
```

### Причины краша:
1. **Коллизия адресов в ОЗУ (`0x01000000`):**
   - Переменная `0x10db908` (`loadaddr`) по умолчанию инициализируется значением `0x01000000`.
   - По этому же физическому адресу (`0x01000000`) размещен и исполняется код самого U-Boot BL33.
   - Стек и код функций U-Boot расположены в диапазоне `0x01000000`–`0x01075000`.
   - Функция `memcpy(0x01000000, 0x02080000, size)` копирует образ размером 6–14 МБ поверх выполняемого кода U-Boot, разрушая структуры загрузчика.

2. **Нехватка памяти кучи при сжатом ядре (`android_image_need_move`):**
   - Функция `android_image_need_move` (`0x0102b9d0`) при обнаружении сжатого ядра (gzip `\x1f\x8b`) вычисляет расстояние между `loadaddr` и `kernel_addr`.
   - Если расстояние < 32 МБ, U-Boot пытается переместить весь `boot.img` в кучу через `malloc(total_size)`.
   - В конфигурации с 256 МБ ОЗУ куча загрузчика (`CONFIG_SYS_MALLOC_LEN`) составляет менее 4 МБ. Для образа размером 5.9 МБ `malloc` возвращает `NULL` (`-ENOMEM`), приводя к аварийному вызову `do_reset()`.

---

## 2. Анализ штатной загрузки `imgread kernel`

В заводском `bootcmd`:
```sh
storeboot=setenv bootargs ${bootargs} ${initargs} otg_device=${otg_device}; if imgread kernel ${boot_part} ${loadaddr}; then bootm ${loadaddr}; fi;
```

Функция `imgread kernel` (`0x0101cec4`):
1. Вызывает SMC в EL3 Secure Monitor (`0x820000ff` / `0x82000042` / `0x82000043`):
   - Расшифровывает криптоконтейнер `AMLSECU!` с раздела `mtd2` (`boot`).
   - Проверяет цифровую подпись RSA в Secure OS (BL31/TEE).
2. Извлекает DTB и передает его ядру.
3. Передает управление распакованному ядру по адресу `0x01080000`.

---

## 3. Выводы по запуску кастомных систем (Alpine Linux)

1. **Раздел `system` (`mtd3`) свободен от Secure Boot:**
   - Представляет собой стандартный образ UBIFS.
   - Не содержит криптоконтейнеров `AMLSECU` и не защищен `dm-verity`.
   - Штатное ядро монтирует `root=ubi0:rootfs rootfstype=ubifs` и запускает `/sbin/init`.
   - Развертывание корневой файловой системы Alpine Linux (ARM64 aarch64) в `mtd3` возможно без вмешательства в Secure Boot.
