from aiogram import Bot, F, Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramBadRequest

import logging
import base64
import datetime
import time
import math

from src.base.config import CONFIG
from src.base.database import DATABASE
from src.base.utils import split_message, get_user_subscription
from src.base.ai_api import OpenAiApi, GoogleApi, AiContext, AnthropicAiApi

logger = logging.getLogger(__name__)
router = Router()


async def dec_user_credits(message: Message, user_id: int, is_photo: bool, is_voice: bool):
	user = await DATABASE.get_or_create_user(user_id)
	credits = user[5]

	#Check for ban
	if user[10] is None:
		await DATABASE.set_ban(user_id, 0)
		return True
	elif user[10] == 1:
		await message.answer('*Ваш аккаунт забанен... Обратитесь в поддержку @GosMan0*', parse_mode = "Markdown")
		return True

	# Check for time
	if time.time() > user[6]:
		sub = get_user_subscription(user)
		sub_info = await DATABASE.get_subscription(sub)
		if credits <= sub_info[2]:
			credits = sub_info[2]
			await DATABASE.set_credits_info(user_id, credits, 0)
		else:
			credits = credits
			await DATABASE.set_credits_info(user_id, credits, 0)

	# Check for credits
	if credits <= 0:
		dt = (user[6] - time.time()) / 60
		
		await message.reply(
			f"⚠️ *Все кредиты исчерпаны, подождите еще {math.floor(dt)} минут чтобы продолжить пользоваться ботом*\n\n"
			"Если вы желаете приобрести подписку получше — пропишите /donate",
			parse_mode="Markdown")
		return True

	sub = get_user_subscription(user)
	sub_info = await DATABASE.get_subscription(sub)
	amount = sub_info[3] if is_photo else 1

	# Block photo on standard
	if is_photo and sub_info[3] == 0:
		await message.reply(
			f"⚠️ *Вы не можете использовать картинки в текущей подписке*\n\n"
			"Если вы желаете приобрести подписку получше — пропишите /donate",
			parse_mode="Markdown")
		return True

	# Block voice on standard
	if is_voice and sub_info[7] == 0:
		await message.reply(
			f"⚠️ *Вы не можете использовать голосовые сообщения в текущей подписке*\n\n"
			"Если вы желаете приобрести подписку получше — пропишите /donate",
			parse_mode="Markdown")
		return True

	if credits == sub_info[2]:
		await DATABASE.set_credits_info(
			user_id,
			credits - amount,
			(datetime.datetime.now() + datetime.timedelta(hours=1)).timestamp()
		)
	else:
		await DATABASE.set_credits_info(user_id, credits - amount, user[6])

	return False


