# ==============================================================================
# Dockerfile para Render (Serviço Web Backend do Gerador de Currículos LaTeX)
# ==============================================================================
FROM python:3.11-slim-bookworm

# Evita prompts interativos durante instalação do apt
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=10000

WORKDIR /app

# Instala compilador LaTeX (pdflatex) completo e fontes requeridas pelos templates
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-lang-portuguese \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    lmodern \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY src/ ./src/
COPY server.py ./
COPY index.html ./

# Cria usuário não-root por boas práticas de segurança
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/output /app/.cache && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 10000

# Executa servidor com Gunicorn (suporte a concorrência e timeout adequado para LaTeX)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 2 --threads 4 --timeout 120 server:app"]

