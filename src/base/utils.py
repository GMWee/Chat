import time


def split_message(message: str, part_length: int = 3000) -> list[str]:
	parts = []

	while len(message) > part_length:
		part = message[:part_length]
		parts.append(part)
		message = message[part_length:]

	if message:
		parts.append(message)
	return parts


def get_user_subscription(user: tuple):
	if time.time() > user[2]:
		return 0
	return user[1]
