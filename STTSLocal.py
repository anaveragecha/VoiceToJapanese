import io
import os
import subprocess
from threading import Thread
import time
import traceback
import wave
import keyboard
import pyaudio
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play
import requests
from enum import Enum
import romajitable
import dict
import translator
from timer import Timer
import whisper
import chatbot
import json
import streamChat
import soundfile as sf
import sounddevice as sd

def is_valid_path(path):
    return os.path.exists(path)

def load_config():
    try:
        with open("config.json", "r") as json_file:
            data = json.load(json_file)
            print(data)

            translator.deepl_api_key = data['deepl_api_key']
            translator.use_deepl = data['use_deepl']
            chatbot.openai_api_key = data['openai_api_key']
            chatbot.uri = data['custom_api_uri']
            global voice_vox_api_key
            voice_vox_api_key = data['voice_vox_api_key']
            global use_cloud_voice_vox
            use_cloud_voice_vox = data['use_cloud_voice_vox']
            global use_elevenlab
            use_elevenlab = data['use_elevenlab']
            global elevenlab_api_key
            elevenlab_api_key = data['elevenlab_api_key']
            streamChat.twitch_access_token = data['twitch_access_token']
            streamChat.twitch_channel_name = data['twitch_channel_name']
            streamChat.youtube_video_id = data['youtube_video_id']
            
            global use_englishNoJP
            use_englishNoJP = data['use_englishNoJP']
            global voice
            voice = data['voice']
            global emotion
            emotion = data['emotion']
            global ai_voice_api
            ai_voice_api = data['ai_voice_api']
            global aiVoiceCloningPath
            aiVoiceCloningPath = data['aiVoiceCloningPath']

            if (elevenlab_api_key == ''):
                elevenlab_api_key = os.getenv("ELEVENLAB_API_KEY")

    except:
        print("Unable to load JSON file.")
        print(traceback.format_exc())


def save_config(key, value):
    config = None
    try:
        with open("config.json", "r") as json_file:
            config = json.load(json_file)
            config[key] = value
            print(f"config[{key}] = {value}")
        with open("config.json", "w") as json_file:
            json_object = json.dumps(config, indent=4)
            json_file.write(json_object)
    except:
        print("Unable to load JSON file.")
        print(traceback.format_exc())


input_device_id = None
output_device_id = None

VOICE_VOX_URL_HIGH_SPEED = "https://api.su-shiki.com/v2/voicevox/audio/"
VOICE_VOX_URL_LOW_SPEED = "https://api.tts.quest/v1/voicevox/"
VOICE_VOX_URL_LOCAL = "127.0.0.1"

VOICE_OUTPUT_FILENAME = "audioResponse.wav"

use_elevenlab = False
elevenlab_api_key = ''
elevenlab_voiceid = ''
use_cloud_voice_vox = False
voice_vox_api_key = ''
speakersResponse = None
voicevox_server_started = False
speaker_id = 1
mic_mode = 'open mic'

use_englishNoJP = None
voice = "random"
emotion = "Happy"
ai_voice_api = None
aiVoiceCloningPath = None

MIC_OUTPUT_FILENAME = "PUSH_TO_TALK_OUTPUT_FILE.wav"
PUSH_TO_RECORD_KEY = '5'
use_ingame_push_to_talk_key = False
ingame_push_to_talk_key = 'f'

whisper_filter_list = ['you', 'thank you.', 'thanks for watching.']
pipeline_elapsed_time = 0
TTS_pipeline_start_time = 0
pipeline_timer = Timer()
step_timer = Timer()
model = None


def initialize_model():
    global model
    model = whisper.load_model("base")


def start_voicevox_server():
    global voicevox_server_started
    if (voicevox_server_started):
        return
    # start voicevox server
    subprocess.Popen("VOICEVOX\\run.exe")
    voicevox_server_started = True


def initialize_speakers():
    global speakersResponse
    if (not voicevox_server_started):
        start_voicevox_server()
    url = f"http://{VOICE_VOX_URL_LOCAL}:50021/speakers"
    while True:
        try:
            response = requests.request("GET", url)
            break
        except:
            print("Waiting for voicevox to start... ")
            time.sleep(0.5)
    speakersResponse = response.json()


