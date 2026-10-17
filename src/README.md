# 🧩 Arquitetura do Pacote `src/` / Module Architecture

Este diretório contém os módulos centrais da aplicação, organizados com separação clara de responsabilidades:

```
src/
├── __init__.py          # Inicialização do pacote Python
├── _vault.py            # Cofre efêmero, criptografia AES-256-GCM (ENC_PAYLOAD_V1/SECKEY_V1) e redação anti-vazamento
├── compiler.py          # Verificação, sanitização TeX e compilação segura (pdflatex, zero-storage wipe)
├── config.py            # Configurações de diretórios, provedores de IA e modelos recomendados
├── extractors.py        # Coletores multi-fonte (GitHub, ORCID, Lattes XML/PDF, Portfólio URL)
├── i18n.py              # Suporte a internacionalização (pt-BR e en-US)
├── llm_client.py        # Cliente multi-provedor (NVIDIA, Gemini, Claude, OpenAI, DeepSeek)
├── nvidia_client.py     # Adaptador de compatibilidade para NVIDIA NIM
├── pipeline.py          # Orquestrador central do pipeline de síntese e compilação
├── templates.py         # 9 modelos LaTeX integrados (Overleaf, Google, IA/ATS) e suporte a template customizado
├── token_plugins.py     # Plugins modulares de economia de tokens (Caveman, TOON, ShortKey, Cache)
└── ui_theme.py          # Definições de tema visual, CSS responsivo e paletas de cores para Streamlit
```

## 📋 Responsabilidades de Cada Módulo

| Módulo | Responsabilidade Principal |
| :--- | :--- |
| **`_vault.py`** | Enclave criptográfico em memória volátil RAM. Gerencia envelopes de transporte (`ENC_PAYLOAD_V1`), envelope de chaves de usuário (`SECKEY_V1`), redação automática de chaves (`scrub_sensitive_api_keys`) e atestação de chamadores autorizados. |
| **`compiler.py`** | Valida a presença do compilador `pdflatex`, sanitiza código LaTeX contra comandos perigosos (`\write18`, `\csname`), executa compilação isolada com `-no-shell-escape` e realiza a destruição segura por sobrescrita (`0x00`) via `secure_wipe_and_remove_dir`. |
| **`config.py`** | Centraliza constantes de projeto, mapeamento de diretórios (`PROJECT_ROOT`, `CACHE_DIR`, `OUTPUT_DIR`) e metadados públicos de provedores e modelos recomendados. |
| **`extractors.py`** | Faz o parsing resiliente de dados brutos: API do GitHub, API Pública do ORCID v3.0, arquivos XML/ZIP do Currículo Lattes (CNPq), extração de texto de PDFs do LinkedIn e raspagem de portfólios web. |
| **`i18n.py`** | Dicionários multilíngues para a CLI, mensagens de erro e prompts de sistema formatados em português (`pt-BR`) e inglês (`en-US`). |
| **`llm_client.py`** | Despacha chamadas para os modelos de IA selecionados, aplicando a cadeia de plugins de economia de tokens e fallback automático para modelos alternativos em caso de indisponibilidade. |
| **`nvidia_client.py`** | Adaptador que herda de `LLMResumeGenerator` para retrocompatibilidade direta com códigos que instanciam `NvidiaResumeGenerator`. |
| **`pipeline.py`** | Coordena o ciclo de vida completo: coleta de dados -> fusão em TOON -> síntese com LLM -> injeção de cores e modelo LaTeX -> compilação em PDF -> geração de métricas. |
| **`templates.py`** | Contém o código LaTeX dos 9 templates integrados (`modern_pro`, `academic_classic`, `tech_sidebar`, `minimal_ats`, `overleaf_russell_ti`, `overleaf_awesome_cv`, `overleaf_single_page_keywords`, `google_standard`, `ai_ats_max`) e parser de preâmbulo para templates `.tex` customizados. |
| **`token_plugins.py`** | Implementa os plugins de economia de tokens: `CavemanPromptPlugin` (-65% verbosidade), `ThinkingSuppressionPlugin` (0 tokens de raciocínio ocultos), `TOONContextPrunerPlugin`, `ShortKeySchemaPlugin` (-40% tokens de JSON) e `SHA256DiskCachePlugin`. |
| **`ui_theme.py`** | Gera estilos CSS dinâmicos com suporte a temas Claro/Escuro, paletas executivas e regras de responsividade para telas móveis no Streamlit. |
