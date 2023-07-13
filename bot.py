import db.db as db
import logging
import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import RegexpCommandsFilter
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from exceptions import *
from dotenv import dotenv_values


class states(StatesGroup):
    INPUT_LANG = State()
    INPUT_LANG_FOR_INSERT = State()
    INPUT_WORD = State()
    INPUT_TRANSLATION = State()

config = dotenv_values('.env')
API_TOKEN = config['TG_API']

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

help_cmd = """
/random\\_5_ru \\- введенное число случайных слов из ru словаря
/random\\_5_eng \\- введенное число случайных слов из ru словаря
/select _СЛОВО_ \\- Получить перевод/определение
/select\\_all \\- Получить все слова в словаре
/add _СЛОВО_;_ТИП_;_ПЕРЕВОД_ \\- Добавить новое слово
/add\\_def _СЛОВО_;_ТИП_;_НОВЫЙ ПЕРЕВОД_ \\- Добавить перевод/определение
/edit\\_def _СЛОВО_;_ТИП_;_НОВЫЙ ПЕРЕВОД_ \\- Изменить перевод/определение
"""
# TODO при вызове /edit_def нужно вывести текущее определение


@dp.message_handler(commands=['start', 'help'])
async def description(message: types.message):
    await message.answer(help_cmd, parse_mode='MarkdownV2')


@dp.message_handler(RegexpCommandsFilter(regexp_commands=['random']))
async def random_n(message: types.Message, state: FSMContext):
    buttons = [[types.KeyboardButton('ru'), types.KeyboardButton('eng')]]
    keyboard = types.ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await message.answer("Выберите язык:", reply_markup=keyboard)
    await states.INPUT_LANG.set()
    await state.update_data(command=message.text)
    await message.answer(prep_terms(db.select_n_random(int(message.text.split('_')[1])))) # FIXME: определить язык


@dp.message_handler(commands=['select'])
async def get_definition(message: types.message):
    word = message.get_args()
    if not word:
        await message.reply("/select _СЛОВО_", parse_mode='markdownv2')
        return
    definition = db.select_all_definitions(word)
    if not definition:
        await message.answer('Такого слова нет в словаре')
        return
    await message.answer(word.upper() + '\n' + '\n'.join(list(map(lambda x: f'{x[0]}', definition))))


@dp.message_handler(commands=['select_all'])
async def all_words(message: types.message):
    await message.answer(prep_terms(db.select_all())) # FIXME: определить язык


@dp.message_handler(commands=['add'])
async def add(message: types.Message):
    buttons = [[types.KeyboardButton('ru'), types.KeyboardButton('eng')]]
    keyboard = types.ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await message.answer("Выберите язык:", reply_markup=keyboard)
    await states.INPUT_LANG_FOR_INSERT.set()


@dp.message_handler(state=states.INPUT_LANG_FOR_INSERT)
async def process_lang(message: types.Message, state: FSMContext):
    lang = message.text
    await message.answer("Введите слово:", reply_markup=types.ReplyKeyboardRemove())
    await states.INPUT_WORD.set()
    await state.update_data(lang=lang)


@dp.message_handler(state=states.INPUT_WORD)
async def process_word(message: types.Message, state: FSMContext):
    word = message.text
    await message.answer("Введите перевод:")
    await states.INPUT_TRANSLATION.set()
    await state.update_data(word=word)


@dp.message_handler(state=states.INPUT_TRANSLATION)
async def process_definition(message: types.Message, state: FSMContext):
    definition = message.text
    data = await state.get_data()
    lang = data.get('lang')
    word = data.get('word')
    db.insert(word=word, definition=definition, lang=lang)
    await state.finish()
    await message.reply("Добавлено\n" + f'{word.upper()} - {definition} ')


@dp.message_handler(commands=['add_def'])
async def add_def(message: types.Message):
    try:
        word, type_, additional_definition = message.get_args().split(';')
    except ValueError:
        await message.reply("/add\\_def _СЛОВО_;_ТИП_;_НОВЫЙ ПЕРЕВОД_", parse_mode="markdownv2")
        return
    try:
        db.add_definition(word, type_, additional_definition)
        await message.reply("Добавлено")
    except (AlreadyExists, WordNotFound) as e:
        await message.reply(e)


@dp.message_handler(commands=['edit_def'])
async def edit_def(message: types.Message):
    try:
        word, type_, new_definition = message.get_args().split(';')
    except ValueError:
        await message.reply("/edit\\_def _СЛОВО_;_ТИП_;_НОВЫЙ ПЕРЕВОД_", parse_mode="markdownv2")
        return
    db.edit_definition(word, type_, new_definition)
    await message.reply("Изменено")


@dp.message_handler(content_types=['document'])
async def get_csv(message: types.Message):
    input()

def prep_terms(terms: list) -> str:
    """Подготовка определений к выводу"""
    # TODO: определение части речи для англ
    return "\n".join(list(map(lambda x: f"{x[0].upper()} - {x[1]}", terms)))


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