def get_speaker_names(_englishNoJP=False):
    global speakersResponse
    if not _englishNoJP:
        if (speakersResponse == None):
            initialize_speakers()
        speakerNames = list(
            map(lambda speaker: speaker['name'],  speakersResponse))
    else:
        # custom api
        if is_valid_path(aiVoiceCloningPath):
            voice_folders = get_folders_in_directory(aiVoiceCloningPath + "results")
            speakerNames = voice_folders
        else:
            print("\nPath is invalid.\n")
        # custom api
    return speakerNames

def get_speaker_styles(speaker_name, _englishNoJP=False):
    global speakersResponse
    if not _englishNoJP:
        if (speakersResponse == None):
            initialize_speakers()
        speaker_styles = next(speaker['styles'] for speaker in speakersResponse if speaker['name'] == speaker_name)
    else:
        speaker_styles = [{'name': 'None', 'id': 0}, {'name': 'Sad', 'id': 1}, {'name': 'Angry', 'id': 2}, {'name': 'Disgusted', 'id': 3}, {'name': 'Arrogant', 'id': 4}, {'name': 'Happy', 'id': 5}]

    print(speaker_styles)
    return speaker_styles

def get_folders_in_directory(directory):
    folders = []
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            folders.append(item)
    return folders

recording = False
auto_recording = False
logging_eventhandlers = []

voice_name = '四国めたん'
input_language_name = 'English'

# Stores variable for play original function
last_input_text = ''
last_voice_param = None
last_input_language = ''

language_dict = dict.language_dict

def start_record_auto(custom=False):
    log_message("Recording...")
    global auto_recording
    auto_recording = True
    if custom == False:
        thread = Thread(target=start_STTS_loop)
        thread.start()
    elif custom == True:
        # custom api
        thread = Thread(target=lambda: start_STTS_loop(custom=True))
        thread.start()
        # custom api

def start_record_auto_chat(custom=False):
    log_message("Recording...")
    global auto_recording
    auto_recording = True
    if custom == False:
        thread = Thread(target=start_STTS_loop_chat)
        thread.start()
    elif custom == True:
        # custom api
        thread = Thread(target=lambda: start_STTS_loop_chat(custom=True))
        thread.start()
        # custom api

def stop_record_auto():
    global auto_recording
    auto_recording = False
    log_message("Recording Stopped")


def cloud_synthesize(text, speaker_id, api_key=''):
    global pipeline_elapsed_time
    url = ''
    if (api_key == ''):
        print('No api key detected, sending request to low speed server.')
        url = f"{VOICE_VOX_URL_LOW_SPEED}?text={text}&speaker={speaker_id}"
    else:
        print(
            f'Api key {api_key} detected, sending request to high speed server.')
        url = f"{VOICE_VOX_URL_HIGH_SPEED}?text={text}&speaker={speaker_id}&key={api_key}"
    print(f"Sending POST request to: {url}")
    response = requests.request(
        "POST", url)
    print(f'response: {response}')
    # print(f'response.content: {response.content}')
    wav_bytes = None
    if (api_key == ''):
        response_json = response.json()
        # print(response_json)

        try:
            # download wav file from response
            wav_url = response_json['wavDownloadUrl']
        except:
            print("Failed to get wav download link.")
            print(response_json)
            return
        print(f"Downloading wav response from {wav_url}")
        wav_bytes = requests.get(wav_url).content
    else:
        wav_bytes = response.content

    with open(VOICE_OUTPUT_FILENAME, "wb") as file:
        file.write(wav_bytes)


def syntheize_audio(text, speaker_id, _englishNoJP=False):
    global use_cloud_voice_vox, voice_vox_api_key
    global use_elevenlab
    if (use_elevenlab):
        elevenlab_synthesize(text)
    else:
        if (use_cloud_voice_vox):
            cloud_synthesize(text, speaker_id, api_key=voice_vox_api_key)
        else:
            if not _englishNoJP:
                local_synthesize(text, speaker_id)
            else:
                # custom api
                _englishNoJP_synthesize(text)
                # custom api



