#!/usr/bin/env python3
"""
dump_kernel.py - Извлечение незашифрованного ядра ARM64 Linux и сборка boot.img
для Яндекс Станции Лайт 2 (plum, Amlogic A113X).
"""

import mmap
import os
import gzip
import struct
import hashlib

KERNEL_PHYS = 0x01080000
PAGE_SIZE = 2048

def dump_kernel_from_mem(out_image_path):
    print(f"[*] Чтение /dev/mem со смещения 0x{KERNEL_PHYS:08x}...")
    fd = os.open('/dev/mem', os.O_RDONLY | os.O_SYNC)
    # Сначала читаем заголовок (4KB)
    m_hdr = mmap.mmap(fd, 4096, mmap.MAP_SHARED, mmap.PROT_READ, offset=KERNEL_PHYS)
    hdr = m_hdr[:64]
    if hdr[0x38:0x3c] != b'ARMd':
        m_hdr.close()
        os.close(fd)
        raise ValueError(f"Сигнатура ядра ARMd не найдена! Прочитано: {hdr[0x38:0x3c]}")
    
    text_offset, image_size = struct.unpack_from('<QQ', hdr, 8)
    print(f"[+] Найдено ядро Linux ARM64! Размер: {image_size} байт (0x{image_size:x})")
    m_hdr.close()

    # Считываем полный образ ядра
    m = mmap.mmap(fd, image_size, mmap.MAP_SHARED, mmap.PROT_READ, offset=KERNEL_PHYS)
    raw_kernel = m[:image_size]
    m.close()
    os.close(fd)

    with open(out_image_path, 'wb') as f:
        f.write(raw_kernel)
    print(f"[+] Несжатое ядро сохранено: {out_image_path} ({len(raw_kernel)} байт)")
    return raw_kernel

def pack_android_boot(kernel_bytes, dtb_bytes, out_path, gzip_kernel=True):
    if gzip_kernel:
        print("[*] Сжатие ядра gzip (уровень 9)...")
        kernel_data = gzip.compress(kernel_bytes, compresslevel=9)
    else:
        kernel_data = kernel_bytes

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
    cmdline = b'ubi.mtd=system root=ubi0:rootfs rootfstype=ubifs ubi.mtd=bkupgrade console=ttyS0,115200 no_console_suspend printk_no_block'

    # SHA1 ID
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
    kernel_raw = dump_kernel_from_mem('/tmp/Image')
    dtb_data = b''
    if os.path.exists('/tmp/plum-fdt.dtb'):
        with open('/tmp/plum-fdt.dtb', 'rb') as f:
            dtb_data = f.read()
    pack_android_boot(kernel_raw, dtb_data, '/tmp/boot_decrypted.img', gzip_kernel=True)
