#!/usr/bin/env python3
"""
pack_boot.py - Сборка Android boot.img (v0) для Яндекс Станции Лайт 2 (plum, Amlogic A113X).
Формат совместим с Carliv Image Kitchen, unpackbootimg и abootimg.
"""

import os
import sys
import struct
import hashlib

PAGE_SIZE = 2048

def pack_boot(kernel_path, dtb_path, out_path, cmdline=None):
    if not os.path.exists(kernel_path):
        print(f"[-] Файл ядра не найден: {kernel_path}")
        sys.exit(1)

    with open(kernel_path, 'rb') as f:
        kernel_data = f.read()

    dtb_bytes = b''
    if dtb_path and os.path.exists(dtb_path):
        with open(dtb_path, 'rb') as f:
            dtb_bytes = f.read()

    k_sz = len(kernel_data)
    k_addr = 0x01080000
    rd_sz = 0
    rd_addr = 0x00000000
    sec_sz = 0
    sec_addr = 0x00000000
    tags_addr = 0x01000000
    dt_sz = len(dtb_bytes) if dtb_bytes else 0
    os_ver = 0
    name = b''

    if cmdline is None:
        cmdline = b'ubi.mtd=system root=ubi0:rootfs rootfstype=ubifs ubi.mtd=bkupgrade console=ttyS0,115200 no_console_suspend printk_no_block'
    elif isinstance(cmdline, str):
        cmdline = cmdline.encode('latin1')

    # Расчет SHA1 ID
    h = hashlib.sha1()
    h.update(kernel_data)
    h.update(struct.pack('<I', k_sz))
    h.update(b'')
    h.update(struct.pack('<I', rd_sz))
    h.update(b'')
    h.update(struct.pack('<I', sec_sz))
    if dtb_bytes:
        h.update(dtb_bytes)
        h.update(struct.pack('<I', dt_sz))
    img_id = h.digest() + b'\x00' * (32 - len(h.digest()))

    hdr = bytearray(PAGE_SIZE)
    struct.pack_into('<8sIIIIIIIIII', hdr, 0,
                     b'ANDROID!', k_sz, k_addr, rd_sz, rd_addr, sec_sz, sec_addr, tags_addr, PAGE_SIZE, dt_sz, os_ver)
    hdr[48:48+len(name)] = name
    hdr[64:64+len(cmdline)] = cmdline
    hdr[576:576+len(img_id)] = img_id

    def pad(d):
        rem = len(d) % PAGE_SIZE
        return d if rem == 0 else d + b'\x00' * (PAGE_SIZE - rem)

    with open(out_path, 'wb') as f:
        f.write(hdr)
        f.write(pad(kernel_data))
        if dtb_bytes:
            f.write(pad(dtb_bytes))

    print(f"[+] Сформирован Android boot.img: {out_path} ({os.path.getsize(out_path)} байт)")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Использование: pack_boot.py <Image[.gz]> <dtb> [out_boot.img]")
        sys.exit(1)
    k_path = sys.argv[1]
    d_path = sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else 'boot_custom.img'
    pack_boot(k_path, d_path, out)