def local_synthesize(text, speaker_id):
    VoiceTextResponse = requests.request(
        "POST", f"http://127.0.0.1:50021/audio_query?text={text}&speaker={speaker_id}")
    AudioResponse = requests.request(
        "POST", f"http://127.0.0.1:50021/synthesis?speaker={speaker_id}", data=VoiceTextResponse)

    with open(VOICE_OUTPUT_FILENAME, "wb") as file:
        file.write(AudioResponse.content)

# custom api
def send_api_to_mrq(text="Prompt here"):
    # This uses the api from ai-voice-cloning by mrq
    response = requests.post(ai_voice_api, json={
        "data": [
            text, # represents text string of 'Input Prompt' Textbox component
            "hello world", # represents text string of 'Line Delimiter' Textbox component
            emotion, # represents selected choice of 'Emotion' Radio component
            "hello world", # represents text string of 'Custom Emotion' Textbox component
            voice, # represents selected choice of 'Voice' Dropdown component
            {"name":"audio.wav","data":"data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="},
            # represents audio data as object with filename and base64 string of 'Microphone Source' Audio component
            # ex: {"name":"output.wav","data":"data:audio/wav;base64,Microphone Souirce"}
            0, # represents numeric value of 'Voice Chunks' Number component
            1, # represents selected value of 'Candidates' Slider component
            0, # represents numeric value of 'Seed' Number component
            16, # represents selected value of 'Samples' Slider component
            30, # represents selected value of 'Iterations' Slider component
            0.2, # represents selected value of 'Temperature' Slider component
            "P", # represents selected choice of 'Diffusion Samplers' Radio component
            8, # represents selected value of 'Pause Size' Slider component
            0, # represents selected value of 'CVVP Weight' Slider component
            0.8, # represents selected value of 'Top P' Slider component
            1, # represents selected value of 'Diffusion Temperature' Slider component
            1, # represents selected value of 'Length Penalty' Slider component
            2, # represents selected value of 'Repetition Penalty' Slider component
            2, # represents selected value of 'Conditioning-Free K' Slider component
            ["Half Precision"], # represents list of selected choices of 'Experimental Flags' Checkboxgroup component
            False, # represents checked status of 'Use Original Latents Method (AR)' Checkbox component
            False, # represents checked status of 'Use Original Latents Method (Diffusion)' Checkbox component
        ]
    }).json()

    return response

def _englishNoJP_synthesize(text):
    global audiopath_from_englishNoJP

    data = send_api_to_mrq(text)["data"][2]['value']
    #data = send_api_to_mrq(text)
    print(data)
    # splits data
    path_parts = data.split("//")
    output_audioName = path_parts[-1]

    input_name = output_audioName
    parts = input_name.split("_")
    audio_folder_name = parts[0]

    # get audio file path
    audiopath_from_englishNoJP = aiVoiceCloningPath + "results\\" + audio_folder_name + "\\" + output_audioName
    
# custom api

def elevenlab_synthesize(message):

    global elevenlab_api_key
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{elevenlab_voiceid}'
    headers = {
        'accept': 'audio/mpeg',
        'xi-api-key': elevenlab_api_key,
        'Content-Type': 'application/json'
    }
    data = {
        'text': message,
        'voice_settings': {
            'stability': 0.75,
            'similarity_boost': 0.75
        }
    }
    print(f"Sending POST request to: {url}")
    response = requests.post(url, headers=headers, json=data, stream=True)
    print(response)
    audio_content = AudioSegment.from_file(
        io.BytesIO(response.content), format="mp3")
    audio_content.export(VOICE_OUTPUT_FILENAME, 'wav')
    # with open(VOICE_OUTPUT_FILENAME, "wb") as file:
    #     file.write(audio_content.)


