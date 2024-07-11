from openai import OpenAI
from tool import Tool
from typing import Callable

class ToolShedClient(OpenAI):
  def __init__(self, api_key, tools = [], assistant = "", instructions = "You are a helpful assistant", model ="gpt-4o", **kwargs) -> None:
    
    super().__init__(api_key=api_key,**kwargs)
    self.assistant = assistant
    self.instructions = instructions
    self.tools = self.getTools(tools)
    self.model ="gpt-4o"
    self.pollInterval = 2000
    self.api_key=api_key

  def create_thread(self, messages=None):
    return self.beta.threads.create(messages=messages).id
  
  def create_user_message(self, threadId, content, assistant=None):
    self.beta.threads.messages.create(
      thread_id=threadId,
      role = "user",
      content=content
    )
    self.create_and_poll(assistant=assistant)

  def create_and_poll(self, thread_id, assistant=None, add_instructions=None, instructions=None, **kwargs):
    assistant = self.assistant if not assistant else assistant
    instructions = self.instructions if not instructions else instructions

    run = self.beta.threads.runs.create_and_poll(
      thread_id=thread_id,
      assistant_id=assistant, 
      additional_instructions=add_instructions,
      instructions=instructions,
      poll_interval_ms=self.pollInterval,
      tools=self.tools,
      **kwargs)

    return self.handelPoll(thread_id,run)

  def handelPoll(self, thread_id, run):
    if(run.status == "completed"):
      messages = self.beta.threads.messages.list(thread_id)
      value : str = messages.data[0].content[0].text.value
      return {"thread_id" : thread_id, "message":value}
    elif(run.status=='requires_action'):
      tool_calls = run.required_action.submit_tool_outputs.tool_calls
      toolOutputs = Tool.runTools(Tool.tools,tool_calls)
      return self.try_submit_tools_and_poll(toolOutputs,thread_id,run.id)

  def try_submit_tools_and_poll(self, tool_outputs, thread_id, run_id):
    run = self.beta.threads.runs.submit_tool_outputs_and_poll(
    thread_id=thread_id,
    run_id=run_id,
    tool_outputs=tool_outputs,
    )
    return self.handelPoll(thread_id, run)
    
  def getTools(self,tools : list[Callable]):
    results = []
    for tool in Tool.tools:
      for t in tools:
        if t.__name__ == tool.name:
          results.append(tool.tool)
    return results

