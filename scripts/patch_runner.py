#!/usr/bin/env python3
"""
HyperOS Patcher Repository - Main CLI Runner
Orchestrates disassembly, smali bytecode patching, DEX reassembly,
Magisk/KernelSU module packaging, and ROM bake preparation.
"""

import os
import sys
import shutil
import argparse
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

from tool_resolver import resolve_tools
from dex_utils import (
    disassemble_dex,
    assemble_smali,
    extract_dex_from_archive,
    update_zip_with_python,
    fix_dex_integrity
)
from patch_floating_windows import (
    patch_services_floating_windows,
    patch_framework_floating_windows
)
from patch_enhanced_keyboard import (
    patch_ime_injector,
    replace_baidu_in_smali_tree,
    patch_build_props,
    patch_cust_prop_white_keys
)
from package_modules import (
    build_floating_windows_module,
    build_enhanced_keyboard_module,
    prepare_bake_files
)


def find_file_in_dir(search_dir, target_names):
    """
    Localiza um arquivo por nome dentro de um diretório (recursivo ou na raiz).
    target_names pode ser string ou lista de strings.
    """
    if isinstance(target_names, str):
        target_names = [target_names]

    if not os.path.exists(search_dir):
        return None

    # Verifica primeiro na raiz
    for t in target_names:
        direct = os.path.join(search_dir, t)
        if os.path.isfile(direct):
            return os.path.abspath(direct)

    # Procura recursivamente
    for root, _, files in os.walk(search_dir):
        for f in files:
            if f in target_names:
                return os.path.abspath(os.path.join(root, f))
    return None