def PlayAudio(_englishNoJP=False):
    # voiceLine = AudioSegment.from_wav(VOICE_OUTPUT_FILENAME)
    # play(voiceLine)
    # open the file for reading.

    if _englishNoJP == False:
        wf = wave.open(VOICE_OUTPUT_FILENAME, 'rb')
    else:
        wf = wave.open(VOICE_OUTPUT_FILENAME, 'rb')

    # create an audio object
    p = pyaudio.PyAudio()

    global output_device_id
    # length of data to read.
    chunk = 1024
    # open stream based on the wave object which has been input.
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True,
                    output_device_index=output_device_id)

    # read data (based on the chunk size)
    data = wf.readframes(chunk)

    # play stream (looping from beginning of file to the end)
    while data:
        # writing to the stream is what *actually* plays the sound.
        stream.write(data)
        data = wf.readframes(chunk)

    # cleanup stuff.
    wf.close()
    stream.close()
    p.terminate()

# custom api
def PlayAudio_englishNoJP(output_file_path):
    # Read the audio file
    audio_data, sample_rate = sf.read(output_file_path)

    # Play the audio
    sd.play(audio_data, sample_rate)
    sd.wait()
# custom api

def push_to_talk():
    while True:
        a = keyboard.read_key()
        if (a == PUSH_TO_RECORD_KEY):
            log_message(f"push to talk started...")
            audio = pyaudio.PyAudio()
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 44100
            # Open audio stream
            global input_device_id
            stream = audio.open(format=FORMAT, channels=CHANNELS,
                                rate=RATE, input=True,
                                frames_per_buffer=CHUNK, input_device_index=input_device_id)

            # Initialize frames array to store audio data
            frames = []

            # Record audio data
            while True:
                data = stream.read(CHUNK)
                frames.append(data)
                if not keyboard.is_pressed(PUSH_TO_RECORD_KEY):
                    break

            # Stop recording and close audio stream
            log_message("push to talk ended")
            stream.stop_stream()
            stream.close()

            # Save recorded audio data to file
            audio_segment = AudioSegment(
                data=b''.join(frames),
                sample_width=audio.get_sample_size(FORMAT),
                frame_rate=RATE,
                channels=CHANNELS
            )

            audio_segment.export(MIC_OUTPUT_FILENAME, format="wav")
            break


def start_STTS_loop(custom=False):
    global auto_recording
    while auto_recording:
        if not custom:
            start_STTS_pipeline()
        else:
            # custom api
            start_STTS_pipeline(custom=True)
            # custom api

def start_STTS_loop_chat(custom=False):
    global auto_recording
    while auto_recording:
        if custom == False:
            start_STTS_pipeline(use_chatbot=True)
        else:
            # custom api
            start_STTS_pipeline(use_chatbot=True, custom=True)
            # custom api

def start_STTS_pipeline(use_chatbot=False, custom=False):
    global pipeline_elapsed_time
    global step_timer
    global pipeline_timer
    global mic_mode
    audio = None
    if (mic_mode == 'open mic'):
        # record audio
        # obtain audio from the microphone
        r = sr.Recognizer()
        global input_device_id
        with sr.Microphone(device_index=input_device_id) as source:
            # log_message("Adjusting for ambient noise...")
            # r.adjust_for_ambient_noise(source)
            log_message("Say something!")
            audio = r.listen(source)

        global auto_recording
        if not auto_recording:
            return

        with open(MIC_OUTPUT_FILENAME, "wb") as file:
            file.write(audio.get_wav_data())
    elif (mic_mode == 'push to talk'):
        push_to_talk()
    log_message("recording compelete, sending to whisper")

    # send audio to whisper
    pipeline_timer.start()
    step_timer.start()
    input_text = ''
    try:
        global model
        if (model == None):
            initialize_model()
        global input_language_name
        print(input_language_name)
        audio = whisper.load_audio(MIC_OUTPUT_FILENAME)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(model.device)
        options = whisper.DecodingOptions(
            language=input_language_name.lower(), without_timestamps=True, fp16=False if model.device == 'cpu' else None)
        result = whisper.decode(model, mel, options)
        input_text = result.text
    except sr.UnknownValueError:
        log_message("Whisper could not understand audio")
    except sr.RequestError as e:
        log_message("Could not request results from Whisper")
    global whisper_filter_list
    if (input_text == ''):
        return
    log_message(f'Input: {input_text} ({step_timer.end()}s)')

    print(f'looking for {input_text.strip().lower()} in {whisper_filter_list}')
    if (input_text.strip().lower() in whisper_filter_list):
        log_message(f'Input {input_text} was filtered.')
        return
    with open("Input.txt", "w", encoding="utf-8") as file:
        file.write(input_text)
    pipeline_elapsed_time += pipeline_timer.end()
    if (use_chatbot and not custom):
        log_message("recording compelete, sending to chatbot")
        chatbot.send_user_input(input_text)
    elif (use_chatbot and custom):
        # custom api
        log_message("recording compelete, sending to chatbot")
        chatbot.send_user_input_custom_api(input_text)
        # custom api
    else:
        start_TTS_pipeline(input_text, _englishNoJP=use_englishNoJP)

