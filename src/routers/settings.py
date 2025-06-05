import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from src.base.database import DATABASE
from src.base.utils import get_user_subscription
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
router = Router()




class SetState(StatesGroup):
	temperatureS = State()
	system = State()
	tokens = State()

class SetState(StatesGroup):
	temperature = State()
	system = State()
	tokens = State()


@router.message(Command("system"))
async def cmd_system(message: Message, state: FSMContext):
	await message.answer("✏️ *Введите системный промпт*:", parse_mode="Markdown")
	await state.set_state(SetState.system)


@router.message(Command("reset"))
async def clear_guide(message: Message):
	chat_id = message.chat.id
	await DATABASE.set_user_setting(chat_id, "setting_system", "")
	await message.answer("✅ *Cистемный промпт отчищен*", parse_mode="Markdown")


@router.message(SetState.system)
async def set_system(message: Message, state: FSMContext):
	prompt = message.text
	chat_id = message.chat.id

	await DATABASE.set_user_setting(chat_id, "setting_system", prompt)
	await message.answer("✅ *Cистемный промпт задан*", parse_mode="Markdown")
	await state.clear()


@router.message(Command("model"))
async def cmd_model(message: Message):
	user_id = message.chat.id
	user = await DATABASE.get_or_create_user(user_id)
	sub = get_user_subscription(user)
	sub_models = await DATABASE.get_subscription_models(sub)
	keyboard = []

	for model_id in sub_models:
		model = await DATABASE.get_model(model_id[0])
		keyboard.append([InlineKeyboardButton(text=model[1], callback_data=f"set_model_{model[0]}")])

	await message.answer("🤖 *Выберите модель*", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")


@router.callback_query(F.data.startswith("set_model_"))
async def handle_model_selection(callback: CallbackQuery):
	_id = int(callback.data[len("set_model_"):])
	model = await DATABASE.get_model(_id)
	chat_id = callback.message.chat.id

	await DATABASE.set_user_setting(chat_id, "setting_model", _id)

	await callback.message.edit_text(
		text=f"✅ *Выбрана модель*: {model[1]}",
		reply_markup=None,
		parse_mode="Markdown"
	)
	await callback.answer()
