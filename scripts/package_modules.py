#!/usr/bin/env python3
"""
Packager for Magisk / KernelSU / APatch flashable zip modules
and ROM bake file structures.
"""

import os
import shutil
import zipfile

UPDATE_BINARY_SHELL = """#!/sbin/sh
######################################################
# Magisk / KernelSU / APatch Universal Installer
######################################################
OUTFD=$2
ZIPFILE=$3

if ! echo "$OUTFD" | grep -q '^[0-9]\\+$'; then
    for arg in "$@"; do
        if echo "$arg" | grep -q '\\.zip$'; then
            ZIPFILE="$arg"
            break
        fi
    done
fi

ui_print() {
    echo "$1"
}

MODID=""
for line in $(cat "$ZIPFILE" 2>/dev/null | unzip -p "$ZIPFILE" module.prop 2>/dev/null); do
    case "$line" in
        id=*) MODID="${line#id=}" ;;
    esac
done

[ -z "$MODID" ] && MODID="hyperos_custom_mod"

if [ -d "/data/adb/modules" ]; then
    MODPATH="/data/adb/modules/$MODID"
elif [ -d "/data/adb/modules_update" ]; then
    MODPATH="/data/adb/modules_update/$MODID"
else
    MODPATH="/data/adb/modules/$MODID"
fi

rm -rf "$MODPATH"
mkdir -p "$MODPATH"

ui_print "***************************************************"
ui_print "*        HyperOS Mod Installer (Universal)        *"
ui_print "***************************************************"
ui_print "- Extraindo arquivos do modulo ($MODID)..."
unzip -o "$ZIPFILE" -x 'META-INF/*' -d "$MODPATH" >/dev/null 2>&1

ui_print "- Aplicando permissoes do sistema..."
chmod 755 "$MODPATH"
if [ -d "$MODPATH/system" ]; then
    find "$MODPATH/system" -type d -exec chmod 755 {} +
    find "$MODPATH/system" -type f -exec chmod 644 {} +
fi

if [ -f "$MODPATH/post-fs-data.sh" ]; then
    chmod 755 "$MODPATH/post-fs-data.sh"
fi

if [ -f "$MODPATH/service.sh" ]; then
    chmod 755 "$MODPATH/service.sh"
fi

chown -R 0:0 "$MODPATH"
rm -f "$MODPATH/disable"
touch "$MODPATH/auto_mount"

ui_print "- Modulo instalado com sucesso!"
ui_print "- Reinicie o dispositivo para ativar as alteracoes."
exit 0
"""

UPDATER_SCRIPT_DUMMY = "#MAGISK\n"

CUSTOMIZE_SH_CONTENT = """ui_print "- Configurando permissoes..."
set_perm_recursive $MODPATH 0 0 0755 0644
if [ -f "$MODPATH/post-fs-data.sh" ]; then
    set_perm $MODPATH/post-fs-data.sh 0 0 0755
fi
"""

POST_FS_DATA_CONTENT = """#!/system/bin/sh
MODDIR=${0%/*}

# Limpeza preventiva de caches Dalvik/ART para forcar reotimizacao limpa sem bootloop
rm -rf /data/dalvik-cache/*/*MIUIFrequentPhrase*
rm -rf /data/dalvik-cache/*/*miui-framework*
rm -rf /data/dalvik-cache/*/*miui-services*
rm -rf /data/system/package_cache/*
"""


