# Diretório `input/`

Coloque aqui os arquivos originais extraídos da sua ROM HyperOS para processamento:

| Arquivo Alvo | Local Típico na ROM | Necessário para qual Mod |
|---|---|---|
| `miui-services.jar` | `system_ext/framework/` ou `system/framework/` | **Floating Windows** |
| `miui-framework.jar` | `system_ext/framework/` ou `system/framework/` | **Floating Windows** & **Enhanced Keyboard** |
| `MIUIFrequentPhrase.apk` | `product/app/MIUIFrequentPhrase/` | **Enhanced Keyboard** |
| `build.prop` | `system/build.prop` ou `system_ext/etc/build.prop` | **Enhanced Keyboard** |
| `cust_prop_white_keys_list` | `system_ext/etc/cust_prop_white_keys_list` | **Enhanced Keyboard** |

Você também pode manter a estrutura de subpastas da ROM (ex: `input/system_ext/framework/miui-services.jar`), pois o script busca os arquivos recursivamente de forma automática.