def run_patcher(args):
    start_time = time.time()
    print("=" * 72)
    print(" HyperOS Patcher Engine - Execução Modular Autônoma")
    print("=" * 72)

    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir)
    work_dir = os.path.abspath(args.work_dir)
    tools_dir = os.path.abspath(args.tools_dir)

    print(f"[*] Repositório Raiz : {REPO_ROOT}")
    print(f"[*] Diretório Input  : {input_dir}")
    print(f"[*] Diretório Output : {output_dir}")
    print(f"[*] Diretório Work   : {work_dir}")
    print(f"[*] Mod Selecionado  : {args.mod}")
    print(f"[*] Target API Smali : {args.api}")

    # 1. Resolução de ferramentas
    print("\n[+] 1. Verificando ferramentas (Smali / Baksmali)...")
    smali_jar, baksmali_jar = resolve_tools(
        tools_dir=tools_dir,
        explicit_smali=args.smali_jar,
        explicit_baksmali=args.baksmali_jar,
        auto_download=args.auto_download
    )
    print(f"    - Smali Jar   : {smali_jar}")
    print(f"    - Baksmali Jar: {baksmali_jar}")

    # 2. Localização dos arquivos de entrada
    print("\n[+] 2. Localizando arquivos de entrada...")
    services_jar = args.services_jar or find_file_in_dir(input_dir, "miui-services.jar")
    framework_jar = args.framework_jar or find_file_in_dir(input_dir, "miui-framework.jar")
    phrase_apk = args.phrase_apk or find_file_in_dir(input_dir, "MIUIFrequentPhrase.apk")
    build_prop = args.build_prop or find_file_in_dir(input_dir, ["build.prop", "system.build.prop", "etc.build.prop"])
    white_keys = args.white_keys or find_file_in_dir(input_dir, "cust_prop_white_keys_list")

    print(f"    - miui-services.jar     : {services_jar or '[NÃO ENCONTRADO]'}")
    print(f"    - miui-framework.jar    : {framework_jar or '[NÃO ENCONTRADO]'}")
    print(f"    - MIUIFrequentPhrase.apk: {phrase_apk or '[NÃO ENCONTRADO]'}")
    print(f"    - build.prop            : {build_prop or '[NÃO ENCONTRADO]'}")
    print(f"    - cust_prop_white_keys  : {white_keys or '[NÃO ENCONTRADO]'}")

    do_floating = args.mod in ["all", "floating-windows"]
    do_keyboard = args.mod in ["all", "enhanced-keyboard"]

    # Validações mínimas dependendo do mod
    if do_floating and not services_jar:
        print("[!] AVISO: 'miui-services.jar' não foi localizado em input/. O mod Floating Windows necessita deste arquivo.")
    if do_keyboard and not phrase_apk and not framework_jar:
        print("[!] AVISO: 'miui-framework.jar' ou 'MIUIFrequentPhrase.apk' não localizados para Enhanced Keyboard.")

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(work_dir, exist_ok=True)

    patched_services_jar = None
    patched_framework_jar = None
    patched_phrase_apk = None
    patched_build_prop = None
    patched_white_keys = None

    # 3. Processamento de miui-services.jar (Floating Windows)
    if services_jar and (do_floating or do_keyboard):
        print("\n[+] 3. Processando 'miui-services.jar'...")
        services_work = os.path.join(work_dir, "services")
        extracted_dex = extract_dex_from_archive(services_jar, services_work, ["classes.dex"])[0]
        services_smali = os.path.join(services_work, "smali")
        disassemble_dex(extracted_dex, services_smali, baksmali_jar=baksmali_jar)

        if do_floating:
            patch_services_floating_windows(services_smali, max_windows=args.max_windows)

        patched_dex = os.path.join(services_work, "patched_classes.dex")
        assemble_smali(services_smali, patched_dex, api=args.api, smali_jar=smali_jar)

        patched_services_jar = os.path.join(output_dir, "miui-services.jar")
        update_zip_with_python(services_jar, patched_services_jar, {"classes.dex": patched_dex})
        print(f"[+] 'miui-services.jar' patcheado com sucesso -> {patched_services_jar}")

    # 4. Processamento de miui-framework.jar (Floating Windows & Enhanced Keyboard)
    if framework_jar and (do_floating or do_keyboard):
        print("\n[+] 4. Processando 'miui-framework.jar'...")
        framework_work = os.path.join(work_dir, "framework")
        extracted_dex = extract_dex_from_archive(framework_jar, framework_work, ["classes.dex"])[0]
        framework_smali = os.path.join(framework_work, "smali")
        disassemble_dex(extracted_dex, framework_smali, baksmali_jar=baksmali_jar)

        if do_floating:
            patch_framework_floating_windows(framework_smali)

        if do_keyboard:
            patch_ime_injector(framework_smali)

        patched_dex = os.path.join(framework_work, "patched_classes.dex")
        assemble_smali(framework_smali, patched_dex, api=args.api, smali_jar=smali_jar)

        patched_framework_jar = os.path.join(output_dir, "miui-framework.jar")
        update_zip_with_python(framework_jar, patched_framework_jar, {"classes.dex": patched_dex})
        print(f"[+] 'miui-framework.jar' patcheado com sucesso -> {patched_framework_jar}")

    # 5. Processamento de MIUIFrequentPhrase.apk (Enhanced Keyboard)
    if phrase_apk and do_keyboard:
        print("\n[+] 5. Processando 'MIUIFrequentPhrase.apk'...")
        phrase_work = os.path.join(work_dir, "phrase")
        extracted_dex = extract_dex_from_archive(phrase_apk, phrase_work, ["classes.dex"])[0]
        phrase_smali = os.path.join(phrase_work, "smali")
        disassemble_dex(extracted_dex, phrase_smali, baksmali_jar=baksmali_jar)

        replace_baidu_in_smali_tree(phrase_smali)

        patched_dex = os.path.join(phrase_work, "patched_classes.dex")
        assemble_smali(phrase_smali, patched_dex, api=args.api, smali_jar=smali_jar)

        patched_phrase_apk = os.path.join(output_dir, "MIUIFrequentPhrase.apk")
        update_zip_with_python(phrase_apk, patched_phrase_apk, {"classes.dex": patched_dex})
        print(f"[+] 'MIUIFrequentPhrase.apk' patcheado com sucesso -> {patched_phrase_apk}")

    # 6. Propriedades e Whitelist (Enhanced Keyboard)
    if do_keyboard:
        print("\n[+] 6. Configurando propriedades de sistema e whitelist...")
        props_out = os.path.join(output_dir, "props")
        os.makedirs(props_out, exist_ok=True)

        patched_build_prop = os.path.join(props_out, "build.prop")
        if build_prop and os.path.exists(build_prop):
            shutil.copy2(build_prop, patched_build_prop)
        patch_build_props(patched_build_prop)

        patched_white_keys = os.path.join(props_out, "cust_prop_white_keys_list")
        if white_keys and os.path.exists(white_keys):
            shutil.copy2(white_keys, patched_white_keys)
        patch_cust_prop_white_keys(patched_white_keys)

    # 7. Empacotamento de Módulos Magisk / KernelSU / APatch
    if not args.skip_magisk:
        print("\n[+] 7. Gerando pacotes de módulos Magisk / KernelSU...")
        modules_out = os.path.join(output_dir, "modules")
        os.makedirs(modules_out, exist_ok=True)

        if do_floating and patched_services_jar:
            fw_zip = os.path.join(modules_out, "HyperOS_Floating_Windows_Magisk.zip")
            build_floating_windows_module(patched_services_jar, fw_zip, work_dir)

        if do_keyboard:
            kb_zip = os.path.join(modules_out, "HyperOS_Enhanced_Keyboard_Magisk.zip")
            build_enhanced_keyboard_module(
                patched_framework_jar=patched_framework_jar,
                patched_services_jar=patched_services_jar,
                patched_apk=patched_phrase_apk,
                patched_white_keys=patched_white_keys,
                out_zip_path=kb_zip,
                work_dir=work_dir
            )

    # 8. Estrutura pronta para Bake na ROM
    if not args.skip_bake:
        print("\n[+] 8. Gerando estrutura de arquivos pronta para bake na ROM...")
        bake_out = os.path.join(output_dir, "bake_files")

        mappings = [
            ("system_ext/framework/miui-services.jar", services_jar, patched_services_jar),
            ("system/framework/miui-services.jar", services_jar, patched_services_jar),
            ("system_ext/framework/miui-framework.jar", framework_jar, patched_framework_jar),
            ("system/framework/miui-framework.jar", framework_jar, patched_framework_jar),
            ("product/app/MIUIFrequentPhrase/MIUIFrequentPhrase.apk", phrase_apk, patched_phrase_apk),
            ("system_ext/priv-app/MIUIFrequentPhrase/MIUIFrequentPhrase.apk", phrase_apk, patched_phrase_apk),
            ("system/build.prop", build_prop, patched_build_prop),
            ("system_ext/etc/build.prop", build_prop, patched_build_prop),
            ("system_ext/etc/cust_prop_white_keys_list", white_keys, patched_white_keys),
        ]
        prepare_bake_files(bake_out, mappings)

    elapsed = time.time() - start_time
    print("\n" + "=" * 72)
    print(f" EXECUÇÃO CONCLUÍDA EM {elapsed:.2f}s")
    print(f" Saídas disponíveis em: {output_dir}")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(
        description="HyperOS Patcher Engine - Automação de Patches Smali, Módulos Magisk e ROM Bake"
    )
    parser.add_argument("--input-dir", "-i", default=os.path.join(REPO_ROOT, "input"),
                        help="Diretório contendo os arquivos originais (padrão: ./input)")
    parser.add_argument("--output-dir", "-o", default=os.path.join(REPO_ROOT, "output"),
                        help="Diretório para salvar os artefatos compilados (padrão: ./output)")
    parser.add_argument("--work-dir", "-w", default=os.path.join(REPO_ROOT, "build", "work"),
                        help="Diretório de trabalho temporário para descompressão Smali (padrão: ./build/work)")
    parser.add_argument("--tools-dir", "-t", default=os.path.join(REPO_ROOT, "tools"),
                        help="Diretório com smali.jar e baksmali.jar (padrão: ./tools)")
    parser.add_argument("--smali-jar", help="Caminho explícito para smali.jar")
    parser.add_argument("--baksmali-jar", help="Caminho explícito para baksmali.jar")
    parser.add_argument("--auto-download", action="store_true",
                        help="Baixa smali.jar e baksmali.jar automaticamente caso não encontrados")
    parser.add_argument("--api", type=int, default=34,
                        help="Target API para o smali assembler (padrão: 34)")
    parser.add_argument("--mod", choices=["all", "floating-windows", "enhanced-keyboard"], default="all",
                        help="Escolha de quais modificações aplicar (padrão: all)")
    parser.add_argument("--max-windows", type=int, default=6,
                        help="Quantidade máxima de janelas flutuantes ativas simultâneas (padrão: 6)")
    parser.add_argument("--skip-magisk", action="store_true",
                        help="Não gera os arquivos .zip de módulos Magisk/KernelSU")
    parser.add_argument("--skip-bake", action="store_true",
                        help="Não gera a pasta bake_files/ estruturada")

    # Substituições explícitas de arquivos individuais
    parser.add_argument("--services-jar", help="Caminho direto para miui-services.jar")
    parser.add_argument("--framework-jar", help="Caminho direto para miui-framework.jar")
    parser.add_argument("--phrase-apk", help="Caminho direto para MIUIFrequentPhrase.apk")
    parser.add_argument("--build-prop", help="Caminho direto para build.prop")
    parser.add_argument("--white-keys", help="Caminho direto para cust_prop_white_keys_list")

    args = parser.parse_args()
    run_patcher(args)


if __name__ == "__main__":
    main()
