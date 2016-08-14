import hashlib
import json
import os
import time
from argparse import Namespace as ndict

import requests


class vk_api(object):
	__k_count = 100

	@staticmethod
	def md5(s):
		h = hashlib.md5()
		h.update(s.encode("utf-8"))
		return h.hexdigest()

	def __load_hash(self):
		self.__hash.clear()
		if not os.path.isdir(self.__k_hash_path):
			os.mkdir(self.__k_hash_path)

		for file_path_dir in os.listdir(self.__k_hash_path):
			file_path = self.__k_hash_path + file_path_dir
			key = os.path.splitext(os.path.basename(file_path))[0]
			with open(file_path, "r") as file:
				self.__hash[key] = json.loads(file.read())

	def __save_hash(self, s, request):
		if not os.path.isdir(self.__k_hash_path):
			os.mkdir(self.__k_hash_path)

		file_name = s + ".json"
		with open(self.__k_hash_path + file_name, "w") as file:
			file.write(json.dumps(request, sort_keys=True, indent=4, separators=(',', ': ')))

	def clear_hash(self):
		for file_path_dir in os.listdir(self.__k_hash_path):
			file_path = self.__k_hash_path + file_path_dir
			os.remove(file_path)

		os.rmdir(self.__k_hash_path)

		self.__hash = {}

	def __init__(self):
		self.__token = ""
		self.__version = 5.44
		self.__sleep_sec = 0.2
		self.__first_get = False
		self.__k_hash_path = os.getcwd() + "\\vk_hash\\"
		self.__hash = {}

		self.debug = True
		self.__load_hash()

	@staticmethod
	def __get_request(request_str):
		return requests.get(request_str)

	@staticmethod
	def __create_request_string(method, params):
		params_string = "".join(["&{0}={1}".format(key, value) for key, value in sorted(params.items())])
		return method + params_string

	@property
	def token(self):
		if not self.__token:
			if os.path.isfile("token.txt"):
				with open("token.txt", "r", encoding="utf-8") as token_file:
					self.__token = token_file.read()
			else:
				with open("credentials.json", "r", encoding="utf-8") as credentials_file:
					credentials = json.loads(credentials_file.read())

					credentials["v"] = self.__version
					request_string = vk_api.__create_request_string("https://oauth.vk.com/token?grant_type=password", credentials)

					request = vk_api.__get_request(request_string)
					request_content = request.json()
					self.__token = request_content["access_token"]

					with open("token.txt", "w", encoding="utf-8") as token_file:
						token_file.write(self.__token)

		return self.__token

	def __get_string_request(self, request_string):
		if not self.__first_get:
			self.__first_get = True
		else:
			time.sleep(self.__sleep_sec)

		request = vk_api.__get_request(request_string)
		request_content = request.json()["response"]
		return request_content

	def get(self, method, **kwargs):
		rargs = dict(kwargs)
		rargs["v"] = self.__version
		request_string = vk_api.__create_request_string("https://api.vkontakte.ru/method/{0}?access_token={1}".format(method, self.token), rargs)

		if self.debug:
			key = vk_api.md5(request_string)
			if key in self.__hash:
				request_content = self.__hash[key]
			else:
				request_content = self.__get_string_request(request_string)
				self.__hash[key] = request_content
				self.__save_hash(key, request_content)
		else:
			request_content = self.__get_string_request(request_string)

		return request_content

	def chain_items(self, *args, **kwargs) -> ndict:
		k_count_s = "count"
		k_items_s = "items"

		max_count = 0
		has_limit = k_count_s in kwargs
		if has_limit:
			max_count = kwargs[k_count_s]
			del kwargs[k_count_s]

		start_count = vk_api.__k_count if has_limit and max_count > vk_api.__k_count else max_count

		offset = 0
		json_response = self.get(*args, **kwargs, offset=offset, count=start_count)

		total_count = json_response[k_count_s]
		count = min(total_count, max_count) if has_limit else total_count

		result = json_response[k_items_s]
		offset += len(result)

		while offset < count:
			next_count = min(vk_api.__k_count, count - offset)
			next_json = self.get(*args, **kwargs, offset=offset, count=next_count)
			next_result = next_json[k_items_s]
			offset += len(next_result)
			result.extend(next_result)

		return ndict(json=json_response, items=result)

	def get_own_id(self) -> int:
		info = self.get("users.get")[0]
		return info["id"]