from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

import time

from src.base.database import DATABASE
from src.base.utils import get_user_subscription

router = Router()


async def format_subscription_info(sub_info, sub_models):
    text = f"{sub_info[1]}\n\n"
    text += f"— <b>Цена:</b> {float(sub_info[5])}⭐\n"
    text += f"— <b>Кредиты в час</b>:  {sub_info[2]}💎\n"
    text += f"— <b>Фото</b>: "
    if sub_info[3] == 0:
        text += f"недоступны\n"
    else:
        text += f"Стоимость  {sub_info[3]}💎_\n"
    text += f"— <b>Голосовые сообщения</b>: "
    if sub_info[-1] == 0:
        text += f"недоступны\n"
    else:
        text += f"Стоимость  {sub_info[7]}💎_\n"
    text += f"— <b>Длина контекста</b>:  {sub_info[6]}💎\n\n"
    text += f"🤖 Доступные модели:\n"

    for mod in sub_models:
        model = await DATABASE.get_model(mod[0])
        text += f"— {model[1]}\n"

    return text


async def get_all_subscription_info():
    all_texts = []
    for i in range(5):
        sub_info = await DATABASE.get_subscription(i)
        if not sub_info:
            continue

        sub_models = await DATABASE.get_subscription_models(i)
        formatted_text = await format_subscription_info(sub_info, sub_models)
        all_texts.append(formatted_text)
    return all_texts


@router.message(Command('info'))
async def info(message: Message):
    user_id = message.chat.id
    user = await DATABASE.get_or_create_user(user_id)
    sub = get_user_subscription(user)

    if sub is None:
        await message.answer("У вас нет активной подписки.", parse_mode="Markdown")
        return

    sub_info = await DATABASE.get_subscription(sub)
    sub_models = await DATABASE.get_subscription_models(sub)
    current_model = await DATABASE.get_model(user[4])
    cred = user[5]

    if time.time() > user[6]:
        cred = sub_info[2]
        await DATABASE.set_credits_info(user_id, cred, 0)

    text = "❗️ Информация\n\n"
    text += f"— *Баланс:* {float(user[11])}⭐\n"
    text += f"— *Подписка*: {sub_info[1]}\n"
    text += f"— *Выбранная модель*: {current_model[1]}\n"
    text += f"— *Кредиты*: _{cred}💎 / {sub_info[2]}💎_\n"
    if sub_info[4] == 0:
        text += "— *Фото недоступны*\n\n"
    else:
        text += f"— *Стоимость фото*: _{sub_info[4]}💎_\n\n"
    text += "🤖 Доступные модели:\n"

    for mod in sub_models:
        model = await DATABASE.get_model(mod[0])
        text += f"— {model[1]}\n"

    await message.answer(text, parse_mode="Markdown")
    

@router.message(Command('buy'))
async def buy_command(message: Message):
    subscription_texts = await get_all_subscription_info()
    text = ''
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🟤 BRONZE', callback_data='buy_1')],
            [InlineKeyboardButton(text='⚪️ SILVER', callback_data='buy_2')],
            [InlineKeyboardButton(text='🟡 GOLD', callback_data='buy_3')],
            [InlineKeyboardButton(text='🔷 PLATINUM', callback_data='buy_4')],
            [InlineKeyboardButton(text='❤️ ADMIN', callback_data='buy_5')],
        ]
    )
    for sub_text in subscription_texts:
        text += sub_text
        text += "\n\n"
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    
@router.callback_query(F.data.startswith('buy_'))
async def buy_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    sub_id = int(callback.data[len("buy_"):])
    sub_info = await DATABASE.get_subscription(sub_id)
    user = await DATABASE.get_or_create_user(user_id)
    if user[11] < sub_info[5]:
        await callback.message.edit("⚠️ *Не достаточно средств на виртуальном кошельке!*\n\n"
			"Если вы желаете приобрести подписку получше — пропишите /pay для пополнения баланса", parse_mode="Markdown")
        return
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text='Подтвердить', callback_data=f'yes_{sub_id}_{user_id}')]
            ]
        )
        await callback.message.edit_text(f"Вы действительно хотите купить подписку - *{sub_info[1]}* за *{sub_info[5]}⭐*\n\n*После того как вы нажмете кнопку - подтвердить, деньги спишутся с вашего виртуального кошелька и возврату не подлежат!*", reply_markup=keyboard, parse_mode="Markdown")
        
        
@router.callback_query(F.data.startswith('yes_'))
async def buy_sub(callback: CallbackQuery):
    data = callback.data.split("_")
    sub_id = int(data[1])
    user_id = int(data[2])
    sub_info = await DATABASE.get_subscription(sub_id)
    user = await DATABASE.get_or_create_user(user_id)
    sum = user[11] - sub_info[5]
    datatime = (60 * 60 * 24 * 28) + time.time()
    await DATABASE.set_user_subscription(user_id, sub_id, datatime)
    await DATABASE.set_user_balance(sum, user_id)
    # Здесь ошибка - нужно получить пользователя заново
    updated_user = await DATABASE.get_or_create_user(user_id)
    await callback.message.edit_text(
        f"Подписка успешно изменена на {sub_info[1]}\n\n"
        f"Баланс: {updated_user[11]}⭐\n*Приятного использования✅*",
        parse_mode="Markdown"
    )