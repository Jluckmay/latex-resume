# 🧪 Suíte de Testes & Verificação de Segurança / Test Suite

Este diretório contém a suíte completa de testes automatizados do **LaTeX Resume Generator**, cobrindo integridade funcional, proteções de segurança, enclave criptográfico e conformidade com a arquitetura Zero-Storage.

---

## 📂 Organização dos Testes

| Arquivo de Teste | Escopo e Responsabilidade |
| :--- | :--- |
| **`test_awards_and_orcid.py`** | Valida a higienização da seção de prêmios/certificações (omissão automática quando vazia em todos os 9 templates integrados), remoção rigorosa de identificadores ORCID da seção de prêmios e preservação do ORCID exclusivamente no cabeçalho de contatos. |
| **`test_direct_builder.py`** | Valida o construtor direto determinístico (0 tokens / modo offline), mapeamento a partir de XML do Lattes, renderização sem modelo em todos os 9 templates, flag `use_ai=False`, método cirúrgico `review_and_enhance_latex` e API `/api/generate` com provider `none`. |
| **`test_encrypted_comm.py`** | Valida a segurança da camada de transporte entre frontend e backend: envelopamento AES-256-GCM (`ENC_PAYLOAD_V1` e `SECKEY_V1`), rotação de salt/IV, proteção anti-replay (janela temporal e nonce), redação de chaves em mensagens de erro e diretivas estritas de CSP (`font-src`, `style-src`). |
| **`test_ui_assets.py`** | Valida a existência e dimensões dos ícones e favicons (`SVG`, `PNG` 512/192/32/16, `ICO`), endpoints HTTP de favicon no Flask, responsividade da interface web, uso obrigatório do perfil canônico Lucas Silva em todos os previews, e ofuscação segura da URL do backend Render. |
| **`test_zero_storage.py`** | Valida as garantias da arquitetura Zero-Storage: criação isolada em pastas efêmeras em RAM/temporárias, destruição segura por sobrescrita binária (`0x00`) via `secure_wipe_and_remove_dir`, e ausência de retenção de dados após compilação. |
| **`conftest.py`** | Configurações globais de fixtures do pytest, variáveis de ambiente seguras de teste e isolamento de runtime. |

---

## 🚀 Como Executar os Testes

### 1. Executar Toda a Suíte
```powershell
pytest -v
```

### 2. Executar Testes com Relatório de Cobertura
```powershell
pytest -v --cov=src --cov=server --cov=cli
```

### 3. Executar um Módulo Específico
```powershell
pytest -v tests/test_encrypted_comm.py
pytest -v tests/test_awards_and_orcid.py
pytest -v tests/test_zero_storage.py
pytest -v tests/test_ui_assets.py
```

---

## 🛡️ Invariantes de Segurança Garantidos por Testes
1. **Zero Secret Leaks**: Nenhuma chave de API (NVIDIA, Google, Claude, OpenAI, DeepSeek) ou URL interna pode vazar em texto puro em logs, endpoints de status, atributos HTML ou respostas de erro.
2. **Zero Storage**: Nenhum arquivo compilado (PDF, TeX, logs do LaTeX) pode permanecer persistido em disco no servidor após o encerramento do ciclo da requisição.
3. **Payload Criptografado**: Todas as requisições e respostas sensíveis entre a interface web e a API utilizam envelopes cifrados AES-256-GCM com chave de sessão efêmera e vetor de inicialização criptograficamente aleatório.

