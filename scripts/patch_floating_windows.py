#!/usr/bin/env python3
"""
Patch module for HyperOS Floating Windows (Janelas Flutuantes).
- Expands max concurrent floating window limit (default: 6 stacks).
- Neutralizes freeform blacklist (local & cloud).
- Adds null-safety protections against NullPointerExceptions in WindowManager services.
"""

import os
import re


def patch_services_floating_windows(services_smali_dir, max_windows=6):
    """
    Aplica as modificações necessárias na árvore smali de miui-services.jar:
    1. MiuiFreeFormStackDisplayStrategy.smali: getMaxMiuiFreeFormStackCount -> max_windows
    2. MiuiFreeFormManagerService.smali: null-safety no retorno de getFreeformBlackList()
    3. MiuiFreeformServiceImpl.smali: getFreeformBlackList() -> null
    """
    # 1. MiuiFreeFormStackDisplayStrategy.smali
    target_strategy = None
    for root, _, files in os.walk(services_smali_dir):
        if "MiuiFreeFormStackDisplayStrategy.smali" in files:
            target_strategy = os.path.join(root, "MiuiFreeFormStackDisplayStrategy.smali")
            break

    if not target_strategy or not os.path.exists(target_strategy):
        raise FileNotFoundError("Não foi possível encontrar 'MiuiFreeFormStackDisplayStrategy.smali' em miui-services.")

    with open(target_strategy, "r", encoding="utf-8") as f:
        strategy_content = f.read()

    # Verifica se já está patcheado
    already_patched_check = f"const/4 v0, 0x{max_windows:x}\n\n    return v0"
    if already_patched_check in strategy_content:
        print(f"[floating_windows] MiuiFreeFormStackDisplayStrategy.smali já se encontra patcheado ({max_windows} janelas).")
    else:
        pattern = re.compile(
            r"\.method private getMaxMiuiFreeFormStackCount\(Ljava/lang/String;Lcom/android/server/wm/MiuiFreeFormActivityStack;\)I.*?"
            r"\.end method",
            re.DOTALL
        )
        replacement = f""".method private getMaxMiuiFreeFormStackCount(Ljava/lang/String;Lcom/android/server/wm/MiuiFreeFormActivityStack;)I
    .registers 4
    .param p1, "packageName"    # Ljava/lang/String;
    .param p2, "stack"    # Lcom/android/server/wm/MiuiFreeFormActivityStack;

    const/4 v0, 0x{max_windows:x}

    return v0
.end method"""
        new_content, count = pattern.subn(replacement, strategy_content)
        if count != 1:
            raise RuntimeError(f"Esperada 1 correspondência para getMaxMiuiFreeFormStackCount, encontradas: {count}")
        with open(target_strategy, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"[floating_windows] MiuiFreeFormStackDisplayStrategy.smali patcheado para {max_windows} janelas simultâneas.")

    # 2. MiuiFreeFormManagerService.smali (Null-Safety)
    for root, _, files in os.walk(services_smali_dir):
        if "MiuiFreeFormManagerService.smali" in files:
            mgr_path = os.path.join(root, "MiuiFreeFormManagerService.smali")
            with open(mgr_path, "r", encoding="utf-8") as f:
                mgr_content = f.read()

            old_pattern = """:cond_23
    invoke-static {}, Landroid/util/MiuiMultiWindowAdapter;->getFreeformBlackList()Ljava/util/List;

    move-result-object v1

    invoke-interface {v1, p2}, Ljava/util/List;->contains(Ljava/lang/Object;)Z"""

            new_pattern = """:cond_23
    invoke-static {}, Landroid/util/MiuiMultiWindowAdapter;->getFreeformBlackList()Ljava/util/List;

    move-result-object v1

    if-eqz v1, :cond_4a

    invoke-interface {v1, p2}, Ljava/util/List;->contains(Ljava/lang/Object;)Z"""

            if old_pattern in mgr_content:
                mgr_content = mgr_content.replace(old_pattern, new_pattern, 1)
                with open(mgr_path, "w", encoding="utf-8") as f:
                    f.write(mgr_content)
                print("[floating_windows] Null-safety adicionado com sucesso em MiuiFreeFormManagerService.smali.")
            elif "if-eqz v1, :cond_4a" in mgr_content:
                print("[floating_windows] MiuiFreeFormManagerService.smali já possui a proteção de null-safety.")

    # 3. MiuiFreeformServiceImpl.smali (Neutraliza getFreeformBlackList)
    for root, _, files in os.walk(services_smali_dir):
        if "MiuiFreeformServiceImpl.smali" in files:
            impl_path = os.path.join(root, "MiuiFreeformServiceImpl.smali")
            with open(impl_path, "r", encoding="utf-8") as f:
                impl_content = f.read()

            p_impl = re.compile(
                r"\.method public getFreeformBlackList\(\)Ljava/util/List;.*?"
                r"\.end method",
                re.DOTALL
            )
            r_impl = """.method public getFreeformBlackList()Ljava/util/List;
    .registers 2
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "()",
            "Ljava/util/List<",
            "Ljava/lang/String;",
            ">;"
        }
    .end annotation

    const/4 v0, 0x0

    return-object v0
.end method"""
            if "const/4 v0, 0x0\n\n    return-object v0" not in impl_content:
                impl_content, c_impl = p_impl.subn(r_impl, impl_content)
                if c_impl == 1:
                    with open(impl_path, "w", encoding="utf-8") as f:
                        f.write(impl_content)
                    print("[floating_windows] getFreeformBlackList neutralizado em MiuiFreeformServiceImpl.smali.")


