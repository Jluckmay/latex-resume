# 🧪 Suíte de Testes & Verificação de Segurança / Test Suite

Este diretório contém a suíte completa de testes automatizados do **LaTeX Resume Generator** (**214 testes com 100% de aprovação**), cobrindo integridade funcional, proteções de segurança, compilação de templates em página única, enclave criptográfico e conformidade com a arquitetura Zero-Storage.

---

## 📂 Organização dos Módulos de Teste

| Arquivo de Teste | Escopo e Responsabilidade Principal |
| :--- | :--- |
| **`test_academic_mode_and_colors.py`** | Valida a renderização e ordem de seções no modo acadêmico, suporte a cores personalizadas (`\definecolor`), preservação de seções completas e 6 bullets de proficiência de idiomas no preview. |
| **`test_awards_and_orcid.py`** | Valida a higienização da seção de prêmios/certificações (omissão quando vazia em todos os 10 templates), exclusão automática de bolsas de extensão redundantes e isolamento de identificadores ORCID estritamente no cabeçalho. |
| **`test_chronological_ordering_and_deduplication.py`** | Valida a ordenação cronológica reversa estrita de experiências, formações e projetos, além da deduplicação de entradas duplicadas entre diferentes fontes. |
| **`test_direct_builder.py`** | Valida o construtor direto determinístico (0 tokens / modo offline), mapeamento de XML do Lattes, renderização sem modelo em todos os 10 templates, flag `use_ai=False` e endpoint de API offline. |
| **`test_encrypted_comm.py`** | Valida a camada de transporte criptografada: envelopamento AES-256-GCM (`ENC_PAYLOAD_V1` e `SECKEY_V1`), rotação de salt/IV, proteção anti-replay, redação de chaves em mensagens de erro e diretivas estritas de CSP. |
| **`test_english_standardization_and_dedup.py`** | Valida a padronização e tradução de termos para inglês (`en-US`), formatação consistente de datas e eliminação de duplicidades linguísticas em currículos bilíngues. |
| **`test_experience_nouns_and_email.py`** | Valida a higienização de substantivos, títulos de cargos em experiências profissionais e validação segura de formatos de email. |
| **`test_generation_resilience_and_ui_polish.py`** | Valida a resiliência do pipeline contra falhas de rede, fallbacks determinísticos automáticos e consistência visual entre as interfaces. |
| **`test_latex_formatting.py`** | Valida a conformidade de sintaxe LaTeX, quebras de linha explícitas, espaçamento, auditoria anti-injeção (`\write18`, `\input`) e o motor de reparo automático de erros do compilador. |
| **`test_manual_input_mode.py`** | Valida o modo de inserção manual estruturada nas interfaces (Streamlit e Web), parser de texto delimitado por pipes (`|`), cards dinâmicos e geração ponta a ponta via API `/api/generate`. |
| **`test_platform_display.py`** | Valida a formatação e simplificação de handles para exibição limpa em cabeçalhos (GitHub, LinkedIn, ORCID, Google Scholar, Lattes e Portfólio). |
| **`test_projects_enrichment.py`** | Valida o enriquecimento e sanitização de dados de projetos (stack técnica, links de repositório e descrições sem quebra de sintaxe). |
| **`test_scholar_and_publications.py`** | Valida a fusão inteligente e deduplicação de artigos científicos entre Google Scholar, ORCID e Lattes, além de links de DOI e abreviação de nomes acadêmicos. |
| **`test_single_page_template.py`** | Valida a compilação estrita em **1 página** para os templates de alta densidade (`overleaf_single_page_keywords`, `minimal_ats`, `tech_sidebar` e `google_standard`), garantindo ausência de páginas em branco ou estouro de layout. |
| **`test_ui_assets.py`** | Valida a integridade, dimensões e padronização dos ícones e favicons (`SVG`, `PNG` 512/192/32/16, `ICO`), acessibilidade WCAG, temas claro/escuro e ofuscação da URL do backend Render. |
| **`test_zero_storage.py`** | Valida as garantias da arquitetura Zero-Storage: criação isolada em diretórios temporários na RAM, destruição segura por sobrescrita binária (`0x00`) via `secure_wipe_and_remove_dir` e ausência de resíduos em disco. |
| **`conftest.py`** | Configurações globais de fixtures do pytest, variáveis de ambiente seguras de teste e isolamento de runtime. |

---

## 🚀 Como Executar os Testes

### 1. Executar Toda a Suíte (214 Testes)
```powershell
pytest -v
```

### 2. Executar Testes com Relatório de Cobertura
```powershell
pytest -v --cov=src --cov=server --cov=cli
```

### 3. Executar Testes Específicos de Página Única
```powershell
pytest -v tests/test_single_page_template.py
```

### 4. Executar Testes de Segurança e Criptografia
```powershell
pytest -v tests/test_encrypted_comm.py tests/test_zero_storage.py
```

---

## 🛡️ Invariantes de Segurança Garantidos por Testes
1. **Zero Secret Leaks**: Nenhuma chave de API (NVIDIA, Google, Claude, OpenAI, DeepSeek) ou URL interna pode vazar em texto puro em logs, endpoints de status, atributos HTML ou respostas de erro.
2. **Zero Storage**: Nenhum arquivo compilado (PDF, TeX, logs do LaTeX) pode permanecer persistido em disco no servidor após o encerramento do ciclo da requisição.
3. **Página Única Estrita**: Modelos anunciados como página única (`google_standard`, `tech_sidebar`, `minimal_ats`, `overleaf_single_page_keywords`) devem compilar para exatamente 1 página, mesmo sob perfis acadêmicos e profissionais densos.
4. **Payload Criptografado**: Todas as requisições e respostas sensíveis entre a interface web e a API utilizam envelopes cifrados AES-256-GCM com chave de sessão efêmera e vetor de inicialização criptograficamente aleatório.
