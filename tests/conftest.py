"""Configurações globais e fixtures compartilhadas do Pytest para a suíte de testes."""

import sys
from pathlib import Path
from typing import Any, Dict, Generator
import pytest
from flask.testing import FlaskClient

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server import app as flask_app


@pytest.fixture
def app():
    """Instância do Flask configurada para ambiente de testes."""
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app) -> Generator[FlaskClient, None, None]:
    """Cliente de testes HTTP para simulação de requisições à API."""
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def sample_cv_payload() -> Dict[str, Any]:
    """Dados de teste representativos de um perfil de currículo."""
    return {
        "name": "Mariana Souza",
        "role": "Engenheira de Machine Learning",
        "email": "mariana.souza@example.com",
        "location": "São Paulo, SP",
        "phone": "+55 11 99999-8888",
        "linkedin": "https://linkedin.com/in/mariana-souza",
        "github": "marianasouza",
        "portfolio": "https://marianasouza.dev",
        "resume_type": "profissional",
        "template_id": "google_standard",
        "lang": "pt-br",
        "primary_color": "#0F4C81",
        "secondary_color": "#1E293B",
        "provider": "default",
        "extra": "Especialista em LLMs, PyTorch e pipelines de dados.",
    }
