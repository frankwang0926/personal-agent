from state import load_history, save_history
from tools import CALCULATOR_TOOL, execute_tool_safely, parse_tool_arguments
from memory_schemas import REMEMBER_TOOL, RECALL_TOOL
from task_schemas import CREATE_TASK_TOOL, LIST_TASKS_TOOL, UPDATE_TASK_TOOL
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

system_prompt = """
You are a personal assistant with calculator, persistent memory, and task tools.

Use calculator for arithmetic and base your answer on its returned result.

Store personal facts only when the user explicitly requests it. Distinguish
information from conversation history from facts retrieved through memory tools.

Task tools are the source of truth for tasks, rather than conversation history
or personal memory. Read current tasks before modifying them, and clarify
ambiguous references. Change only what the user requested. Recording a task
does not perform it or schedule a reminder.

For task capture, record clear intentions using the user's wording. Preserve
unfamiliar names and abbreviations; do not assume they are typos or incomplete.
Do not require contact details, dates, or other execution details merely to
record a task, and do not invent missing details. Ask for clarification only
when the action itself is unclear or an update could affect the wrong task.

Base answers and confirmations on tool results. Claim an operation succeeded
only when its result has ok=true. Report missing information and failures
honestly; never invent facts, IDs, or completed actions. Keep responses concise.
"""

def run_agent(
    client: OpenAI,
    user_request: str,
    max_steps: int = 5,
    history: list | None = None,
) -> str:
    if max_steps <= 0:
        raise ValueError("max_steps must be a positive integer.")

    if history is None:
        history = []

    history.append({"role": "user", "content": user_request})

    i = 0 
    while i < max_steps:
        function_call = False
        i += 1
        response = client.responses.create(
            model="gpt-6-luna",
            tools=[CALCULATOR_TOOL, REMEMBER_TOOL, RECALL_TOOL, CREATE_TASK_TOOL, LIST_TASKS_TOOL, UPDATE_TASK_TOOL],
            input=history,
            instructions=system_prompt,
        )

        history += response.output
        print("\n**************************")
        print(f"Step {i} response output from the agent:")
        print(response.output)
        print("**************************\n")

        for item in response.output:
            if item.type == "function_call":
                function_call = True
                print("Tool name:", item.name)
                print("Arguments:", item.arguments)
                print("Call ID:", item.call_id)

                try:
                    arguments_dict = parse_tool_arguments(item.arguments)  # Parse the JSON string into a dictionary
                except ValueError as e:
                    history.append( 
                        {
                            "type": "function_call_output", 
                            "call_id": item.call_id, 
                            "output": json.dumps({
                                        "ok": False, 
                                        "error": {
                                            "type": type(e).__name__, 
                                            "message": str(e)
                                        }
                                    })
                        }
                    )
                    continue

                result = execute_tool_safely(item.name, arguments_dict)  # Execute the tool with the provided arguments
                print("Result of tool execution:", result)

                history.append(
                    {
                        "type": "function_call_output", 
                        "call_id": item.call_id, 
                        "output": json.dumps(result)
                    }
                )

        # if there is no function call in the response, we assume the agent has provided a final answer and return the output text
        if not function_call:
            print("i:", i)
            return response.output_text

        if i == max_steps:
            raise RuntimeError("Maximum steps reached. The agent did not provide a final answer.") 

def main():
    # Load variables from .env
    load_dotenv()

    # Load the history from a file if it exists
    history = load_history("conversation.json")

    # Read your API key
    api_key = os.getenv("OPENAI_API_KEY")

    # Initialize the client
    client = OpenAI(api_key=api_key)

    user_request = input("Enter your request: ")
    response = run_agent(client, user_request, history=history)
    print("\nFinal response from the agent:")
    print(response)

    # Save the updated history to a file
    save_history("conversation.json", history)

if __name__ == "__main__":
    main()
