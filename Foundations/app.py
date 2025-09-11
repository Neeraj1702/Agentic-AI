from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from PyPDF2 import PdfReader
import gradio as gr


load_dotenv(override=True)

pushover_user=os.getenv("PUSHOVER_USER")
pushover_token=os.getenv("PUSHOVER_TOKEN")
pushover_url="https://api.pushover.net/1/messages.json"

def push(text):
    requests.post(
        pushover_url,
        data={
            "token":pushover_token,
            "user": pushover_user,
            "message": text
        }
    )

def record_user_details(email, name="Name not Provided", notes="not Provided"):
    push(f"Recording interests from {name} with email {email} and notes {notes}")
    return {"Recorded": "OK"}

def record_unknown_question(question):
    push(f"Recording {question} asked that I couldn't answer")
    return {"Recorded": "OK"}

record_user_details_json= {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "decription": " The user's name, if they provided it "
            },
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }   
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answeres as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties":{
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required":["question"],
        "additionalProperties": False
    }
}

tools=[{"type": "function", "function": record_user_details_json},
      {"type": "function", "function": record_unknown_question_json}]


class Me:

    def __init__(self):
        self.openai=OpenAI()
        self.name="Neeraj"
        reader=PdfReader("me/Neeraj Resume.pdf")
        self.resume=""
        for page in reader.pages:
            text= page.extract_text()
            if text:
                self.resume += text

        with open("me/summary.txt", "r", encoding='utf-8') as f:
            self.summary=f.read()

    # this function can take a list of tool calls, and run them.
    def handle_tool_calls(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name=tool_call.function.name
            arguments= json.loads(tool_call.function.arguments)
            print(f"Tool called : {tool_name}", flush=True)

        # if tool_name == "record_user_details":
        #     result= record_user_details(**arguments)
        # elif tool_name == "record_unknown_questions":
        #     result = record_unknown_questions(**arguments)

            tool=globals().get(tool_name)
            result= tool(**arguments) if tool else {}

            results.append({"role": "tool", "content": json.dumps(result),"tool_call_id": tool_call.id})
        return results

    def system_prompt(self):
        system_prompt= f"You are acting as {self.name}. You are answering questions on {self.name}'s Website, \
    particularly questions related to {self.name}'s carrer, background, skills and experience. \
    Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
    Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
    If you don't know answer to any question , use your record_unknown_question tool to record the question that you couldn't answer. \
    If user is enaging in discussion , try to steer them towards getting in touch via email; ask for their email and record it using your tools"

        system_prompt+=f"\n\n ## Summary:\n{self.summary}\n\n##{self.resume}\n\n"
        system_prompt+=f"with this context, please chat with the user, always staying in character as {self.name}"
        return system_prompt

    def chat(self,message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
        # this is the call to LLm -- see that we pass in the tools json
            response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )
        
            finish_reason = response.choices[0].finish_reason

        #If the LLm want to call a tool we do that!
            if finish_reason=="tool_calls":
                message= response.choices[0].message
                tool_calls = message.tool_calls
                results= self.handle_tool_calls(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        return response.choices[0].message.content

me = Me()
demo=gr.ChatInterface(me.chat, type="messages")
if __name__ == "__main__":
    demo.launch()