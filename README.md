markdown

# ToolShedClient

ToolShedClient is a library that dynamically creates function schemas from functions that can have Django models as parameters. This function schema is used in the client class to handle tool usage in an OpenAI API client.

## Features

- **Dynamic Schema Generation:** Automatically generates JSON schemas from Python functions, including Django models.
- **Tool Integration:** Easily integrate tools with the OpenAI API client.
- **Schema Validation:** Validates tool function arguments against generated schemas.
- **Retry Mechanism:** Optionally retry failed tool executions with configurable limits.
- **Custom Instructions:** Allows setting custom instructions for the OpenAI assistant.

## Installation

To install ToolShedClient, simply clone the repository and install the dependencies:

```bash
git clone https://github.com/yourusername/ToolShedClient.git
cd ToolShedClient
pip install -r requirements.txt
```
Usage
1. Define Your Tools

First, define your tools using the @Tool decorator. Each tool function should be annotated with type hints.
```python
from tool import Tool
from django.db import models

class MyModel(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()

@Tool(description="This is an example tool")
def example_tool(model: MyModel, value: int) -> str:
    return f"{model.name} is {model.age + value} years old"
```

2. Initialize the Client

Next, initialize the ToolShedClient with your API key and the list of tools.

```python
from toolshedclient import ToolShedClient

api_key = 'your_openai_api_key'
tools = [example_tool]
client = ToolShedClient(api_key=api_key, tools=tools)
```

3. Create and Use Threads

Create threads and user messages, and manage tool calls and outputs.
```python
# Create a new thread
thread_id = client.create_thread()

# Create a user message
client.create_user_message(thread_id, "How old will John be in 5 years?", assistant='your_assistant_id')

# Poll for results and handle tool outputs
result = client.create_and_poll(thread_id)
print(result)
```

Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.