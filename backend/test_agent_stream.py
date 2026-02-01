
from app.agents.river_agent import build_agent
from app.core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

# Mock keys if not present (assuming environment has them or defaults)
agent = build_agent(None, None)

print("Starting run...")
# Run with a query that should trigger knowledge retrieval if possible, or just a generic one
# We need to see if chunks have sources
response = agent.run("hello", stream=True)
for chunk in response:
    print(f"Type: {type(chunk)}")
    print(f"Dir: {dir(chunk)}")
    if hasattr(chunk, 'sources'):
        print(f"Sources: {chunk.sources}")
    break
