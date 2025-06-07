from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

import time

from src.base.database import DATABASE
from src.base.utils import get_user_subscription

router = Router()


async def format_subscription_info(sub_info, sub_models):
    """Formats the subscription information into a readable string."""
    text = f"{sub_info[1]}\n\n"
    text += f"— *Цена:* {float(sub_info[5])}⭐\n"
    text += f"— *Кредиты в час*: _{sub_info[2]}💎\n"
    text += "— *Фото*: "
    if sub_info[3] == 0:
        text += "недоступны\n"
    else:
        text += f"Стоимость _{sub_info[3]}💎_\n"
    text += "— *Голосовые сообщения*: "
    if sub_info[-1] == 0:
        text += "недоступны\n"
    else:
        text += f"Стоимость _{sub_info[-1]}💎_\n"
    text += f"— *Длина контекста*: _{sub_info[-2]}💎\n\n"
    text += "🤖 Доступные модели:\n"

    for mod in sub_models:
        model = await DATABASE.get_model(mod[0])
        if model:  # Ensure model is found
            text += f"— {model[1]}\n"
        else:
            text += "— Модель не найдена\n"  # Handle missing model

    return text


async def get_all_subscription_info():
    """Retrieves and formats information for all subscription tiers."""
    all_texts = []
    for i in range(5):
        sub_info = await DATABASE.get_subscription(i)
        if not sub_info:
            continue

        sub_models = await DATABASE.get_subscription_models(i)
        formatted_text = await format_subscription_info(sub_info, sub_models)
        all_texts.append(formatted_text)
    return all_texts


@router.message(Command('buy'))
async def buy_command(message: Message):
    """Handles the /buy command."""
    subscription_texts = await get_all_subscription_info()
    # The follow code will send a large string when it should've been seperate messages
    # text = ''
    # for i in range(5):
    #     text += subscription_texts[i]
    #     text += "\n\n"
    # await message.answer(text, parse_mode="Markdown")

    for text in subscription_texts:
        await message.answer(text, parse_mode="Markdown")


@router.message(Command('info'))
async def info(message: Message):
    """Handles the /info command to display user-specific information."""
    user_id = message.chat.id
    user = await DATABASE.get_or_create_user(user_id)
    sub = get_user_subscription(user)
    # Removed redunant get or create call since you already have the user
    #balance = await DATABASE.get_or_create_user(user_id)

    # Make sure sub is a valid index
    if sub is None:
        await message.answer("У вас нет активной подписки.", parse_mode="Markdown")
        return

    sub_info = await DATABASE.get_subscription(sub)
    sub_models = await DATABASE.get_subscription_models(sub)
    current_model = await DATABASE.get_model(user[4])  # index 4 might be wrong
    cred = user[5]

    if time.time() > user[6]:
        cred = sub_info[2]
        await DATABASE.set_credits_info(user_id, cred, 0)

    text = "❗️ Информация\n\n"
    text += f"— *Баланс:* {float(user[11])}⭐\n"  # Access balance from the user
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