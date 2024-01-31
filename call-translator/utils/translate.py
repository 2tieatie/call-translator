import datetime
from io import BytesIO

import deepl
import requests
import os
from dotenv import load_dotenv
from gtts import gTTS
from pydub import AudioSegment
from deepgram import DeepgramClient, DeepgramClientOptions, PrerecordedOptions



def load_env():
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.env')
    load_dotenv(dotenv_path)


load_env()


class Translator:
    LLM_TOKEN = os.getenv('LLM_TOKEN')
    DEEPL_TOKEN = os.getenv('DEEPL_TOKEN')
    DEEPGRAM_TOKEN = os.getenv('DEEPGRAM_TOKEN')
    deepgram = DeepgramClient(api_key=DEEPGRAM_TOKEN)
    MIMETYPE = 'webm'
    options = PrerecordedOptions(
        model="nova-2",
        smart_format=True,
        language='ru'
    )

    @classmethod
    def recognize_speech(cls, audio_bytes, language='ru', task='transcribe'):
        source = {"buffer": audio_bytes, "mimetype": 'audio/' + cls.MIMETYPE}
        try:
            cls.options.language = language
            res = cls.deepgram.listen.prerecorded.v("1").transcribe_file(source, cls.options)
            data = res.results.channels[0].alternatives[0]
            text = data.transcript
            confidence = data.confidence
            print({
                'status': 'succeeded',
                'text': text,
            })
            return {
                'status': 'succeeded',
                'text': text,
            }
        except Exception as ex:
            return {
                'status': f'error {ex}',
                'text': [],
            }

        # url = 'https://api.deepinfra.com/v1/inference/openai/whisper-large'
        # headers = {
        #     "Authorization": f"bearer {cls.LLM_TOKEN}"
        # }
        # files = {
        #     'audio': ('my_voice.mp3', audio_bytes)
        # }
        # data = {
        #     'language': language,
        #     'task': task,
        #     'temperature': 0.1,
        #     'no_speech_threshold': 0.6,
        # }
        # response = requests.post(url, headers=headers, files=files, data=data)
        # result = response.json()
        # if result.get('detail'):
        #     if result.get('detail').get('error'):
        #         return {
        #             'status': 'error',
        #         }
        #
        # print(result)


        # return {
        #     'status': result['inference_status']['status'],
        #     'text': result['text'],
        #     'language': result['language'],
        #     'segments': result['segments'],
        # }

    @classmethod
    def translate(cls, audio_bytes: object, deepl_language: str, deepgram_language: str, no_speech_prob: float = 0.1) -> object:
        data = cls.recognize_speech(audio_bytes=audio_bytes, language=deepgram_language)
        status = data['status']
        if status != 'succeeded':
            return {'status': 'error'}

        if not data['text']:
            return {'status': 'empty text'}

        text = data['text']
        if not text:
            return {'status': 'empty text'}

        result = deepl.Translator(cls.DEEPL_TOKEN) \
            .translate_text(
            text=text, target_lang=deepl_language
        )
        return {'status': 'success', 'text': result.text.strip()}

    @classmethod
    def make_audio(cls, text: str, language='en'):
        tts = gTTS(text=text, lang=language)
        audio_stream = BytesIO()
        tts.write_to_fp(audio_stream)
        audio_stream.seek(0)
        return audio_stream.getvalue()
