# HyperOS Patcher Engine

[![Build HyperOS Mods](https://github.com/hacker1001ea/hyperos-auto-patcher/actions/workflows/build_mods.yml/badge.svg)](https://github.com/hacker1001ea/hyperos-auto-patcher/actions/workflows/build_mods.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Java 11+](https://img.shields.io/badge/java-11%20%7C%2017%20%7C%2021-orange.svg)](https://adoptium.net/)
[![Target Android API](https://img.shields.io/badge/Android%20Target-API%2034%20(Android%2014%2F15)-brightgreen.svg)](https://developer.android.com/)

Repositório autônomo, desacoplado e portátil para engenharia reversa, aplicação de patches em Smali/DEX (API 34) e geração automatizada de **módulos Magisk / KernelSU / APatch** e **arquivos prontos para *bake* de ROMs Xiaomi HyperOS**.

---

## 🎯 Modificações Suportadas

### 1. Janelas Flutuantes Expandidas (Floating Windows)
- **Aumento do limite de instâncias simultâneas:** Altera `getMaxMiuiFreeFormStackCount(...)I` em `MiuiFreeFormStackDisplayStrategy.smali` para permitir até **6 janelas ativas simultâneas** (ou configurável via CLI).
- **Neutralização de Blacklists:** Neutraliza `getFreeformBlackList()` e `getFreeformBlackListFromCloud()` em `MiuiMultiWindowAdapter.smali` e `MiuiFreeformServiceImpl.smali` retornando `null`.
- **Proteção Null-Safety:** Insere verificações defensivas de nulo em `MiuiFreeFormManagerService.smali` para prevenir `NullPointerException` (NPE) nas chamadas de verificação de lista.

### 2. Teclado Aprimorado (Enhanced Keyboard / Gboard & SwiftKey)
- **Desbloqueio de Suporte IME:** Força `isImeSupport(Landroid/content/Context;)Z` para retornar sempre `true` (`0x1`) em `InputMethodServiceInjector.smali`.
- **Substituição de IME Proprietário:** Remove referências a `com.baidu.input_mi` e substitui por `com.google.android.inputmethod.latin` (Gboard) em `InputMethodServiceInjector` e em toda a árvore Smali do `MIUIFrequentPhrase.apk`.
- **Propriedades de Sistema e Whitelist:**
  - Configura `ro.miui.support_miui_ime_bottom=1` e `persist.mdc_color_detection=1` nos arquivos `build.prop`.
  - Registra as chaves de sistema no arquivo de permissão `cust_prop_white_keys_list`.

---

## 📁 Estrutura do Repositório

```text
hyperos_patcher_repo/
├── .github/
│   └── workflows/
│       └── build_mods.yml           # Pipeline CI/CD GitHub Actions
├── input/
│   ├── .gitkeep                     # Pasta padrão para arquivos originais
│   └── README.md                    # Instruções sobre os binários de entrada
├── output/                          # Diretório de saída gerado na execução
│   ├── modules/                     # Módulos Magisk/KernelSU (.zip)
│   ├── bake_files/                  # Estrutura de arquivos pronta para bake na ROM
│   └── props/                       # build.prop e whitelist atualizados
├── scripts/
│   ├── patch_runner.py              # CLI principal e orquestrador ponta a ponta
│   ├── tool_resolver.py             # Resolução e download automático de smali/baksmali
│   ├── dex_utils.py                 # Desmontagem, montagem e correção de integridade DEX
│   ├── patch_floating_windows.py    # Patches Smali das Janelas Flutuantes
│   ├── patch_enhanced_keyboard.py   # Patches Smali do Teclado e injeção de propriedades
│   └── package_modules.py           # Empacotador universal de módulos Magisk e bake
├── tests/
│   └── test_patcher.py              # Testes unitários de regex, parsing e integridade
├── tools/
│   ├── .gitkeep                     # Pasta local para smali.jar e baksmali.jar
│   ├── smali.jar                    # Compilador DEX Smali (API 34)
│   └── baksmali.jar                 # Descompilador DEX Smali
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Requisitos de Sistema

- **Python 3.8+** (utiliza estritamente a biblioteca padrão para máxima velocidade).
- **Java JRE/JDK 11, 17 ou 21** instalado e acessível no `PATH` (para execução do `smali.jar` e `baksmali.jar`).

---

## 🛠️ Como Utilizar

### 1. Preparação dos Arquivos de Entrada
Copie os arquivos da sua ROM original para a pasta `input/`:
- `miui-services.jar`
- `miui-framework.jar`
- `MIUIFrequentPhrase.apk`
- `build.prop` *(opcional, se desejar atualizar as propriedades existentes)*
- `cust_prop_white_keys_list` *(opcional)*

*(Nota: Você pode colocar os arquivos na raiz de `input/` ou manter a hierarquia de pastas da ROM, pois a busca é recursiva).*

### 2. Execução Simples (Todos os Mods)
Para rodar a compilação completa com configurações padrão:
```bash
python scripts/patch_runner.py
```

### 3. Opções Avançadas da CLI

```bash
# Executar apenas o mod de Janelas Flutuantes:
python scripts/patch_runner.py --mod floating-windows

# Executar apenas o mod de Teclado Aprimorado:
python scripts/patch_runner.py --mod enhanced-keyboard

# Definir limite personalizado de janelas flutuantes (ex: 8):
python scripts/patch_runner.py --mod floating-windows --max-windows 8

# Forçar download automático do smali.jar/baksmali.jar caso ausentes:
python scripts/patch_runner.py --auto-download

# Apontar para diretórios customizados:
python scripts/patch_runner.py -i /caminho/minha_rom_extraida -o /caminho/saida
```

---

## 📦 Entregáveis Gerados

Após a execução, os artefatos estarão disponíveis em `output/`:

1. **Módulos Flasháveis (`output/modules/`):**
   - `HyperOS_Floating_Windows_Magisk.zip`: Módulo universal para Magisk, KernelSU e APatch contendo o `miui-services.jar` patcheado.
   - `HyperOS_Enhanced_Keyboard_Magisk.zip`: Módulo contendo os JARs modificados, o APK `MIUIFrequentPhrase.apk`, script `post-fs-data.sh` para limpeza preventiva do cache Dalvik/ART, propriedades `system.prop` e whitelist.
2. **Arquivos Prontos para Bake (`output/bake_files/`):**
   - Estrutura espelhada da ROM (`system/`, `system_ext/`, `product/`) com os binários modificados prontos para reempacotamento de imagens (`erofs`, `ext4`, `super.img`).
3. **Binários Individuais Patcheados (`output/`):**
   - `miui-services.jar`, `miui-framework.jar`, `MIUIFrequentPhrase.apk`.

---

## 🧪 Testes Unitários

O projeto conta com uma suíte de testes unitários que valida a integridade do cabeçalho DEX (Adler-32 e SHA-1), regexes de Smali e parsing de propriedades:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 🌐 Integração Contínua (GitHub Actions)

O workflow `.github/workflows/build_mods.yml` permite:
- Execução automática dos testes unitários em cada `push` e `pull_request`.
- Execução manual via **Workflow Dispatch** na interface do GitHub, permitindo selecionar o mod desejado e baixar os arquivos ZIP dos módulos diretamente como artefatos da Action.
