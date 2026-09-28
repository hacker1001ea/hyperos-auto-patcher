#!/usr/bin/env python3
"""
Tool Resolver for smali and baksmali jar binaries.
Resolves tool paths portably from repo-local directories, environment variables, or remote downloads.
"""

import os
import sys
import shutil
import urllib.request
import urllib.error

DEFAULT_SMALI_VERSION = "2.5.2"
SMALI_MAVEN_URL = f"https://repo1.maven.org/maven2/org/smali/smali/{DEFAULT_SMALI_VERSION}/smali-{DEFAULT_SMALI_VERSION}.jar"
BAKSMALI_MAVEN_URL = f"https://repo1.maven.org/maven2/org/smali/baksmali/{DEFAULT_SMALI_VERSION}/baksmali-{DEFAULT_SMALI_VERSION}.jar"


def get_default_tools_dir():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo_root, "tools")


def download_file(url, destination):
    print(f"[tool_resolver] Baixando {url} -> {destination}...")
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    temp_dst = destination + ".tmp"
    try:
        urllib.request.urlretrieve(url, temp_dst)
        if os.path.exists(destination):
            os.remove(destination)
        os.rename(temp_dst, destination)
        print(f"[tool_resolver] Download concluído com sucesso ({os.path.getsize(destination)} bytes).")
    except Exception as e:
        if os.path.exists(temp_dst):
            os.remove(temp_dst)
        raise RuntimeError(f"Falha ao baixar {url}: {e}")


def resolve_tools(tools_dir=None, explicit_smali=None, explicit_baksmali=None, auto_download=False):
    """
    Localiza smali.jar e baksmali.jar de forma portátil e desacoplada.
    Ordem de busca:
    1. Parâmetros explícitos (CLI)
    2. Variáveis de ambiente (SMALI_JAR, BAKSMALI_JAR, TOOLS_DIR)
    3. Diretório tools/ local do repositório
    4. PATH do sistema
    5. Download automático se auto_download=True
    """
    tools_dir = tools_dir or os.environ.get("TOOLS_DIR") or get_default_tools_dir()
    os.makedirs(tools_dir, exist_ok=True)

    smali_path = explicit_smali or os.environ.get("SMALI_JAR")
    if not smali_path or not os.path.exists(smali_path):
        candidate = os.path.join(tools_dir, "smali.jar")
        if os.path.exists(candidate):
            smali_path = candidate
        else:
            # Procura no PATH
            which_smali = shutil.which("smali.jar") or shutil.which("smali")
            if which_smali and which_smali.endswith(".jar") and os.path.exists(which_smali):
                smali_path = which_smali

    baksmali_path = explicit_baksmali or os.environ.get("BAKSMALI_JAR")
    if not baksmali_path or not os.path.exists(baksmali_path):
        candidate = os.path.join(tools_dir, "baksmali.jar")
        if os.path.exists(candidate):
            baksmali_path = candidate
        else:
            which_baksmali = shutil.which("baksmali.jar") or shutil.which("baksmali")
            if which_baksmali and which_baksmali.endswith(".jar") and os.path.exists(which_baksmali):
                baksmali_path = which_baksmali

    # Caso ainda não encontre e auto_download esteja ativado
    if auto_download:
        if not smali_path or not os.path.exists(smali_path):
            target_smali = os.path.join(tools_dir, "smali.jar")
            download_file(SMALI_MAVEN_URL, target_smali)
            smali_path = target_smali

        if not baksmali_path or not os.path.exists(baksmali_path):
            target_baksmali = os.path.join(tools_dir, "baksmali.jar")
            download_file(BAKSMALI_MAVEN_URL, target_baksmali)
            baksmali_path = target_baksmali

    if not smali_path or not os.path.exists(smali_path):
        raise FileNotFoundError(
            f"smali.jar não encontrado em '{tools_dir}'. "
            f"Coloque o arquivo smali.jar em '{tools_dir}' ou passe --smali-jar ou use --auto-download."
        )

    if not baksmali_path or not os.path.exists(baksmali_path):
        raise FileNotFoundError(
            f"baksmali.jar não encontrado em '{tools_dir}'. "
            f"Coloque o arquivo baksmali.jar em '{tools_dir}' ou passe --baksmali-jar ou use --auto-download."
        )

    return os.path.abspath(smali_path), os.path.abspath(baksmali_path)


if __name__ == "__main__":
    sm, bsm = resolve_tools()
    print("Resolved Smali:", sm)
    print("Resolved Baksmali:", bsm)
