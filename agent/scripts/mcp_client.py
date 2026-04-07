from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.messages import HumanMessage
import asyncio
from prompts import SYSTEM_PROMPT

async def main():
    async with MultiServerMCPClient({                      
        "pubchem": {
            "command": "python",
            "args": ["pubchem_mcp_server.py"],
            "transport": "stdio",
        }
    }) as client:
        
        tools = await client.get_tools()
        llm = ChatOpenAI(
            model="gpt-4o",  # ВЫБРАТЬ LLM
            temperature=0
        )
        prompt=SYSTEM_PROMPT
        agent = create_agent(model=llm, 
                             tools=tools, 
                             system_prompt=prompt)

        #вызов агента
       # response = await agent.ainvoke({
        #    "messages": [HumanMessage(content="Найди аспирин")]
        #})
        #print(response)

if __name__ == "__main__":
    asyncio.run(main())