def create_zip_from_dir(src_dir, out_zip_path):
    os.makedirs(os.path.dirname(os.path.abspath(out_zip_path)), exist_ok=True)
    with zipfile.ZipFile(out_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                abs_f = os.path.join(root, file)
                rel_f = os.path.relpath(abs_f, src_dir).replace("\\", "/")
                z.write(abs_f, rel_f)
    print(f"[package] Gerado módulo: {out_zip_path} ({os.path.getsize(out_zip_path)} bytes)")


def build_floating_windows_module(patched_services_jar, out_zip_path, work_dir):
    """
    Empacota o módulo Magisk isolado para Floating Windows.
    """
    stage_dir = os.path.join(work_dir, "stage_floating_windows")
    if os.path.exists(stage_dir):
        shutil.rmtree(stage_dir)
    os.makedirs(stage_dir, exist_ok=True)

    # META-INF
    meta_dir = os.path.join(stage_dir, "META-INF", "com", "google", "android")
    os.makedirs(meta_dir, exist_ok=True)
    with open(os.path.join(meta_dir, "update-binary"), "w", encoding="utf-8", newline="\n") as f:
        f.write(UPDATE_BINARY_SHELL)
    with open(os.path.join(meta_dir, "updater-script"), "w", encoding="utf-8", newline="\n") as f:
        f.write(UPDATER_SCRIPT_DUMMY)

    # customize.sh
    with open(os.path.join(stage_dir, "customize.sh"), "w", encoding="utf-8", newline="\n") as f:
        f.write(CUSTOMIZE_SH_CONTENT)

    # module.prop
    prop_content = """id=hyperos_floating_windows
name=HyperOS Floating Windows Unlocker (6 Stacks)
version=v1.0
versionCode=10
author=Antigravity
description=Desbloqueia ate 6 janelas flutuantes ativas simultaneas e neutraliza a blacklist de freeform no HyperOS.
"""
    with open(os.path.join(stage_dir, "module.prop"), "w", encoding="utf-8", newline="\n") as f:
        f.write(prop_content)

    # system.prop
    with open(os.path.join(stage_dir, "system.prop"), "wb") as f:
        f.write(b"")

    # Injeta miui-services.jar em system_ext/framework e system/framework
    dest_se = os.path.join(stage_dir, "system", "system_ext", "framework")
    dest_s = os.path.join(stage_dir, "system", "framework")
    os.makedirs(dest_se, exist_ok=True)
    os.makedirs(dest_s, exist_ok=True)
    shutil.copy2(patched_services_jar, os.path.join(dest_se, "miui-services.jar"))
    shutil.copy2(patched_services_jar, os.path.join(dest_s, "miui-services.jar"))

    create_zip_from_dir(stage_dir, out_zip_path)


def build_enhanced_keyboard_module(
    patched_framework_jar,
    patched_services_jar,
    patched_apk,
    patched_white_keys,
    out_zip_path,
    work_dir
):
    """
    Empacota o módulo Magisk para Teclado Aprimorado (Gboard / SwiftKey).
    """
    stage_dir = os.path.join(work_dir, "stage_enhanced_keyboard")
    if os.path.exists(stage_dir):
        shutil.rmtree(stage_dir)
    os.makedirs(stage_dir, exist_ok=True)

    # META-INF
    meta_dir = os.path.join(stage_dir, "META-INF", "com", "google", "android")
    os.makedirs(meta_dir, exist_ok=True)
    with open(os.path.join(meta_dir, "update-binary"), "w", encoding="utf-8", newline="\n") as f:
        f.write(UPDATE_BINARY_SHELL)
    with open(os.path.join(meta_dir, "updater-script"), "w", encoding="utf-8", newline="\n") as f:
        f.write(UPDATER_SCRIPT_DUMMY)

    # customize.sh & post-fs-data.sh
    with open(os.path.join(stage_dir, "customize.sh"), "w", encoding="utf-8", newline="\n") as f:
        f.write(CUSTOMIZE_SH_CONTENT)
    with open(os.path.join(stage_dir, "post-fs-data.sh"), "w", encoding="utf-8", newline="\n") as f:
        f.write(POST_FS_DATA_CONTENT)

    # module.prop
    prop_content = """id=hyperos_enhanced_keyboard
name=HyperOS Enhanced Keyboard (Gboard / SwiftKey)
version=v2.0
versionCode=20
author=Antigravity
description=Desbloqueia a barra inferior (bottom bar) de atalhos e frases frequentes do MIUI/HyperOS para Gboard, SwiftKey e outros teclados.
"""
    with open(os.path.join(stage_dir, "module.prop"), "w", encoding="utf-8", newline="\n") as f:
        f.write(prop_content)

    # system.prop
    sys_prop = """ro.miui.support_miui_ime_bottom=1
persist.mdc_color_detection=1
"""
    with open(os.path.join(stage_dir, "system.prop"), "w", encoding="utf-8", newline="\n") as f:
        f.write(sys_prop)

    # JARs em system_ext/framework e system/framework
    if patched_framework_jar and os.path.exists(patched_framework_jar):
        dest_se_fw = os.path.join(stage_dir, "system", "system_ext", "framework")
        dest_s_fw = os.path.join(stage_dir, "system", "framework")
        os.makedirs(dest_se_fw, exist_ok=True)
        os.makedirs(dest_s_fw, exist_ok=True)
        shutil.copy2(patched_framework_jar, os.path.join(dest_se_fw, "miui-framework.jar"))
        shutil.copy2(patched_framework_jar, os.path.join(dest_s_fw, "miui-framework.jar"))

    if patched_services_jar and os.path.exists(patched_services_jar):
        dest_se_fw = os.path.join(stage_dir, "system", "system_ext", "framework")
        dest_s_fw = os.path.join(stage_dir, "system", "framework")
        os.makedirs(dest_se_fw, exist_ok=True)
        os.makedirs(dest_s_fw, exist_ok=True)
        shutil.copy2(patched_services_jar, os.path.join(dest_se_fw, "miui-services.jar"))
        shutil.copy2(patched_services_jar, os.path.join(dest_s_fw, "miui-services.jar"))

    # APK em system_ext/priv-app e product/app
    if patched_apk and os.path.exists(patched_apk):
        dest_apk1 = os.path.join(stage_dir, "system", "system_ext", "priv-app", "MIUIFrequentPhrase")
        dest_apk2 = os.path.join(stage_dir, "system", "product", "app", "MIUIFrequentPhrase")
        os.makedirs(dest_apk1, exist_ok=True)
        os.makedirs(dest_apk2, exist_ok=True)
        shutil.copy2(patched_apk, os.path.join(dest_apk1, "MIUIFrequentPhrase.apk"))
        shutil.copy2(patched_apk, os.path.join(dest_apk2, "MIUIFrequentPhrase.apk"))

    # cust_prop_white_keys_list em system_ext/etc
    if patched_white_keys and os.path.exists(patched_white_keys):
        dest_etc = os.path.join(stage_dir, "system", "system_ext", "etc")
        os.makedirs(dest_etc, exist_ok=True)
        shutil.copy2(patched_white_keys, os.path.join(dest_etc, "cust_prop_white_keys_list"))

    create_zip_from_dir(stage_dir, out_zip_path)


def prepare_bake_files(bake_out_dir, mappings, rom_target_dir=None):
    """
    Estrutura os arquivos prontos para bake na ROM:
    - mappings: lista de tuplas (rel_path, orig_file_path, patched_file_path)
    - Cria backups .bak ao lado dos arquivos caso orig_file_path seja fornecido.
    - Se rom_target_dir for especificado, aplica as cópias e .bak diretamente nessa pasta de ROM.
    """
    os.makedirs(bake_out_dir, exist_ok=True)

    for rel_path, orig_file, patched_file in mappings:
        if not patched_file or not os.path.exists(patched_file):
            continue

        # 1. Dentro de bake_out_dir
        dest_bake = os.path.join(bake_out_dir, rel_path)
        os.makedirs(os.path.dirname(dest_bake), exist_ok=True)
        if orig_file and os.path.exists(orig_file):
            shutil.copy2(orig_file, dest_bake + ".bak")
        shutil.copy2(patched_file, dest_bake)

        # 2. Opcional: dentro de rom_target_dir
        if rom_target_dir and os.path.exists(rom_target_dir):
            rom_dest = os.path.join(rom_target_dir, rel_path)
            os.makedirs(os.path.dirname(rom_dest), exist_ok=True)
            bak_file = rom_dest + ".bak"
            if orig_file and os.path.exists(orig_file) and not os.path.exists(bak_file):
                shutil.copy2(orig_file, bak_file)
            shutil.copy2(patched_file, rom_dest)
            print(f"[bake] ROM: {rel_path} atualizado (backup em {rel_path}.bak)")

    print(f"[bake] Arquivos de bake organizados com sucesso em '{bake_out_dir}'.")
