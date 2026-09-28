#!/usr/bin/env python3
"""
Patch module for HyperOS Enhanced Keyboard (Barra inferior e frases frequentes).
- Forces isImeSupport in InputMethodServiceInjector to always return true (1).
- Replaces proprietary Baidu IME packages (com.baidu.input_mi) with Gboard (com.google.android.inputmethod.latin).
- Configures required build.prop flags and whitelist entries.
"""

import os
import re


def patch_ime_injector(framework_smali_dir):
    """
    Patches InputMethodServiceInjector.smali:
    - isImeSupport(Landroid/content/Context;)Z -> return 1
    - Substitui referências a com.baidu.input_mi por com.google.android.inputmethod.latin
    """
    injector_smali = None
    for root, _, files in os.walk(framework_smali_dir):
        if "InputMethodServiceInjector.smali" in files:
            injector_smali = os.path.join(root, "InputMethodServiceInjector.smali")
            break

    if not injector_smali or not os.path.exists(injector_smali):
        raise FileNotFoundError("Não foi possível encontrar 'InputMethodServiceInjector.smali' em miui-framework.")

    with open(injector_smali, "r", encoding="utf-8") as f:
        content = f.read()

    p = re.compile(
        r"\.method private static blacklist isImeSupport\(Landroid/content/Context;\)Z.*?"
        r"\.end method",
        re.DOTALL
    )

    r = """.method private static blacklist isImeSupport(Landroid/content/Context;)Z
    .registers 2
    .param p0, "context"    # Landroid/content/Context;

    const/4 v0, 0x1

    return v0
.end method"""

    if "const/4 v0, 0x1\n\n    return v0" not in content:
        content, c = p.subn(r, content)
        if c != 1:
            raise RuntimeError(f"Esperada 1 correspondência para isImeSupport, encontradas {c}")
        print("[enhanced_keyboard] isImeSupport forçado para true (1) em InputMethodServiceInjector.smali.")
    else:
        print("[enhanced_keyboard] isImeSupport já se encontra desbloqueado.")

    if "com.baidu.input_mi" in content:
        content = content.replace("com.baidu.input_mi", "com.google.android.inputmethod.latin")
        print("[enhanced_keyboard] Referência a com.baidu.input_mi substituída por Gboard no injector.")

    with open(injector_smali, "w", encoding="utf-8") as f:
        f.write(content)


def replace_baidu_in_smali_tree(smali_dir, target_ime="com.google.android.inputmethod.latin"):
    """
    Substitui todas as ocorrências de 'com.baidu.input_mi' por target_ime (padrão Gboard)
    em todos os arquivos .smali na árvore informada.
    """
    total_files = 0
    total_replacements = 0
    for root, _, files in os.walk(smali_dir):
        for f in files:
            if f.endswith(".smali"):
                fp = os.path.join(root, f)
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    txt = fh.read()
                if "com.baidu.input_mi" in txt:
                    count = txt.count("com.baidu.input_mi")
                    txt = txt.replace("com.baidu.input_mi", target_ime)
                    with open(fp, "w", encoding="utf-8") as fh:
                        fh.write(txt)
                    total_files += 1
                    total_replacements += count
                    print(f"[enhanced_keyboard] Substituídas {count} ocorrência(s) em {f}")

    print(f"[enhanced_keyboard] Concluído: {total_replacements} substituição(ões) em {total_files} arquivo(s).")
    return total_replacements


def patch_build_props(prop_path, extra_props=None):
    """
    Adiciona ou atualiza propriedades essenciais no build.prop:
    ro.miui.support_miui_ime_bottom=1
    persist.mdc_color_detection=1
    """
    props_to_set = {
        "ro.miui.support_miui_ime_bottom": "1",
        "persist.mdc_color_detection": "1"
    }
    if extra_props:
        props_to_set.update(extra_props)

    lines = []
    if os.path.exists(prop_path):
        with open(prop_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [l.strip() for l in f.readlines()]

    updated_keys = set()
    new_lines = []
    for line in lines:
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            k = k.strip()
            if k in props_to_set:
                new_lines.append(f"{k}={props_to_set[k]}")
                updated_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in props_to_set.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}")

    os.makedirs(os.path.dirname(os.path.abspath(prop_path)), exist_ok=True)
    with open(prop_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")
    print(f"[enhanced_keyboard] Propriedades atualizadas em {prop_path}")


def patch_cust_prop_white_keys(cust_keys_path, extra_keys=None):
    """
    Garante que as propriedades necessárias constem em cust_prop_white_keys_list.
    """
    keys_to_add = [
        "ro.miui.support_miui_ime_bottom",
        "persist.mdc_color_detection"
    ]
    if extra_keys:
        keys_to_add.extend(extra_keys)

    lines = []
    if os.path.exists(cust_keys_path):
        with open(cust_keys_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]

    for k in keys_to_add:
        if k not in lines:
            lines.append(k)

    os.makedirs(os.path.dirname(os.path.abspath(cust_keys_path)), exist_ok=True)
    with open(cust_keys_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[enhanced_keyboard] Whitelist atualizada em {cust_keys_path}")
