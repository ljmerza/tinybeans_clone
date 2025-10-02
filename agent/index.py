from dotenv import load_dotenv
import os

# auto looks for this ENV var too
load_dotenv()
my_api_key = os.getenv("ANTHROPIC_API_KEY")
print(my_api_key)

from anthropic import Anthropic

client = Anthropic(
    api_key=my_api_key
)

our_first_message = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=1000,
    messages=[
        {"role": "user", "content": "Hi there! Please write me a haiku about a pet chicken"}
    ]
)

print(our_first_message.content[0].text)

def translate(word, language):
  response = client.messages.create(
      model="claude-3-opus-20240229",
      max_tokens=1000,
      messages=[
          {"role": "user", "content": f"Translate the word {word} into {language}.  Only respond with the translated word, nothing else"}
      ]
  )
  return response.content[0].text 

def chat_bot(prompt):
    conversation_history = []

    while True:
        user_input = input("User: ")
        
        if user_input.lower() == "quit":
            print("Conversation ended.")
            break
        
        conversation_history.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            messages=conversation_history,
            max_tokens=500
        )

        assistant_response = response.content[0].text
        print(f"Assistant: {assistant_response}")
        conversation_history.append({"role": "assistant", "content": assistant_response})

def generate_questions(topic, num_questions=3):
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=500,
        system=f"You are an expert on {topic}. Generate thought-provoking questions about this topic.",
        messages=[
            {"role": "user", "content": f"Generate {num_questions} questions about {topic} as a numbered list."}
        ],
        stop_sequences=[f"{num_questions+1}."]
    )
    print(response.content[0].text)

def streaming_response():
    stream = client.messages.create(
        messages=[
            {
                "role": "user",
                "content": "How do large language models work?",
            }
        ],
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        stream=True,
    )
    for event in stream:
        if event.type == "message_start":
            input_tokens = event.message.usage.input_tokens
            print("MESSAGE START EVENT", flush=True)
            print(f"Input tokens used: {input_tokens}", flush=True)
            print("========================")
        elif event.type == "content_block_delta":
            print(event.delta.text, flush=True, end="")
        elif event.type == "message_delta":
            output_tokens = event.usage.output_tokens
            print("\n========================", flush=True)
            print("MESSAGE DELTA EVENT", flush=True)
            print(f"Output tokens used: {output_tokens}", flush=True)