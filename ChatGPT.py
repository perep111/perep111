import asyncio
import os
from gtts import gTTS
from aiogram.types import ChatActions
from yoomoney import Client
from yoomoney import Quickpay
import uuid
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import Voice
import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import openai
from pydub import AudioSegment
import io
from spacy.lang.ru import Russian
import replicate
import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv('TOKEN')
client = Client(TOKEN)

REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')
Y_TOKEN = os.getenv('Y_TOKEN')

# Токен вашего телеграм бота
API_TOKEN = os.getenv('API_TOKEN')

openai.api_key = os.getenv('API_OPENI_TOKEN')

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)
nlp = Russian()


subscribers = []

message_log = [
    {"role": "system", "content": "You are a helpful assistant."}
]


kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
menu = KeyboardButton(text='/menu')
help1 = KeyboardButton(text='/help')
kb.add(menu,help1)


def pay(comment):
    quickpay = Quickpay(
                receiver="4100118220335308",
                quickpay_form="shop",
                targets="Sponsor this project",
                paymentType="AC",
                successURL='https://t.me/perep111_bot',
                sum=2,
                label=comment
                )

    return quickpay


def send_message(message_log):
    # Use OpenAI's ChatCompletion API to get the chatbot's response
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # The name of the OpenAI chatbot model to use
        messages=message_log,   # The conversation history up to this point, as a list of dictionaries
        max_tokens=300,        # The maximum number of tokens (words or subwords) in the generated response
        stop=None,              # The stopping sequence for the generated response, if any (not used here)
        temperature=0.7,        # The "creativity" of the generated response (higher temperature = more creative)
    )

    # Find the first response from the chatbot that has text in it (some responses may not have text)
    for choice in response.choices:
        if "text" in choice:
            return choice.text

    # If no response with text is found, return the first response's content (which may be empty)
    return response.choices[0].message.content


async def audio_to_text(file_path: str) -> str:
    """Принимает путь к аудио файлу, возвращает текст файла."""
    with open(file_path, "rb") as audio_file:
        transcript = await openai.Audio.atranscribe(
            "whisper-1", audio_file
        )
    return transcript["text"]


async def save_voice_as_mp3(bot: Bot, voice: Voice) -> str:
    """Скачивает голосовое сообщение и сохраняет в формате mp3."""
    voice_file_info = await bot.get_file(voice.file_id)
    voice_ogg = io.BytesIO()
    await bot.download_file(voice_file_info.file_path, voice_ogg)

    voice_mp3_path = f"voice_files/voice-{voice.file_unique_id}.mp3"
    AudioSegment.from_file(voice_ogg, format="ogg").export(
        voice_mp3_path, format="mp3"
    )
    return voice_mp3_path


@dp.message_handler(commands=['start'])
async def process_start_command(msg: types.Message):
    id = str(msg.from_user.id)
    if id in subscribers:
        username = msg.from_user.username
        await msg.reply(f'Привет {username}, можешь задать свой вопрос текстом,\n'
                        'а можешь записать голосовое сообщение,\n\n'
                        '✉ Чтобы получить текстовый ответ, просто напишите в чат ваш вопрос.\n\n'
                        '🎼 Если запишешь вопрос голосовым сообщением, получешь в ответ тоже голосовое сообщение\n\n'
                        '🌅 Чтобы создать изображение с помощью Midjourney,'
                        ' начни запрос с команды /imagine а затем добавьте описание')

    else:
        await msg.answer('Вы находитесь в боте ChatGPT-4\n'
                         'Для начала работы вам необходимо оплатить подписку,\n'
                         'нажмите кнопку /menu', reply_markup=kb)


@dp.message_handler(commands=['menu'])
async def menu_message(msg: types.Message, state: FSMContext):
    passvord = str(uuid.uuid4())
    keyboard = InlineKeyboardMarkup()
    btn_payment = InlineKeyboardButton('Оплатить', callback_data='payment', url=pay(comment=passvord).redirected_url)
    btn_cancel = InlineKeyboardButton('Отмена', callback_data='cancel')
    verification = InlineKeyboardButton('ПРОВЕРКА_ОПЛАТЫ', callback_data='verification')
    keyboard.add(btn_payment, btn_cancel)
    keyboard.row(verification)
    # print(passvord)
    async with state.proxy() as data:
        data['passvord'] = passvord

    # print(passvord)

    await msg.answer(text='После оплаты подписки жми \n'
                     'ПРОВЕРКА ОПЛАТЫ', reply_markup=keyboard)


@dp.callback_query_handler(text='cancel')
async def push_cancel(call: types.CallbackQuery):
    await call.answer()
    await call.message.answer('Вы отказались от подписки\n'
                              'Для дальнейшей работы с ботом необходима подписка\n'
                              'нажмите /menu', reply_markup=kb)
    await call.message.delete()


@dp.callback_query_handler(text='verification')
async def push_payment(call: types.CallbackQuery, state: FSMContext):
    username = call.from_user.username
    async with state.proxy() as data:
         passvord = data['passvord']
    try:
        history = client.operation_history(label=passvord)

        if not history.operations:
            await call.message.answer('Оплаты не было,\n'
                                      'Для дальнейшей работы с ботом необходима подписка\n'
                                      'нажмите /menu', reply_markup=kb)
            await call.message.delete()

        else:
            for i in history.operations:
                if i.status == 'success':
                    await call.message.answer('Вы подписались')
                    subscribers.append(str(call.from_user.id))
                    await bot.send_message(chat_id='1348491834', text='Пришли бабосики')
                    await call.message.answer(f'Привет {username}, можешь задать свой вопрос текстом,\n'
                                              f'а можешь записать голосовое сообщение,\n\n'
                                              f'✉ Чтобы получить текстовый ответ, просто напишите в чат ваш вопрос.\n\n'
                                              f'🎼 Если запишешь вопрос голосовым сообщением, получешь в ответ тоже'
                                              f' голосовое сообщение\n\n'
                                              f'🌅 Чтобы создать изображение с помощью Midjourney, '
                                              f'начни запрос с команды /imagine а затем добавьте описание')
                    # print(subscribers)
                    await state.finish()

    except Exception as e:
        await call.answer(str(e))


