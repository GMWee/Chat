import aiogram
import aiohttp
import asyncio
import logging

from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.base.config import CONFIG
from src.routers import messages, settings, subscription, donate
from src.base.database import DATABASE


class Bot:
	def __init__(self):
		self.bot: aiogram.Bot = None
		self.dispatch = None
		self._shutdown_event = asyncio.Event()
	
	async def run(self):
		await DATABASE.open_connection(
			CONFIG["database_host"],
			CONFIG["database_port"],
			CONFIG["database_user"],
			CONFIG["database_password"],
			CONFIG["database_database"],
		)
		
		self.bot = aiogram.Bot(CONFIG["token"])
		self.dispatch = aiogram.Dispatcher()
		
		await self._set_commands()
		self._register_handlers()
		
		self.dispatch.include_router(donate.router)
		self.dispatch.include_router(subscription.router)
		self.dispatch.include_router(settings.router)
		self.dispatch.include_router(messages.router)
		
		async with aiohttp.ClientSession() as session:
			try:
				polling_task = asyncio.create_task(
					self.dispatch.start_polling(self.bot, skip_updates=True, aiohttp_session=session)
				)
				shutdown_task = asyncio.create_task(self._shutdown_event.wait())
				
				done, pending = await asyncio.wait(
					{polling_task, shutdown_task},
					return_when=asyncio.FIRST_COMPLETED
				)
				
				if shutdown_task in done:
					logging.info("Получен сигнал остановки бота")
					await self.dispatch.stop_polling()
				
				for task in pending:
					task.cancel()
					try:
						await task
					except asyncio.CancelledError:
						pass
			
			finally:
				await self.bot.session.close()
				await DATABASE.close_connection()
	
	async def _set_commands(self):
		commands = [
			aiogram.types.BotCommand(command="pay", description="Пополнить виртуальный кошелек"),
			aiogram.types.BotCommand(command="buy", description="Преобрести подписку"),
			aiogram.types.BotCommand(command="reset", description="Очистить системный промпт"),
			aiogram.types.BotCommand(command="system", description="Задать системный промпт"),
			aiogram.types.BotCommand(command="clear", description="Очистить историю чата"),
			aiogram.types.BotCommand(command="command", description="Список команд"),
			aiogram.types.BotCommand(command="model", description="Список моделей"),
			aiogram.types.BotCommand(command="info", description="Информация о текущей подписке"),
			aiogram.types.BotCommand(command="temp", description="Температура генерации"),
			aiogram.types.BotCommand(command="token", description="Кол-во выводимых токенов"),
		]
		
		await self.bot.set_my_commands(commands)
	
	def _register_handlers(self):
		
		@self.dispatch.message(Command('stop'))
		async def stop_bot_request(message: Message):
			user = await DATABASE.get_or_create_user(message.chat.id)
			
			if user[3] < 1:
				await message.answer("❌ Недостаточно прав для выполнения команды")
				return
			
			builder = InlineKeyboardBuilder()
			builder.button(text="✅ Да, остановить", callback_data="confirm_stop")
			builder.button(text="❌ Отмена", callback_data="cancel_stop")
			
			await message.answer(
				"⚠️ *Вы уверены, что хотите остановить бота?*\n\n"
				"Это действие прервет работу для всех пользователей.",
				parse_mode="Markdown",
				reply_markup=builder.as_markup()
			)
		
		@self.dispatch.callback_query(F.data == "confirm_stop")
		async def confirm_stop(callback: CallbackQuery):
			user = await DATABASE.get_or_create_user(callback.message.chat.id)
			if user[3] < 1:
				await callback.answer("Недостаточно прав", show_alert=True)
				return
			
			logging.info(f"БОТ ОСТАНОВЛЕН ПОЛЬЗОВАТЕЛЕМ {callback.from_user.id}")
			await callback.message.edit_text("🔴 *Бот остановлен*\n\nВаш ID в целях безопасности был отправлен владельцу бота и в логи", parse_mode="Markdown")
			await callback.answer()
			
			self._shutdown_event.set()
		
		@self.dispatch.callback_query(F.data == "cancel_stop")
		async def cancel_stop(callback: CallbackQuery):
			await callback.message.edit_text("✅ Остановка отменена")
			await callback.answer()