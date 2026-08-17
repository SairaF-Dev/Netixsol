from app.agent import llm
from langchain_core.messages import HumanMessage

response = llm.invoke([
    HumanMessage(content="Say hello in one sentence.")
])

print("CONTENT:")
print(response.content)

print("\nUSAGE METADATA:")
print(response.usage_metadata)

print("\nRESPONSE METADATA:")
print(response.response_metadata)