def patch_framework_floating_windows(framework_smali_dir):
    """
    Aplica as modificações na árvore smali de miui-framework.jar:
    - MiuiMultiWindowAdapter.smali:
      * getFreeformBlackList() -> return-object null
      * getFreeformBlackListFromCloud() -> return-object null
    """
    adapter_smali = None
    for root, _, files in os.walk(framework_smali_dir):
        if "MiuiMultiWindowAdapter.smali" in files:
            adapter_smali = os.path.join(root, "MiuiMultiWindowAdapter.smali")
            break

    if not adapter_smali or not os.path.exists(adapter_smali):
        raise FileNotFoundError("Não foi possível encontrar 'MiuiMultiWindowAdapter.smali' em miui-framework.")

    with open(adapter_smali, "r", encoding="utf-8") as f:
        content = f.read()

    p1 = re.compile(
        r"\.method public static blacklist getFreeformBlackList\(\)Ljava/util/List;.*?"
        r"\.end method",
        re.DOTALL
    )
    r1 = """.method public static blacklist getFreeformBlackList()Ljava/util/List;
    .registers 1
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "()",
            "Ljava/util/List<",
            "Ljava/lang/String;",
            ">;"
        }
    .end annotation

    const/4 v0, 0x0

    return-object v0
.end method"""

    p2 = re.compile(
        r"\.method public static blacklist getFreeformBlackListFromCloud\(Landroid/content/Context;\)Ljava/util/List;.*?"
        r"\.end method",
        re.DOTALL
    )
    r2 = """.method public static blacklist getFreeformBlackListFromCloud(Landroid/content/Context;)Ljava/util/List;
    .registers 2
    .param p0, "context"    # Landroid/content/Context;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "(",
            "Landroid/content/Context;",
            ")",
            "Ljava/util/List<",
            "Ljava/lang/String;",
            ">;"
        }
    .end annotation

    const/4 v0, 0x0

    return-object v0
.end method"""

    changed = False
    if "const/4 v0, 0x0\n\n    return-object v0" not in content:
        content, c1 = p1.subn(r1, content)
        content, c2 = p2.subn(r2, content)
        if c1 == 1 and c2 == 1:
            changed = True
            with open(adapter_smali, "w", encoding="utf-8") as f:
                f.write(content)
            print("[floating_windows] Métodos de blacklist neutralizados com sucesso em MiuiMultiWindowAdapter.smali.")
        else:
            print(f"[floating_windows] Aviso: c1={c1}, c2={c2} em MiuiMultiWindowAdapter.smali.")
    else:
        print("[floating_windows] MiuiMultiWindowAdapter.smali já possui métodos neutralizados.")
