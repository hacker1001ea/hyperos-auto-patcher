#!/usr/bin/env python3
"""
DEX and Archive Utilities for Smali disassembly, assembly, header integrity fixes,
and clean archive repackaging.
"""

import os
import sys
import shutil
import struct
import hashlib
import zlib
import zipfile
import subprocess
from tool_resolver import resolve_tools


def fix_dex_integrity(dex_path, target_magic=b"dex\n039\x00"):
    """
    Garante o magic header esperado do DEX e recalcula os checksums Adler32 e SHA-1.
    """
    with open(dex_path, "rb") as f:
        data = bytearray(f.read())

    if len(data) < 112:
        raise ValueError(f"Arquivo DEX '{dex_path}' é muito pequeno: {len(data)} bytes")

    if target_magic and data[0:8] != target_magic:
        data[0:8] = target_magic

    # SHA-1 cobre do byte 32 até o final do arquivo
    sha1 = hashlib.sha1(data[32:]).digest()
    data[12:32] = sha1

    # Adler-32 cobre do byte 12 até o final do arquivo
    adler = zlib.adler32(data[12:]) & 0xFFFFFFFF
    struct.pack_into("<I", data, 8, adler)

    with open(dex_path, "wb") as f:
        f.write(data)

    print(f"[fix_dex_integrity] {os.path.basename(dex_path)}: Adler=0x{adler:08X} SHA1={sha1.hex()[:8]}")
    return adler, sha1.hex()


def disassemble_dex(dex_path, out_smali_dir, baksmali_jar=None):
    """
    Desmonta um arquivo DEX para código Smali legível usando baksmali.jar.
    """
    if not baksmali_jar:
        _, baksmali_jar = resolve_tools()

    if os.path.exists(out_smali_dir):
        shutil.rmtree(out_smali_dir)
    os.makedirs(out_smali_dir, exist_ok=True)

    cmd = ["java", "-jar", baksmali_jar, "d", dex_path, "-o", out_smali_dir]
    print(f"[baksmali] Desmontando {os.path.basename(dex_path)} -> {out_smali_dir}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Baksmali falhou em {dex_path}:\n{res.stderr}\n{res.stdout}")
    print(f"[baksmali] Desmontagem concluída com sucesso.")


def assemble_smali(smali_dir, out_dex_path, api=34, smali_jar=None):
    """
    Remonta uma pasta com código Smali em um arquivo DEX compilado usando smali.jar.
    Aplica validação e correção de integridade (Adler32/SHA-1).
    """
    if not smali_jar:
        smali_jar, _ = resolve_tools()

    os.makedirs(os.path.dirname(out_dex_path), exist_ok=True)
    cmd = ["java", "-jar", smali_jar, "a", "--api", str(api), smali_dir, "-o", out_dex_path]
    print(f"[smali] Remontando {smali_dir} -> {out_dex_path} (API {api})...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Smali falhou em {smali_dir}:\n{res.stderr}\n{res.stdout}")

    fix_dex_integrity(out_dex_path)
    print(f"[smali] Remontagem concluída. Tamanho final: {os.path.getsize(out_dex_path)} bytes.")


def extract_dex_from_archive(archive_path, out_dir, dex_names=None):
    """
    Extrai arquivos DEX especificados (ou todos classes*.dex) de um arquivo JAR ou APK.
    Retorna uma lista dos caminhos locais extraídos.
    """
    os.makedirs(out_dir, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(archive_path, "r") as z:
        for item in z.infolist():
            if dex_names:
                matches = item.filename in dex_names
            else:
                matches = item.filename.startswith("classes") and item.filename.endswith(".dex")
            if matches:
                target_path = os.path.join(out_dir, os.path.basename(item.filename))
                with z.open(item) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted.append(target_path)
                print(f"[archive] Extraído: {item.filename} ({os.path.getsize(target_path)} bytes)")
    if not extracted:
        raise FileNotFoundError(f"Nenhum arquivo DEX encontrado dentro de '{archive_path}'")
    return extracted


def update_zip_with_python(src_archive, dst_archive, replacements):
    """
    Copia src_archive para dst_archive substituindo entradas específicas sem quebrar
    o alinhamento do Android ou outros atributos do arquivo ZIP.
    replacements: dicionário { entry_name_in_zip: local_file_path }
    """
    os.makedirs(os.path.dirname(dst_archive), exist_ok=True)
    with zipfile.ZipFile(src_archive, "r") as zin:
        with zipfile.ZipFile(dst_archive, "w") as zout:
            replaced_set = set()
            for item in zin.infolist():
                if item.filename in replacements:
                    local_f = replacements[item.filename]
                    with open(local_f, "rb") as rf:
                        data = rf.read()
                    zout.writestr(item, data)
                    replaced_set.add(item.filename)
                else:
                    data = zin.read(item.filename)
                    zout.writestr(item, data)

            # Insere eventuais entradas novas que não existiam originalmente
            for name, local_f in replacements.items():
                if name not in replaced_set:
                    with open(local_f, "rb") as rf:
                        zout.writestr(name, rf.read(), compress_type=zipfile.ZIP_DEFLATED)

    print(f"[archive] Gerado '{dst_archive}' com substituições: {list(replacements.keys())}")
