import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def run():
    server_params = StdioServerParameters(command="npx", args=["-y", "@cocal/gmail-mcp"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for t in tools.tools:
                print(t.name)

asyncio.run(run())