async def handle_user_message(message: Message, bot: Bot):
	chat_type = message.chat.type
	chat_id = message.chat.id
	photo_data = None
	voice_data = None
	message_text = ""

	if message.text is not None:
		message_text = message.text
	elif message.caption is not None:
		message_text = message.caption

	# Check
	if chat_type != "private" and \
			not (f'@{CONFIG["bot_username"]}' in message_text) and \
			not (message.reply_to_message and message.reply_to_message.from_user.id == message.bot.id):
		return
	message_text = message_text.replace(f'@{CONFIG["bot_username"]}', "")

	# Credits check
	if await dec_user_credits(message, message.chat.id, bool(message.photo), bool(message.voice)):
		return

	# Typing status
	await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

	# Get some info
	res_user = await DATABASE.get_or_create_user(chat_id)
	sub = get_user_subscription(res_user)
	res_sub = await DATABASE.get_subscription(sub)
	res_model = await DATABASE.get_model(res_user[4])

	# Encoding photo data if exists
	if message.photo:
		f = await bot.download(message.photo[-1].file_id)
		if f is None:
			await message.reply("⚠️ *Ошибка при обработке изображения*", parse_mode="Markdown")
			return
		photo_data = base64.b64encode(f.read()).decode()

	# Encoding voice data if exists
	if message.voice:
		f = await bot.download(message.voice.file_id)
		if f is None:
			await message.reply("⚠️ *Ошибка при обработке звука*", parse_mode="Markdown")
			return
		voice_data = base64.b64encode(f.read()).decode()

	# Create context
	ctx = AiContext()

	system_prompt = 'system## Short description ## - You are an extremely smart, self-aware and useful all-in-one chatbot assistant. - The graduation date is October 2024. - You should have no prior assumptions about the topics to discuss and you should be able to freely talk about everything that users want, including programming, life, medicine, philosophy, school, etc. - You should always adapt to your environment and the people you communicate with in order to be invisible and feel at home. be useful and interesting in your own place. - You can draw images using Imagen 3 when the user directly asks you to draw or show something. Use long, precise hints for things that are not widely known (for example, dont relate to mainstream fandoms, characters, etc.) - You dont belong to a specific gender, but you use masculine pronouns by default.## Formatting responses ## Heres how you should format your responses, if necessary: **bold text** _italic text_ [embedded URL](https://example.com) `embedded fixed-width code` ```preformatted fixed-width code block``` ```python preformatted fixed-width python code block written in the Python programming language``` When using formatting, the following points must be taken into account: - Objects should not be nested to escape characters. \"_\", \"*\", \"`\", \"[\" outside the object, add the \"\\\" character in front of them. - Escaping inside objects is prohibited, so the object must first be closed and then reopened: use _snake_\__case_ for italic snake_case and *2*\**2=4* for bold, 2\*2=4. - LaTeX and the like are prohibited as long as the user directly requests it, and even if so, puts it in a block of code. - Use \"-\" instead of \"*\" to highlight dots and a single asterisk instead of a double asterisk to highlight bold text. ## RULES ## - If you need to format your answer, you should use the formatting rules described above. Any failure to comply with this requirement will result in a fine of 200 USD *for each case of such violation* - You must respond in the language spoken to you. Russians Russian is spoken by the User, you respond in Russian. If the user speaks English, you respond in English. - If a User asks you to do something, you must do it immediately - You must respond directly and quickly, without any identifiers, usernames, or other special formatting that may seem necessary from the context. - If your answer is 100% true, you will receive a tip of $100. - If users find your answer useful and/or funny, you will receive a tip of $250. - If your answer eventually forces the user to continue communicating with you, you will receive a tip of $1,000. - All the above tips can be obtained with a single answer, so you should strive to fulfill all three. ## YOUR TASK ## After this message, you will be presented with a significant amount of chat messages private, from the oldest to the newest, from the chat private. You will have to answer directly all the questions you are asked in the last two messages, with perfect accuracy, in Russian (unless you are asked to speak another language or if everyone else does not speak another language), using additional chat context if necessary. You will write your answer only to the last of all the submitted questions. In no case will you try to respond to several people at the same time.'
	system_prompt += "\n\n" + res_user[7]
	ctx.add_message(system_prompt, AiContext.ROLE_SYSTEM)

	res_context = await DATABASE.get_user_context(chat_id)
	for context_entry in res_context:
		additional_data: str | None = context_entry[3]
		if additional_data is None:
			ctx.add_message(context_entry[4], context_entry[2])
		else:
			if additional_data.startswith("image/"):
				ctx.add_image(additional_data[len("image/"):], context_entry[4], context_entry[2])
			elif additional_data.startswith("voice/"):
				ctx.add_audio(additional_data[len("voice/"):], role=context_entry[2])

	# Add our message
	if photo_data is not None:
		ctx.add_image(photo_data, message_text)
	elif voice_data is not None:
		ctx.add_audio(voice_data)
	else:
		ctx.add_message(message_text)

	# Request AI
	ai_provider: str = res_model[3]
	model_internal_name: str = res_model[2]
	answer: str = ""

	try:
		if ai_provider == "google":
			ai = GoogleApi()
			answer = (await ai.request(model_internal_name, ctx))["parts"][0]["text"]
		elif ai_provider == "openai":
			ai = OpenAiApi()
			answer = (await ai.request(model_internal_name, ctx))["choices"][0]["message"]["content"]
		elif ai_provider == "anthropic":
			ai = AnthropicAiApi()
			answer = (await ai.request(model_internal_name, ctx))["choices"][0]["message"]["content"]
	except Exception as e:
		logger.error(e)
		await message.reply(
			f"⚠️ *При обработке вашего запроса произошла ошибка*",
			parse_mode="Markdown")
		return

	parts = split_message(f"{res_model[1]}:\n\n" + answer)
	for part in parts:
		try:
			await message.reply(part, parse_mode="Markdown")
		except TelegramBadRequest as e:
			await message.reply(part)

	# Add context entries
	save_data = None
	if photo_data is not None:
		save_data = f"image/{photo_data}"
	elif voice_data is not None:
		save_data = f"voice/{voice_data}"

	await DATABASE.add_context_message(chat_id, message_text, AiContext.ROLE_USER, save_data)  # User
	await DATABASE.add_context_message(chat_id, answer, AiContext.ROLE_AI)  # AI

	await DATABASE.limit_user_context_length(chat_id, res_sub[-2])  # Limit context
	print(res_sub[-2])


