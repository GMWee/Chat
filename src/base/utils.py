import time

from src.base.database import DATABASE



def split_message(message: str, part_length: int = 3000) -> list[str]:
	parts = []

	while len(message) > part_length:
		part = message[:part_length]
		parts.append(part)
		message = message[part_length:]

	if message:
		parts.append(message)
	return parts

def get_user_subscription(user):
	if time.time() > user[2]:
		print(time.time())
		return 0
	return user[1]
