import sys
import asyncio
import logging

from src.bot import Bot
from src.base.config import CONFIG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


if __name__ == "__main__":
	config_file = sys.argv[1] if len(sys.argv) > 1 else "run/config.json"
	CONFIG.load_config(config_file)

	try:
		if sys.platform == "win32":
			asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
		bot = Bot()
		asyncio.run(bot.run())
	except KeyboardInterrupt:
		logging.info("Bot is shutdown")
	except Exception as e:
		logging.exception("An error occurred during bot execution:")