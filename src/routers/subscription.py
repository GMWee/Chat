from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from decimal import Decimal, InvalidOperation

import datetime
import json
import logging
import aiohttp
import time
from urllib.parse import urlencode, quote

from src.base.config import CONFIG
from src.base.database import DATABASE
from src.base.utils import get_user_subscription

YOOMONEY_API_URL = "https://yoomoney.ru/api/operation-history"

logger = logging.getLogger(__name__)
router = Router()

class SetState(StatesGroup):
    sum = State()

class sum:
	sum = 20

SUM = sum()
@router.message(Command('info'))
async def info(message: Message):
	user_id = message.chat.id
	user = await DATABASE.get_or_create_user(user_id)
	sub = get_user_subscription(user)
	balance = await DATABASE.get_or_create_user(user_id)
	sub_info = await DATABASE.get_subscription(sub)
	sub_models = await DATABASE.get_subscription_models(sub)
	current_model = await DATABASE.get_model(user[4])
	cred = user[5]

	if time.time() > user[6]:
		cred = sub_info[2]
		await DATABASE.set_credits_info(user_id, cred, 0)

	text = "❗️ Информация\n\n"
	text += f"— *Баланс:* {float(balance[11])}⭐\n"
	text += f"— *Подписка*: {sub_info[1]}\n"
	text += f"— *Выбранная модель*: {current_model[1]}\n"
	text += f"— *Кредиты*: _{cred}💎 / {sub_info[2]}💎_\n"
	if sub_info[4] == 0:
		text += f"— *Фото недоступны*\n\n"
	else:
		text += f"— *Стоимость фото*: _{sub_info[4]}💎_\n\n"
	text += "🤖 Доступные модели:\n"

	for mod in sub_models:
		model = await DATABASE.get_model(mod[0])
		text += f"— {model[1]}\n"

	await message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data.startswith("sub_info_"))
async def sub_info(callback: CallbackQuery):
	_id = int(callback.data[len("sub_info_"):])
	sub = await DATABASE.get_subscription(_id)
	sub_models = await DATABASE.get_subscription_models(_id)

	text = f"<b>{sub[1]}</b>\n"
	text += f"💲 <b>Цена:</b> <em>{sub[5]}₽ / месяц</em>\n\n"
	text += "❗️ <b>Основная информация:</b>\n"
	text += f"— <b>{sub[2]}💎</b> <em>в час</em>\n"
	text += f"— <b>Стоимость фото: {sub[3]}💎</b>\n\n"
	text += "🤖 <b>Доступные модели:</b>\n"

	for mod in sub_models:
		model = await DATABASE.get_model(mod[0])
		text += f"— {model[1]}\n"

	await callback.message.answer(text, parse_mode="HTML")
	await callback.answer()

@router.message(Command("donate"))
async def cmd_system(message: Message, state: FSMContext):
    await message.answer("⭐️*Введите сумму не менее 20 рублей.\n(1⭐️ = 1₽):*", parse_mode="Markdown")
    await state.set_state(SetState.sum)

@router.message(SetState.sum)
async def set_system(message: Message, state: FSMContext):
    keyboard = []
    try:
        sum_value = float(message.text)
    except ValueError:
        await message.answer("*ОШИБКА:*\nВведите *числовое значение* суммы❗️", parse_mode="Markdown")
        return

    if not isinstance(sum_value, (int, float)) or sum_value < 20:
        await message.answer("*ОШИБКА:*\nВведите сумму *не менее 20₽*❗️", parse_mode="Markdown")
        return

    SUM.sum = sum_value

    keyboard.append([
        InlineKeyboardButton(text=f"Оплата на {sum_value}₽", callback_data=f"sub_buy_{sum_value}"),
    ])

    await message.answer(
        "Нажимая на кнопку вам дадут *ссылку* на оплату\n"
        f"и *вы получите {sum_value}⭐️* на баланс вашего виртуального кошелька.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )
    await state.clear()

#Ниже приведена логика оплаты
#запрос к микросервису оплаты
async def get_label(sum, id, num):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'http://127.0.0.1:8000/get_quickpay_link/{sum}/{id}') as resp:
            data = await resp.json()
            return data.get('url') if num == 1 else data.get('label')

async def check_payment(label, user_id, num):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'http://127.0.0.1:8000/check_payment_handler/{label}/{user_id}') as resp:
            data = await resp.json()
            return data.get('label')

@router.callback_query(F.data.startswith("sub_buy_"))
async def sub_buy(callback: CallbackQuery):
    _sum = float(callback.data[len("sub_buy_"):])
    formatted_price_for_label = f"{Decimal(_sum):.2f}"
    text = (
        f"<b>⭐{_sum}</b>\n"
        f"💲 <b>Цена:</b> <em>{formatted_price_for_label} руб</em>\n\n"
        "1️⃣ Нажмите <b>Оплатить</b> (вы перейдёте на сайт YooMoney)\n"
        "2️⃣ Затем <b>Я оплатил</b>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Оплатить", url=await get_label(_sum, callback.from_user.id, 1))],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"sub_check_{await get_label(_sum, callback.from_user.id, 0)}")]
    ])
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("sub_check_"))
async def check_payment_handler(callback: CallbackQuery):
	label: str = callback.data[len("sub_check_"):]
	user_id = callback.from_user.id

	await callback.answer("⏳ Проверяем статус вашего платежа...")

	if await check_payment(label, user_id, 0) == 1:
		await sub_update(callback.message.chat.id, float(label.split("_")[-1]))

		await callback.message.answer(
			f"✅ <b>Оплата успешна!</b>\n\n"
			f"Ваш баланс пополнен<b>Спасибо</b>!",
			parse_mode="HTML"
		)
	else:
		await callback.message.answer(
			"⚠️ <b>Платеж не найден или еще не обработан</b>\n\n"
			"Пожалуйста, убедитесь, что вы завершили оплату в YooMoney\n"
			"Платеж может занять несколько минут\n\n"
			"Попробуйте нажать <b>Я оплатил</b> еще раз через пару минут\n"
			"Если проблема сохраняется, обратитесь в поддержку",
			parse_mode="HTML"
		)

async def sub_update(sum: int, telegram_id: int):
	await DATABASE.set_user_balance(sum, telegram_id,)