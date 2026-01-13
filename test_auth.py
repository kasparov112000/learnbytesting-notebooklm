"""Test NotebookLM authentication and chat."""
import asyncio
from notebooklm import NotebookLMClient

NOTEBOOK_ID = "536d6313-4350-4f7b-8569-96fb07470350"

async def test():
    try:
        async with await NotebookLMClient.from_storage() as client:
            print("Checking ChatAPI methods...")
            print(f"ChatAPI methods: {[m for m in dir(client.chat) if not m.startswith('_')]}")

            # Try the correct method
            print("Testing chat with notebook...")
            response = await client.chat.ask(
                notebook_id=NOTEBOOK_ID,
                question="What openings have I played?"
            )
            print(f"SUCCESS: {response}")
            if hasattr(response, 'text'):
                print(f"Answer: {response.text}")
            else:
                print(f"Answer: {response}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
