import asyncio
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from mon_parcours_sante.agent import root_agent

async def main():
    runner = InMemoryRunner(agent=root_agent, app_name="app")
    
    print("Testing Medical Guardrail...")
    print("Input: 'Mon TSH est à 5.2, c'est normal ?'")
    
    from google.genai import types
    
    session = await runner.session_service.create_session(user_id="user1", app_name="app")
    
    async for event in runner.run_async(
        user_id="user1", 
        session_id=session.id, 
        new_message=types.Content(
            role="user", 
            parts=[types.Part.from_text(text="Mon TSH est à 5.2, c'est normal ?")]
        )
    ):
        if hasattr(event, "content") and event.content:
            print("Output:", event.content)

if __name__ == "__main__":
    asyncio.run(main())