@dp.message_handler(commands=['help'])
async def help_message(msg: types.Message):
    await msg.answer('Вы находитесь в боте ChatGPT-4\n'
                     'Для взаимодействия с ботом необходима подписка\n'
                     'Если вы оформили подписку и она не активна напишите '
                     'пожалуйста администраторам @f_o_x_y_s',
                     reply_markup=keyboard_check)
    await msg.delete()

keyboard_check = InlineKeyboardMarkup()
btn_check = InlineKeyboardButton('Проверить подписку', callback_data='check')
keyboard_check.add(btn_check)


@dp.callback_query_handler(text='check')
async def check_sub(call: types.CallbackQuery):
    await call.answer()
    id = str(call.from_user.id)
    if id in subscribers:
        await call.message.answer('У вас активна подписка')
        await call.message.delete()
    else:
        await call.message.answer('Подписка не активна\n'
                                  'что бы оплатить подписку,\n'
                                  'нажми /menu', reply_markup=kb)
        await call.message.delete()


@dp.message_handler(commands=['imagine'])
async def answer_gpt(msg: types.Message):
    id = str(msg.from_user.id)
    if id in subscribers:
        await bot.send_chat_action(msg.chat.id, ChatActions.TYPING)
        await asyncio.sleep(3)
        await msg.answer('5 сек, генерирую картинку...')
        prompt_translete = f'переведи на английский язык{msg.text.replace("/imagine", "")}'
        response_translete = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt_translete,
            temperature=0.5,
            max_tokens=200,
        )
        message = response_translete.choices[0].text.strip()
        # print(prompt_translete)

        output = replicate.Client(api_token=REPLICATE_API_TOKEN).run(
             "tstramer/midjourney-diffusion:436b051ebd8f68d23e83d22de5e198e0995357afef113768c20f0b6fcef23c8b",
            input={"prompt": 'mdjrny-v4' + message}
        )

    # print(message)
        image_url = output[0]
        await bot.send_chat_action(msg.chat.id, ChatActions.UPLOAD_PHOTO)
        await asyncio.sleep(4)
        await bot.send_photo(chat_id=msg.chat.id, photo=image_url)

    else:
        await msg.answer('Для начала работы вам необходимо оплатить подписку,\n'
                             'нажмите кнопку /menu', reply_markup=kb)


@dp.message_handler(content_types=types.ContentType.VOICE)
async def process_message(message: types.Message):
    id = str(message.from_user.id)
    if id in subscribers:
        """Принимает все голосовые сообщения и отвечает эхо."""
        voice_path = await save_voice_as_mp3(bot, message.voice)
        transcripted_voice_text = await audio_to_text(voice_path)
        voce_name = f'{str(message.from_user.id)}.mp3'

        if transcripted_voice_text:
            await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
            await asyncio.sleep(3)
            await message.answer("ИИ думает...")
            for file in os.scandir('voice_files'):
                os.remove(file.path)
        else:
            await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
            await asyncio.sleep(3)
            await message.reply('Извините, не распознали ваш запрос\n'
                                'попробуйте еще раз...')

        # message_log = [
        #     {"role": "system", "content": "You are a helpful assistant."}
        # ]

        first_request = True

        if first_request:
            user_input = transcripted_voice_text
            message_log.append({"role": "user", "content": user_input})
            response = send_message(message_log)
            message_log.append({"role": "assistant", "content": response})
            first_request = False

        else:
            user_input = transcripted_voice_text

            message_log.append({"role": "user", "content": user_input})
            response = send_message(message_log)
            message_log.append({"role": "assistant", "content": response})

        # print(message_log)
        replay_audio = gTTS(text=response, lang="ru", slow=False)
        replay_audio.save("voice_mp3/" + voce_name)

        with open("voice_mp3/" + voce_name, 'rb') as voice:
            await bot.send_chat_action(message.chat.id, ChatActions.RECORD_AUDIO,)
            await asyncio.sleep(3)
            await bot.send_voice(chat_id=message.from_user.id, voice=voice)
        for file in os.scandir('voice_mp3'):
            os.remove(file.path)

    else:
        await message.answer('Для начала работы вам необходимо оплатить подписку,\n'
                             'нажмите кнопку /menu', reply_markup=kb)


@dp.message_handler(content_types=types.ContentType.TEXT)
async def ansver_gpt_text(message: types.Message):
    id = str(message.from_user.id)
    if id in subscribers:
        await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
        await asyncio.sleep(3)
        await message.answer("ИИ думает...")
        # message_log = [
        #     {"role": "system", "content": "You are a helpful assistant."}
        # ]

        first_request = True

        if first_request:
            user_input = message.text
            message_log.append({"role": "user", "content": user_input})
            response = send_message(message_log)
            message_log.append({"role": "assistant", "content": response})
            first_request = False

        else:
            user_input = message.text

            message_log.append({"role": "user", "content": user_input})
            response = send_message(message_log)
            message_log.append({"role": "assistant", "content": response})

        # print(message_log)
        await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
        await asyncio.sleep(3)
        await message.answer(response)
    else:
        await message.answer('Для начала работы вам необходимо оплатить подписку,\n'
                             'нажмите кнопку /menu', reply_markup=kb)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)