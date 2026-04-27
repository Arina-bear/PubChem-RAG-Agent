import asyncio
from src.app.config import Settings
from src.app.services.query_service import QueryService
from src.app.schemas.agent import QueryRequest
# Импортируй свой реальный MultiServerMCPClient
from src.app.agent.mcp_client import MultiServerMCPClient 
from pathlib import Path
import os

current_dir = Path(__file__).parent.parent
src_path = str(current_dir / "src")

async def debug_mcp_query():
    print("--- Фаза 1: Инициализация настроек ---")
    settings = Settings()
    mcp_config = {
    "pubchem": {
        "command": "python",
        "args": ["-m", "app.agent.msp_server"], 
        "transport": "stdio",
        "env": {**os.environ, "PYTHONPATH": src_path}
    }
}
    mcp_client = MultiServerMCPClient(mcp_config) 
    
    print("--- Фаза 2: Подключение к MCP ---")
    try:
        async with mcp_client.session("pubchem") as session:
            service = QueryService(settings, mcp_client)
            
            # Создаем запрос
            req = QueryRequest(
                input_mode="inchikey",
                identifier="QCOZYUGXYJSINC-UHFFFAOYSA-N",
                operation="property",
                limit=2,
                include_raw=True
            )
            
            print(f"--- Фаза 3: Выполнение запроса {req.identifier} ---")
            response = await service.execute(req)
            
            print("Ответ сформирован:")
            print(f"CID: {response.normalized.matches[0].cid}")
            print(f"Title: {response.normalized.matches[0].title}")
            
    except Exception as e:
        print("\n!!!ОШИБКА !!!")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_mcp_query())