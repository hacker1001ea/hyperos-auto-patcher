#!/usr/bin/env python3
"""
Unit tests for HyperOS patch engine:
- DEX integrity calculation (Adler32 and SHA-1)
- Smali regex matching and replacements
- Build.prop parser and whitelist key injection
"""

import os
import sys
import shutil
import tempfile
import unittest

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from dex_utils import fix_dex_integrity
from patch_floating_windows import patch_services_floating_windows, patch_framework_floating_windows
from patch_enhanced_keyboard import (
    patch_ime_injector,
    replace_baidu_in_smali_tree,
    patch_build_props,
    patch_cust_prop_white_keys
)


class TestHyperOSPatcher(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_hyperos_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_dex_integrity(self):
        # Cria um mock DEX mínimo com 128 bytes
        dummy_dex = os.path.join(self.test_dir, "test.dex")
        raw = bytearray(128)
        raw[0:8] = b"dex\n035\x00"
        with open(dummy_dex, "wb") as f:
            f.write(raw)

        adler, sha1 = fix_dex_integrity(dummy_dex, target_magic=b"dex\n039\x00")
        with open(dummy_dex, "rb") as f:
            data = f.read()

        self.assertEqual(data[0:8], b"dex\n039\x00")
        self.assertNotEqual(adler, 0)
        self.assertEqual(len(sha1), 40)

    def test_floating_windows_services_patch(self):
        smali_path = os.path.join(self.test_dir, "MiuiFreeFormStackDisplayStrategy.smali")
        sample_smali = """.class public Lcom/android/server/wm/MiuiFreeFormStackDisplayStrategy;
.super Ljava/lang/Object;

.method private getMaxMiuiFreeFormStackCount(Ljava/lang/String;Lcom/android/server/wm/MiuiFreeFormActivityStack;)I
    .registers 4
    .param p1, "packageName"    # Ljava/lang/String;
    .param p2, "stack"    # Lcom/android/server/wm/MiuiFreeFormActivityStack;

    const/4 v0, 0x2

    return v0
.end method
"""
        with open(smali_path, "w", encoding="utf-8") as f:
            f.write(sample_smali)

        patch_services_floating_windows(self.test_dir, max_windows=6)
        with open(smali_path, "r", encoding="utf-8") as f:
            res = f.read()

        self.assertIn("const/4 v0, 0x6", res)
        self.assertNotIn("const/4 v0, 0x2", res)

    def test_floating_windows_framework_blacklist(self):
        adapter_path = os.path.join(self.test_dir, "MiuiMultiWindowAdapter.smali")
        sample_adapter = """.class public Landroid/util/MiuiMultiWindowAdapter;
.super Ljava/lang/Object;

.method public static blacklist getFreeformBlackList()Ljava/util/List;
    .registers 1
    const-string v0, "bla"
    return-object v0
.end method

.method public static blacklist getFreeformBlackListFromCloud(Landroid/content/Context;)Ljava/util/List;
    .registers 2
    const-string v0, "bla"
    return-object v0
.end method
"""
        with open(adapter_path, "w", encoding="utf-8") as f:
            f.write(sample_adapter)

        patch_framework_floating_windows(self.test_dir)
        with open(adapter_path, "r", encoding="utf-8") as f:
            res = f.read()

        self.assertIn("const/4 v0, 0x0", res)
        self.assertIn("return-object v0", res)

    def test_enhanced_keyboard_injector_patch(self):
        injector_path = os.path.join(self.test_dir, "InputMethodServiceInjector.smali")
        sample_injector = """.class public Landroid/inputmethodservice/InputMethodServiceInjector;
.super Ljava/lang/Object;

.method private static blacklist isImeSupport(Landroid/content/Context;)Z
    .registers 2
    .param p0, "context"    # Landroid/content/Context;

    const/4 v0, 0x0

    return v0
.end method
"""
        with open(injector_path, "w", encoding="utf-8") as f:
            f.write(sample_injector)

        patch_ime_injector(self.test_dir)
        with open(injector_path, "r", encoding="utf-8") as f:
            res = f.read()

        self.assertIn("const/4 v0, 0x1", res)

    def test_replace_baidu_in_smali_tree(self):
        sub_dir = os.path.join(self.test_dir, "sub")
        os.makedirs(sub_dir, exist_ok=True)
        file1 = os.path.join(sub_dir, "Test1.smali")
        with open(file1, "w", encoding="utf-8") as f:
            f.write('const-string v0, "com.baidu.input_mi"\ninvoke-virtual {v0}')

        count = replace_baidu_in_smali_tree(self.test_dir)
        self.assertEqual(count, 1)

        with open(file1, "r", encoding="utf-8") as f:
            res = f.read()
        self.assertIn("com.google.android.inputmethod.latin", res)
        self.assertNotIn("com.baidu.input_mi", res)

    def test_build_prop_and_white_keys(self):
        prop_path = os.path.join(self.test_dir, "build.prop")
        with open(prop_path, "w", encoding="utf-8") as f:
            f.write("ro.product.model=Houji\nro.miui.support_miui_ime_bottom=0\n")

        patch_build_props(prop_path)
        with open(prop_path, "r", encoding="utf-8") as f:
            res = f.read()

        self.assertIn("ro.miui.support_miui_ime_bottom=1", res)
        self.assertIn("persist.mdc_color_detection=1", res)

        keys_path = os.path.join(self.test_dir, "cust_prop_white_keys_list")
        with open(keys_path, "w", encoding="utf-8") as f:
            f.write("some.key.one\n")

        patch_cust_prop_white_keys(keys_path)
        with open(keys_path, "r", encoding="utf-8") as f:
            keys_res = f.read()

        self.assertIn("ro.miui.support_miui_ime_bottom", keys_res)
        self.assertIn("persist.mdc_color_detection", keys_res)


if __name__ == "__main__":
    unittest.main()