def start_TTS_pipeline(input_text, _englishNoJP=False):
    global voice_name
    global speaker_id
    global pipeline_elapsed_time
    pipeline_timer.start()
    inputLanguage = language_dict[input_language_name][:2]
    if (use_elevenlab) or _englishNoJP:
        outputLanguage = 'en'
    else:
        outputLanguage = 'ja'
    print(f"inputLanguage: {inputLanguage}, outputLanguage: {outputLanguage}")
    translate = inputLanguage != outputLanguage
    if (translate):
        step_timer.start()
        input_processed_text = translator.translate(
            input_text, inputLanguage, outputLanguage)
        log_message(
            f'Translation: {input_processed_text} ({step_timer.end()}s)')
    else:
        input_processed_text = input_text

    # filter special characters
    filtered_text = ''
    for char in input_processed_text:
        if char != "*":
            filtered_text += char

    with open("translation.txt", "w", encoding="utf-8") as file:
        file.write(filtered_text)
    step_timer.start()

    if not _englishNoJP or not use_englishNoJP:
        syntheize_audio(filtered_text, speaker_id)
    else:
        syntheize_audio(filtered_text, speaker_id, _englishNoJP=True)

    log_message(
        f"Speech synthesized for text [{filtered_text}] ({step_timer.end()}s)")
    log_message(
        f'Total time: ({round(pipeline_elapsed_time + pipeline_timer.end(),2)}s)')
    print(f"ingame_push_to_talk_key: {ingame_push_to_talk_key}")

    global use_ingame_push_to_talk_key
    if (use_ingame_push_to_talk_key and ingame_push_to_talk_key != ''):
        keyboard.press(ingame_push_to_talk_key)

    if not _englishNoJP or not use_englishNoJP:
        PlayAudio()
    else:
        # custom api
        PlayAudio_englishNoJP(audiopath_from_englishNoJP)
        # custom api

    if (use_ingame_push_to_talk_key and ingame_push_to_talk_key != ''):
        keyboard.release(ingame_push_to_talk_key)

    global last_input_text
    last_input_text = input_text
    global last_input_language
    last_input_language = inputLanguage
    global last_voice_param
    last_voice_param = speaker_id
    pipeline_elapsed_time = 0


def playOriginal():
    global last_input_text
    global last_voice_param
    global last_input_language
    global input_language_name
    inputLanguage = language_dict[input_language_name][:2]
    last_input_text_processed = ''
    if (last_input_language != 'en'):
        last_input_text_processed = translator.translate(
            last_input_text, inputLanguage, 'en')
    else:
        last_input_text_processed = last_input_text
    text_ja = romajitable.to_kana(last_input_text_processed).katakana
    text_ja = text_ja.replace('・', '')
    syntheize_audio(text_ja, last_voice_param)
    log_message(f'playing input: {text_ja}')


def log_message(message_text):
    print(message_text)
    global logging_eventhandlers
    for eventhandler in logging_eventhandlers:
        eventhandler(message_text)


def change_input_language(input_lang_name):
    global input_language_name
    input_language_name = input_lang_name
