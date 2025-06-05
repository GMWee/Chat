import json

import aiohttp
from typing_extensions import override

from src.base.config import CONFIG


class AiContext:
	ROLE_AI = "ai"
	ROLE_USER = "user"
	ROLE_SYSTEM = "system"

	def __init__(self):
		self.context = []

	def add_message(self, message: str, role: str = ROLE_USER):
		self.context.append({
			"role": role,
			"content": message
		})

	def add_image(self, image_b64: str, message: str = "", role: str = ROLE_USER):
		self.context.append({
			"role": role,
			"image_format": "jpeg",
			"image_data": image_b64,
			"content": message
		})

	def add_audio(self, audio_b64: str, message: str = "", role: str = ROLE_USER):
		self.context.append({
			"role": role,
			"audio_format": "ogg",
			"audio_data": audio_b64,
			"content": message,
		})


class AiApi:
	async def _do_http_request(self, url: str, data):
		headers = {
			"Authorization": f"Bearer {CONFIG["proxy_api_key"]}",
			"Content-Type": "application/json"
		}

		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, json=data) as response:
				j = await response.json()
				if "id" in j and "error" in j["id"]:
					raise Exception(json.dumps(j))
				return j

	def _convert_context(self, context: AiContext):
		raise NotImplementedError

	async def request(self, model: str, context: AiContext, max_tokens: int = 2048):
		raise NotImplementedError


class GoogleApi(AiApi):
	@override
	def _convert_context(self, context: AiContext):
		data = []

		for ctx in context.context:
			a = {"parts": []}

			# Image
			if "image_data" in ctx:
				a["parts"].append({
					"inline_data": {
						"mime_type": f"image/{ctx['image_format']}",
						"data": ctx["image_data"]
					}
				})

			# Audio
			if "audio_data" in ctx:
				a["parts"].append({
					"inline_data": {
						"mime_type": f"audio/{ctx['audio_format']}",
						"data": ctx["audio_data"]
					}
				})

			a["parts"].append({
				"text": ctx["content"]
			})

			a["role"] = ctx["role"]
			if ctx["role"] == AiContext.ROLE_AI:
				a["role"] = "model"
			elif ctx["role"] == AiContext.ROLE_SYSTEM:
				a["role"] = "user"

			data.append(a)

		return data

	@override
	async def request(self, model: str, context: AiContext, max_tokens: int = 8096):
		contents = self._convert_context(context)

		data = {
			"contents": contents,
			"generation_config": {
				"max_output_tokens": max_tokens
			}
		}

		res = await self._do_http_request(
			f"https://oai.weegam.com/proxy/google-ai/v1beta/models/{model}:generateContent", data)
		return res["candidates"][0]["content"]


class OpenAiApi(AiApi):
	@override
	def _convert_context(self, context: AiContext):
		data = []

		for ctx in context.context:
			a = {"content": ctx["content"], "role": ctx["role"]}

			if "image_data" in ctx:
				a["content"] = [
					{"type": "text", "text": ctx["content"]},
					{"type": "image_url", "image_url": {"url": f"data:image/{ctx['image_format']};base64,{ctx["image_data"]}"}}
				]

			if ctx["role"] == AiContext.ROLE_AI:
				a["role"] = "assistant"

			data.append(a)

		return data

	@override
	async def request(self, model: str, context: AiContext, max_tokens: int = 8096, system: str = ""):
		messages = self._convert_context(context)

		data = {
			"model": model,
			"max_tokens": max_tokens,
			"messages": messages
		}

		res = await self._do_http_request("https://oai.weegam.com/proxy/openai/v1/chat/completions", data)
		return res

class AnthropicAiApi(AiApi):
	@override
	def _convert_context(self, context: AiContext):
		data = []
		system_prompt: str = ""

		for ctx in context.context:
			a = {"content": ctx["content"], "role": ctx["role"]}

			if "image_data" in ctx:
				a["content"] = [
					{"type": "text", "text": ctx["content"]},
					{"type": "image_url", "image_url": {"url": f"data:image/{ctx['image_format']};base64,{ctx["image_data"]}"}}
				]

			if ctx["role"] == AiContext.ROLE_AI:
				a["role"] = "assistant"

			if ctx["role"] == AiContext.ROLE_SYSTEM:
				system_prompt = ctx["content"]
				continue

			data.append(a)

		return data, system_prompt

	@override
	async def request(self, model: str, context: AiContext, max_tokens: int = 8096, system: str = ""):
		messages, system_prompt = self._convert_context(context)

		data = {
			"model": model,
			"max_tokens": max_tokens,
			"messages": messages,
			"system": system
		}

		print(data)
		res = await self._do_http_request("https://oai.weegam.com/proxy/anthropic/v1/messages", data)
		return res
