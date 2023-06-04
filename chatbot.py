import os
import re
import traceback
import requests
import json
import STTSLocal as STTS

HOST = 'localhost:5000'
URI = f'http://{HOST}/api/v1/chat'

AI_RESPONSE_FILENAME = 'ai-response.txt'
character_limit = 3000

lore = ''
try:
    with open('./lore.txt', 'r', encoding='utf-8') as file:
        #lore = file.read()
        lore = 'Name\n' #not needed
except Exception:
    print("error when reading lore.txt")
    print(traceback.format_exc())
lore = lore.replace('\n', '')

message_log = [
    {"role": "system", "content": lore},
    # {"role": "user", "content": lore},
]

logging_eventhandlers = []

history = {'internal': [], 'visible': []}

def send_user_input(user_input):
    message_log.append({"role": "user", "content": user_input})
    log_message(f'user: {user_input}')

    request = {
        'user_input': user_input,
        'history': history,
        'mode': 'chat',  # Valid options: 'chat', 'chat-instruct', 'instruct'
        'character': 'Your character', # your character from the oobabooga text-gen repo
        'instruction_template': 'None',
        'your_name': 'You',

        'regenerate': False,
        '_continue': False,
        'stop_at_newline': False,
        'chat_prompt_size': 2048,
        'chat_generation_attempts': 1,
        'chat-instruct_command': 'Continue the chat dialogue below. Write a single reply for the character "".\n\n',

        'max_new_tokens': 200,
        'do_sample': True,
        'temperature': 0.6,
        'top_p': 0.9,
        'typical_p': 1,
        'epsilon_cutoff': 0,  # In units of 1e-4
        'eta_cutoff': 0,  # In units of 1e-4
        'tfs': 1,
        'top_a': 0,
        'repetition_penalty': 1.15,
        'top_k': 100,
        'min_length': 0,
        'no_repeat_ngram_size': 0,
        'num_beams': 1,
        'penalty_alpha': 0,
        'length_penalty': 1,
        'early_stopping': False,
        'mirostat_mode': 0,
        'mirostat_tau': 5,
        'mirostat_eta': 0.1,
        'seed': -1,
        'add_bos_token': True,
        'truncation_length': 2048,
        'ban_eos_token': False,
        'skip_special_tokens': True,
        'stopping_strings': []
    }

    response = requests.post(URI, json=request)

    if response.status_code == 200:
        result = response.json()['results'][0]['history']
        
        text_response = result['visible'][-1][1]
        message_log.append({"role": "assistant", "content": text_response})
        log_message(f'AI: {text_response}')

        with open(AI_RESPONSE_FILENAME, "w", encoding="utf-8") as file:
            separated_text = separate_sentences(text_response)
            file.write(separated_text)

        STTS.start_TTS_pipeline(text_response)

        return text_response
    else:
        return None


def log_message(message_text):
    print(message_text)
    global logging_eventhandlers
    for eventhandler in logging_eventhandlers:
        eventhandler(message_text)


def separate_sentences(text):
    # Define common sentence-ending punctuation marks
    sentence_enders = re.compile(r'[.!?]+')

    # Replace any newline characters with spaces
    text = text.replace('\n', ' ')

    # Split text into list of strings at each sentence-ending punctuation mark
    sentences = sentence_enders.split(text)

    # Join sentences with newline character
    result = '\n'.join(sentences)

    return result
