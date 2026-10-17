# 📁 Arquivos de Exemplo / Sample Examples

Este diretório contém arquivos de teste e modelos de exemplo para experimentação rápida do gerador de currículos:

| Arquivo | Descrição | Como Utilizar |
| :--- | :--- | :--- |
| **`sample_lattes.xml`** | Arquivo XML de exemplo no formato oficial do CNPq (Currículo Lattes). Contém dados cadastrais fictícios, formação, projetos de pesquisa e artigos publicados. | Envie via campo de upload do Lattes na interface web (`index.html`), no Streamlit (`app.py`) ou via CLI: `--lattes-file examples/sample_lattes.xml`. |
| **`sample_photo.png`** | Imagem quadrada de avatar neutro para teste de normalização com Pillow e renderização com moldura colorida nos modelos que suportam foto. | Envie no campo de foto de perfil na interface web, no Streamlit ou via CLI: `--photo examples/sample_photo.png`. |
| **`custom_template_example.tex`** | Modelo de currículo LaTeX customizado com estrutura em seções limpas e placeholders para demonstração do renderizador de templates externos. | Selecione a opção "Template Customizado" na interface web ou utilize via CLI: `--custom-template examples/custom_template_example.tex`. |
| **`custom_template_example.pdf`** | Versão em PDF pré-compilada a partir do `custom_template_example.tex` para referência visual do layout esperado. | Abra diretamente em qualquer leitor de PDF para inspecionar a tipografia e espaçamento. |

### 💡 Teste Rápido via CLI usando os Exemplos:
```powershell
python cli.py --type academico --template-id academic_classic --lattes-file examples/sample_lattes.xml --photo examples/sample_photo.png --lang pt-br
```
