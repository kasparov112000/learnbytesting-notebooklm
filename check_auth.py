import asyncio
from notebooklm import NotebookLMClient

async def check():
    async with await NotebookLMClient.from_storage() as client:
        print('Client connected successfully!')
        notebooks = await client.notebooks.list()
        print(f'Authenticated! Found {len(notebooks)} notebooks')
        for nb in notebooks[:5]:
            print(f'  - {nb.title}')

asyncio.run(check())
