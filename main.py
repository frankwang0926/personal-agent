from tools import CALCULATOR_TOOL, execute_tool, execute_tool_safely
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

system_prompt = (
                "You are a calculator assistant. "
                "Use the calculator tool for arithmetic. "
                "Base your final answer on the returned tool result."
            )

def run_agent(
    client: OpenAI,
    user_request: str,
    max_steps: int = 5,
) -> str:
    if max_steps <= 0:
        raise ValueError("max_steps must be a positive integer.")
    
    input_list = [{"role": "user", "content": user_request}]
    i = 0 
    while i < max_steps:
        function_call = False
        i += 1
        response = client.responses.create(
            model="gpt-6-luna",
            tools=[CALCULATOR_TOOL],
            input=input_list,
            instructions=system_prompt,
        )

        input_list += response.output
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

                result = execute_tool_safely(item.name, json.loads(item.arguments))  # Execute the tool with the provided arguments
                print("Result of tool execution:", result)

                input_list.append(
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

    # Read your API key
    api_key = os.getenv("OPENAI_API_KEY")

    # Initialize the client
    client = OpenAI(api_key=api_key)

    user_request = input("Enter your request: ")
    response = run_agent(client, user_request)
    print("\nFinal response from the agent:")
    print(response)

if __name__ == "__main__":
    main()