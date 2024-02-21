from pathlib import Path
from collections import Counter
from copy import copy


class CFEX:
	magic_values = ['$_key', '$_section']
	def __init__(self, cfex_path, context={}):
		self.path = Path(cfex_path)
		self.env = {**context}
		self.for_clean = []
		self.curent_section = None
		self.prod = False

	def _read(self):
		if self.path.is_file():
			with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
				self.raw_data = f.read()
				if self.raw_data.replace('\n', '') != '' and self.path.name == 'prod.cfex':
					self.prod = True
		else:
			self.raw_data = ''

	def load(self):
		self._read()
		if self.raw_data == '':
			return {}
		else:
			self.process()
			self.clean_private()
			return self.env

	def process(self):
		self.lines = self.get_lines()
		for line, _type in self.getter(self.lines):
			if _type == 'var':
				self.get_var(line)
			elif _type == list or _type == dict:
				self.set_section(line, _type)
			elif _type == 'include':
				self.include(line)

	def get_lines(self, ):
		return self.raw_data.split('\n')

	def getter(self, lines):
		for line in lines:
			if line == '':
				self.clean_ref()
				continue

			if line.startswith('#'):
				continue

			if line.startswith('@include'):
				yield line, 'include'
				continue

			if line.startswith('[') and line.endswith(']'):
				yield line, dict
				continue

			if line.startswith('(') and line.endswith(')'):
				yield line, list
				continue

			yield line, 'var'

	def get_var(self, line):
		k, v = line.split('=', 1)
		k = k.strip()
		v = v.strip()

		if k.startswith('__'):
			self.for_clean.append(k)

		is_link = False
		if v.startswith('$') and v not in self.magic_values:
			v = self.get_value_by_link(k, v.replace('$', ''))
			is_link = True

		if isinstance(v, str) and not is_link:
			if v.replace('-', '').replace('+', '').replace('e', '').replace('_', '').replace('.', '').isdigit():
				counter = Counter(v)
				if counter['.'] == 1:
					if '.' in v:
						v = float(v)
				elif counter['.'] == 0: 
					v = int(v)

			if v in ['True', 'true']:
				v = True
			elif v in ['False', 'false']:
				v = False
			elif v in ['None', 'none', 'undefined']:
				v = None

		if isinstance(v, str) and not is_link:
			if (v.startswith('"') or v.startswith('\'')) and (v.endswith('"') or v.endswith('\'')):
				v = v[1:-1]

		if isinstance(v, str):
			if '{{' in v and '}}' in v:
				v = self.set_value(v)

		if self.curent_section is None:
			self.env[k] = v
		else:
			if k == '':
				self.get_section().append(v)
			else:
				self.get_section()[k] = v

	def get_section(self):
		ref = self.env
		for e in self.curent_section.split('.'):
			ref = self.env[e]
		return ref

	def set_section(self, line, _type):
		section = line.replace('(','').replace(')','').replace('[','').replace(']','')
		if section.startswith('__'):
			self.for_clean.append(section)
		self.env[section] = _type()
		self.curent_section = section

	def get_value_by_link(self, key, link):
		ref = self.env
		for e in link.split('.'):
			if isinstance(ref, list) and e.isdigit():
				e = int(e)
			ref = ref[e]
		ref = self.check_items('$_key', ref, key)
		ref = self.check_items('$_section', ref, self.curent_section)
		return ref

	def set_value(self, v):
		while True:
			try:
				start = v.index('{{') + 2
				end = v.index('}}')
				key = v[start:end]

				v = v.replace('{{'+key+'}}', self.env.get(key, key))
			except:
				return v

	def check_items(self, key, ref, value):
		if isinstance(ref, str):
			if ref == key:
				return value
		if isinstance(ref, list):
			if key in ref:
				_list = copy(ref)
				_list[_list.index(key)] = value
				return _list
		if isinstance(ref, dict):
			if key in ref.values():
				for k,v in list(ref.items()):
					if v == key:
						_dict = copy(ref)
						_dict[k] = value
						return _dict
		return ref

	def include(self, link):
		_, path = link.split(' ')
		path = path.strip()
		if path.startswith('$'):
			path = self.get_value_by_link(None, path.replace('$', ''))
		self.env.update(CFEX(path).load())

	def clean_ref(self):
		self.curent_section = None

	def clean_private(self):
		for obj in self.for_clean:
			del self.env[obj]
