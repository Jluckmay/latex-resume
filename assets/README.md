# 🎨 Identidade Visual & Ícones Oficiais / Brand Assets

Este diretório armazena todos os arquivos oficiais da identidade visual do projeto **LaTeX Resume Generator**:

```
assets/
├── icons/                 # Ícones, favicons e logotipo oficial
│   ├── favicon.svg        # Logotipo vetorial SVG de alta definição (viewBox 0 0 512 512)
│   ├── favicon.png        # Ícone em alta resolução PNG (512x512)
│   ├── favicon-192.png    # Variante PWA / Android (192x192)
│   ├── favicon-32.png     # Favicon padrão para desktop (32x32)
│   ├── favicon-16.png     # Favicon compacto para abas densas (16x16)
│   ├── apple-touch-icon.png # Ícone para iOS Safari / Apple Home Screen (180x180)
│   └── favicon.ico        # Ícone multi-resolução para navegadores legados e modernos
└── README.md              # Especificações de design e guia de assets
```

## 📐 Especificações Técnicas de Design

- **Cores Oficiais**:
  - `Azul Noturno`: `#0B192C` (fundo principal)
  - `Azul Clássico LaTeX`: `#0F4C81` (acento e gradiente)
  - `Azul Royal / Deep Blue`: `#1E3A8A` (profundidade)
  - `Ciano Neon Tech`: `#38BDF8` (brilho e realces)
  - `Branco Puro`: `#FFFFFF` (página do documento)
  - `Dourado Sparkle`: `#FBBF24` (estrela de IA)
- **Elementos Visuais**:
  - *Squircle* com borda gradiente suave e cantos arredondados.
  - Folha de currículo com dobra superior direita tridimensional.
  - Tipografia LaTeX central (`L`, `A`, `T`, `E`, `X` com deslocamento tipográfico tradicional).
  - Estrela de 4 pontas no topo simbolizando síntese inteligente por IA.

## 🔄 Como Regerar os Ícones
Para regerar ou atualizar todos os formatos a partir do código vetorial, execute:
```powershell
python scripts/generate_icons.py
```
*(Os arquivos são gerados e organizados exclusivamente em `assets/icons/`, mantendo a raiz do projeto e diretórios de código completamente limpos).*
