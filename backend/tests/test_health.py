import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock

from src.app.main import create_app

def test_health_endpoint_success():
    """
    Тестируем эндпоинт health, используя mock-контейнер,
    чтобы не зависеть от реальных подключений к MCP 
    """
    mock_settings = MagicMock()
    mock_settings.api_version = "1.0.0-beta"
    mock_settings.environment = "testing"
    mock_settings.pubchem_rest_base_url = "https://pubchem.mock/rest"
    mock_settings.pubchem_view_base_url = "https://pubchem.mock/view"
    mock_settings.app_name = "PubChem Agent Test"
    # Добавляем другие необходимые атрибуты, если они требуются в CORSMiddleware
    mock_settings.cors_origins = ["*"]

    mock_container = MagicMock()
    mock_container.settings = mock_settings
    mock_container.close = AsyncMock() 

    app = create_app(container_override=mock_container)

    # 4. Выполняем запрос через TestClient
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == "1.0.0-beta"
    assert payload["environment"] == "testing"
    assert payload["upstream"]["pubchem_rest_base_url"] == "https://pubchem.mock/rest"
    
    # Проверяем наличие обязательных полей
    assert "cache_backend" in payload
    assert "planned_components" in payload