import asyncpg


class Database:
	def __init__(self):
		self.connection: asyncpg.Connection = ...
		self._last_row_id: int = 0

	async def open_connection(self, host: str, port: int, user: str, password: str, database: str) -> None:
		self.connection = await asyncpg.connect(host=host, port=port, user=user, password=password, database=database)

	async def close_connection(self) -> None:
		if self.connection:
			await self.connection.close()

	async def execute_query(self, query: str, params: tuple = None) -> None:
		async with self.connection.transaction():  # Start a transaction
			await self.connection.execute(query, *(params or ())) # Use execute directly
			# asyncpg does not directly expose lastrowid.  This will need to be handled separately
			# if it is needed in a specific query.  Consider using RETURNING id in INSERT/UPDATE.

	async def execute_get_query(self, query: str, params: tuple = None):
		return await self.connection.fetch(query, *(params or ()))  # Use fetch directly

	@property
	def last_id(self):
		return self._last_row_id  # This property likely doesn't work correctly with asyncpg.  See comment above.


class ProjectDatabase(Database):
	def __init__(self):
		super().__init__()

	async def get_or_create_user(self, tg_id: int, create_if_not_found: bool = True):
		res = await self.execute_get_query("SELECT * FROM users WHERE id = $1", (tg_id,))
		if not res and create_if_not_found:
			await self.execute_query("INSERT INTO users(id) VALUES ($1)", (tg_id,))
			res = await self.execute_get_query("SELECT * FROM users WHERE id = $1", (tg_id,))
			return res[0] if res else None # Corrected handling of empty result.
		return res[0] if res else None
	
	
	async def get_subscriptions(self):
		return await self.execute_get_query("SELECT * FROM subscriptions")

	async def get_subscription(self, subscription_id: int):
		res = await self.execute_get_query("SELECT * FROM subscriptions WHERE id = $1", (subscription_id,))
		return res[0] if res else None

	async def get_subscription_models(self, subscription_id: int):
		return await self.execute_get_query("SELECT model_id FROM s_models WHERE sub_id = $1", (subscription_id,))

	async def get_model(self, model_id: int):
		res = await self.execute_get_query("SELECT * FROM models WHERE id = $1", (model_id,))
		return res[0] if res else None

	async def set_user_subscription(self, user_id: int, sub_id: int, time: str):
		await self.execute_query("UPDATE users SET sub_type = $1, sub_time = $2 WHERE id = $3", (sub_id, time, user_id))

	async def get_user_context(self, user_id: int):
		return await self.execute_get_query("SELECT * FROM u_context WHERE user_id = $1", (user_id,))

	async def add_context_message(self, user_id: int, message: str, role: str, image_data: str | None = None):
		return await self.execute_query("INSERT INTO u_context(user_id, role, image_data, content) VALUES ($1, $2, $3, $4)", (user_id, role, image_data, message,))

	async def info_api_key(self, client_id: str):
		return await self.execute_get_query("SELECT * FROM api_key WHERE client_id = $1", (client_id,))

	async def add_api_key(self,client_id: str, key: str):
		await self.execute_query("INSERT INTO api_key(client_id, key) VALUES ($1, $2)", (client_id, key,))

	async def delete_api_key(self, client_id: str):
		await self.execute_query("DELETE FROM api_key WHERE client_id = CAST($1 AS TEXT)", (client_id,))

	async def clear_context(self, user_id: int):
		await self.execute_query("DELETE FROM u_context WHERE user_id = $1", (user_id,))

	async def set_ban(self, num: int, user_id: int):
		await self.execute_query("UPDATE users SET ban = $1 WHERE id = $2", (num, user_id))

	async def set_user_balance(self, sum: int, user_id: int):
		await self.execute_query("UPDATE users SET balance = $1 WHERE id = $2", (sum, user_id))

	async def set_role(self, num: int, user_id: int):
		await self.execute_query("UPDATE users SET role = $1 WHERE id = $2", (num, user_id))

	async def set_credits_info(self, user_id: int, amount: int, time: float):
		await self.execute_query("UPDATE users SET credits = $1, next_credits_time = $2 WHERE id = $3", (amount, time, user_id))

	async def set_user_setting(self, user_id: int, name: str, value: int | str | float):
		await self.execute_query(f"UPDATE users SET {name} = $1 WHERE id = $2", (value, user_id))
	
	async def limit_user_context_length(self, user_id: int, limit: int):
		await self.execute_query(
			"DELETE FROM u_context WHERE user_id = $1 AND timestamp NOT IN ("
			"SELECT timestamp FROM u_context WHERE user_id = $1 ORDER BY timestamp DESC LIMIT $2"
			")",
			(user_id, limit))

	async def api_key_print(self):
		return await self.execute_get_query(f"SELECT * FROM api_key")



DATABASE = ProjectDatabase()