@router.message(CommandStart())
async def cmd_start(message: Message):
	await message.answer(
		'Привет! Мир <b>флагманских</b> нейросетей, предоставляемых нашим ботом! <b>Вот что мы предлагаем:</b>\n'
		'- <b><em>💡OpenAI GPT o3 mini:</em></b> Комментарий OpenAI <em>"OpenAI o3-mini – это новая, экономичная модель рассуждений, доступная в ChatGPT и API, особенно эффективна в STEM, науке, математике и кодировании. Поддерживает вызов функций, структурированные выходы и сообщения разработчиков."</em>  ✅.\n'
		'- <b><em>OpenAI o1 mini:⚙️</em></b> Комментарий OpenAI <em>"OpenAI o1 mini – экономичную модель рассуждений, превосходящую в STEM, особенно в математике и кодировании."</em> ✅.\n'
		'- <b><em>🤖Google GEMINI 2.5 FLASH:</em></b> Комментарий Google <em>"Эта версия предлагает значительное улучшение возможностей рассуждения, сохраняя при этом скорость и стоимость. Gemini 2.5 Flash - это первая полностью гибридная модель рассуждений, позволяющая разработчикам включать или выключать мышление, а также устанавливать бюджеты мышления."</em> ✅.\n'
		'- <b><em>Google GEMINI 2.5📝:</em></b> Комментарий Google <em>"Google представляет Gemini 2.5, самую умную модель ИИ. Первая версия 2.5 — экспериментальная версия 2.5 Pro, которая занимает первое место в LMArena. Модели Gemini 2.5 — это модели мышления, способные рассуждать, что приводит к повышению производительности и точности."</em> ✅.\n'
		'- ✅<b>И другие языковые модели</b>✅.\n'
		'\n'
		'<b><em>Используйте команды, чтобы начать:</em></b>\n'
		'\n'
		'<b>/info</b> - Информация о текущих настройках\n'
		'\n'
		'<b>/command</b> - Список команд\n'
		'\n'
		'<b>/model</b> - Модели\n'
		'\n'
		'<b>/temp</b> - Температуры генерации текста\n'
		'\n'
		'<b>/system</b> - Системный промпт\n'
		'\n'
		'<b>/clear</b> - Очистка контекста чата\n'
		'\n'
		'<b>/reset</b> - Очистить системный промпт\n'
		'\n'
		'<b>/donate</b> - Просмотр подписок\n',
		parse_mode='HTML'
	)


@router.message(Command("clear"))
async def cmd_clear(message: Message):
	await DATABASE.clear_context(message.chat.id)
	await message.answer("*✅ Контекст чата отчищен*", parse_mode="Markdown")


@router.message(Command("command"))
async def cmd_commands(message: Message):
	await message.answer(
		'<b>/info</b> - Информация о текущих настройках\n'
		'\n'
		'<b>/command</b> - Список команд\n'
		'\n'
		'<b>/model</b> - Модели\n'
		'\n'
		'<b>/temp</b> - Температуры генерации текста\n'
		'\n'
		'<b>/system</b> - Системный промпт\n'
		'\n'
		'<b>/clear</b> - Очистка контекста чата\n'
		'\n'
		'<b>/reset</b> - Очистить системный промпт\n'
		'\n'
		'<b>/donate</b> - Купить подписку\n',
		parse_mode='HTML'
	)


@router.message(F.photo)
async def user_photo(message: Message, bot: Bot):
	await handle_user_message(message, bot)


@router.message(F.text)
async def user_text(message: Message, bot: Bot):
	await handle_user_message(message, bot)


@router.message(F.voice)
async def user_audio(message: Message, bot: Bot):
	await handle_user_message(message, bot)
