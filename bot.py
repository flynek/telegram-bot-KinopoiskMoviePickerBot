import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import requests
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, LabeledPrice

# настройки логирования
logging.basicConfig(level=logging.INFO)

# инициализация бота и диспетчера
bot = Bot(token='https://youtu.be/dQw4w9WgXcQ')
dp = Dispatcher(bot)
KINO_TOKEN = 'https://youtu.be/dQw4w9WgXcQ'
PAYMENT_TOKEN = 'https://youtu.be/dQw4w9WgXcQ'
index = 0
movies = []
caption, poster, year = '', '', ''

# клавиатуры
kb_understand = InlineKeyboardMarkup().add(InlineKeyboardButton('Понятно', callback_data='delete'))
kb_choice = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton('Купить', callback_data='buy')],
    [InlineKeyboardButton('Следующий фильм', callback_data='next')],
    [InlineKeyboardButton('Отмена', callback_data='delete')]
], row_width=1)
kb_welcome = InlineKeyboardMarkup().add(InlineKeyboardButton('Пожалуйста', callback_data='delete'))
kb_cancel = InlineKeyboardMarkup().add(InlineKeyboardButton('Отмена', callback_data='delete'))


# функция выбора фильма (система тиндера)
async def movie_tinder(movies: list, index: int, message: types.Message,
                       bot: Bot, kb: InlineKeyboardMarkup):
    global caption, poster, year
    if len(movies[index].get('description')) >= 4060:
        index += 1
    movie = movies[index]
    name = movie.get('nameRu', 'Название не найдено')
    name_en = movie.get('nameEn', 'Название не найдено')
    year = movie.get('year', 'Год не найден')
    description = movie.get('description', 'Описание не найдено')
    poster = movie.get('posterUrlPreview', '')
    rating = movie.get('rating', 'Рейтинг не найден')
    caption = f'{name} (RUS)/ {name_en} (ENG)\n' \
              f'Год выпуска: {year}, Рейтинг: {rating}\n' \
              f'Описание:\n' \
              f'{description}'
    await bot.send_photo(chat_id=message.chat.id, photo=poster, reply_markup=kb,
                         caption=caption)


# функция редактирования фильма
async def edit_movie_tinder(movies: list, index: int, callback: types.CallbackQuery,
                            bot: Bot, kb: InlineKeyboardMarkup):
    global caption, poster, year
    if len(movies[index].get('description')) >= 1000:
        index += 1
        if index >= len(movies):
            await bot.send_message(chat_id=callback.message.chat.id, text='Фильмы закончились')
    movie = movies[index]
    name = movie.get('nameRu', 'Название не найдено')
    name_en = movie.get('nameEn', 'Название не найдено')
    year = movie.get('year', 'Год не найден')
    description = movie.get('description', 'Описание не найдено')
    poster = InputMediaPhoto(movie.get('posterUrlPreview', ''))
    rating = movie.get('rating', 'Рейтинг не найден')
    caption = f'{name} (RUS)/ {name_en} (ENG)\n' \
              f'Год выпуска: {year}, Рейтинг: {rating}\n' \
              f'Описание:\n' \
              f'{description}'
    await bot.edit_message_media(media=poster, chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await bot.edit_message_caption(caption=caption, chat_id=callback.message.chat.id, parse_mode='HTML',
                                   message_id=callback.message.message_id)
    await bot.edit_message_reply_markup(reply_markup=kb, chat_id=callback.message.chat.id,
                                        message_id=callback.message.message_id)


# обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    # отправляем сообщение с инструкцией
    await bot.send_message(chat_id=message.chat.id, text='Привет! Я помогу тебе найти и оплатить фильм на вечер\n'
                                                         'Напиши название фильма и выбирай из предложенных вариантов',
                           reply_markup=kb_understand)


# обработчик команды удаления
@dp.callback_query_handler(text='delete')
async def delete_command(callback: types.CallbackQuery):
    # реализуем удаление стартового сообщения
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await callback.answer()


# обработчик платежей
@dp.callback_query_handler(text='buy')
async def pay_film(callback: types.CallbackQuery):
    lines = caption.split('\n')
    # расчёт цены со скидкой, зависящей от года выпуска
    if year == 'Год не найден':
        price = 500_00
    elif int(year) <= 1913:
        price = 10_00
    else:
        price = 500_00 * ((2023 - int(year)) / 100)
    await bot.send_invoice(title=lines[0],
                           description='\n'.join(lines[3:]),
                           payload='88805553535',
                           currency='RUB',
                           prices=[
                               LabeledPrice(label=lines[0], amount=int(price))],
                           photo_url=poster,
                           photo_size=600,
                           provider_token=PAYMENT_TOKEN,
                           chat_id=callback.from_user.id)


@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await bot.send_message(chat_id=message.chat.id, text='Благодарим за покупку!')
    
    
@dp.pre_checkout_query_handler()
async def check(query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)



# обработчик текстовых сообщений
@dp.message_handler()
async def search_movies(message: types.Message):
    global index, movies
    index = 0
    url = f'https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword?keyword=' \
          f'{message.text}&page=1'
    headers = {'X-API-KEY': KINO_TOKEN, 'accept': 'application/json; charset=utf-8'}
    response = requests.get(url, headers=headers).json()
    # обрабатываем ответ и формируем список результатов
    if 'films' in response:
        movies = response['films']
        await movie_tinder(movies=movies, index=index, message=message, bot=bot, kb=kb_choice)
    else:
        await bot.send_message(chat_id=message.chat.id, text='Фильмы не найдены')


# обработчик перебора результатов
@dp.callback_query_handler(text='next')
async def next_movie(callback: types.CallbackQuery):
    global index, movies
    index += 1
    if index >= len(movies):
        await bot.send_message(chat_id=callback.message.chat.id, text='Фильмы закончились')
    else:
        await edit_movie_tinder(movies=movies, index=index, callback=callback, bot=bot, kb=kb_choice)


# запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
