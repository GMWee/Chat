import aiogram
import aiohttp

from src.base.config import CONFIG
from src.routers import messages, settings, subscription
from src.base.database import DATABASE


class Bot:
	def __init__(self):
		self.bot: aiogram.Bot = ...

	async def run(self):
		await DATABASE.open_connection(
			CONFIG["database_host"],
			CONFIG["database_port"],
			CONFIG["database_user"],
			CONFIG["database_password"],
			CONFIG["database_database"],
		)

		self.bot = aiogram.Bot(CONFIG["token"])
		dispatch = aiogram.Dispatcher()

		await self._set_commands()

		dispatch.include_router(subscription.router)
		dispatch.include_router(settings.router)
		dispatch.include_router(messages.router)

		async with aiohttp.ClientSession() as session:
			try:
				await dispatch.start_polling(self.bot, skip_updates=True, aiohttp_session=session)
			finally:
				await self.bot.session.close()
				await DATABASE.close_connection()

	async def _set_commands(self):
		commands = [
			aiogram.types.BotCommand(command="donate", description="Преобрести подписку"),
			aiogram.types.BotCommand(command="reset", description="Очистить системный промпт"),
			aiogram.types.BotCommand(command="system", description="Задать системный промпт"),
			aiogram.types.BotCommand(command="clear", description="Очистить историю чата"),
			aiogram.types.BotCommand(command="command", description="Список команд"),
			aiogram.types.BotCommand(command="model", description="Список моделей"),
			aiogram.types.BotCommand(command="info", description="Информация о текущей подписке"),
			aiogram.types.BotCommand(command="temp", description="Температура генерации"),
			aiogram.types.BotCommand(command="token", description="Кол-во выводимых токенов")
		]

		await self.bot.set_my_commands(commands)
