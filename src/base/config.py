import json


class ConfigMissingRequiredKey(Exception):
	def __init__(self, key: str):
		super().__init__(f'Missing required key "{key}"')


def get_jsondata(file_path: str) -> dict:
	json_file = open(file_path, "r", encoding="utf-8")
	json_data = json.load(json_file)
	json_file.close()
	return json_data


class Config:
	def __init__(self):
		pass

	def __getitem__(self, key: str):
		return self.__getattribute__(key)

	def __setitem__(self, key, value):
		self.__setattr__(key, value)

	def __contains__(self, key: str):
		return hasattr(self, key)

	@staticmethod
	def setdefault(space: 'SpaceLike', key, value):
		if key not in space:
			space[key] = value

	@staticmethod
	def _check_key(space: 'SpaceLike', key: str, value: str | int | list | dict):
		if (value == "REQUIRED" or value == -1) and (key not in space or not space[key]):
			raise ConfigMissingRequiredKey(key)

	def process_config_key(self, key: str, value: str | int | dict | list, space: 'SpaceLike'):
		self._check_key(space, key, value)
		self.setdefault(space, key, value)
		if isinstance(value, dict):
			for k, v in value.items():
				self.process_config_key(k, v, space[key])

	def load_config(self, file: str) -> None:
		for k, v in get_jsondata(file).items():
			self[k] = v


CONFIG: Config = Config()
