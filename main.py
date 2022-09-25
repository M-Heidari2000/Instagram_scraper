import asyncio
import aiohttp
import time
import requests
import re
import aiofiles

class Scraper:

	def __init__(self, username: str, Cookie: str, CSRFToken:str):
		self.username = username
		self.Cookie = Cookie
		self.CSRFToken = CSRFToken
		self.idx = 0
		
		self.video_queue = None	

	
	async def start(self):
		user_page_url = f'https://www.instagram.com/{self.username}/'
		user_profile_api = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={self.username}'
		
		response = requests.get(user_page_url, headers={'Cookie': Cookie, 'CSRFToken': CSRFToken})
		X_IG_matcher = re.search(r'"X-IG-App-ID":"([^,]*)"', response.text)
		self.app_id = X_IG_matcher.group(1)

		posts_response = requests.get(user_profile_api, headers={'X-IG-App-ID': self.app_id, 'Cookie': self.Cookie, 'CSRFToken': self.CSRFToken})

		response_dict = posts_response.json()
		self.user_id = response_dict['data']['user']['id']
		self.video_count = response_dict['data']['user']['edge_owner_to_timeline_media']['count']
		self.query_hash = '69cba40317214236af40e7efa697781d'

		edges = response_dict['data']['user']['edge_owner_to_timeline_media']['edges']
		self.video_queue = asyncio.Queue()
		for item in [edge['node']['video_url'] for edge in edges if edge['node']['is_video']]:
			self.video_queue.put_nowait(item)
		end_cursor = response_dict['data']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
		query = f'"id":"{self.user_id}","first":{50},"after":"{end_cursor}"'

		self.session = aiohttp.ClientSession()
		await self.crawl(end_cursor, query)
		await self.download_videos()

	
	async def download_videos(self):
		while not self.video_queue.empty():
			try:
				video_url = await self.video_queue.get()
				self.idx += 1
				async with self.session.get(video_url) as response:
					if response.status == 200:
						print(f'downloading video #{self.idx}')
						f = await aiofiles.open(f'video{self.idx}.mp4', mode='wb')
						await f.write(await response.read())
						await f.close()
					else:
						print(f'error in downloading video{self.idx}')
			except Exception as e:
				print(e)


	async def crawl(self, end_cursor: str, query: str):
		while True:
			try:
				graphql_videos_url = 'https://www.instagram.com/graphql/query/?query_hash=69cba40317214236af40e7efa697781d&variables=' + '{' + query + '}'
				async with self.session.get(graphql_videos_url, headers={'X-IG-App-ID': self.app_id, 'Cookie': self.Cookie, 'CSRFToken': self.CSRFToken}) as graphql_response:
					response_dict = await graphql_response.json()
					for edge in response_dict['data']['user']['edge_owner_to_timeline_media']['edges']:
						if edge['node']['is_video']:
							await self.video_queue.put(edge['node']['video_url'])
			
					end_cursor = response_dict['data']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
					query = f'"id":"{self.user_id}","first":{50},"after":"{end_cursor}"'

				if not response_dict['data']['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']:
					break
			except Exception as e:
				print(e)


if __name__ == '__main__':
	username = 'leomessi'
	Cookie = r'csrftoken=Yjnpq8FgGn4X0r1eM10aDmuXZ7jVSRwl; mid=YymAqQAEAAHgndZYdWvx5Xgudbqn; ig_did=861EA883-9E4E-48CE-BE13-FFDFB8C17055; ig_nrcb=1; dpr=1.2; ds_user_id=55484981050; sessionid=55484981050%3AGk78Z8MIKwXh8h%3A0%3AAYfkH8sT6sELPch7Hphhy1kD5xUKuTy8USAMaFIanw; datr=8o0pY6_95ovClFqnNGjAt47H; rur="VLL\05455484981050\0541695505668:01f7240feac6f228c78669aa98ed9079b5cc194f085f61e64db4c29c5c9308755442e86a"'
	CSRFToken = 'Yjnpq8FgGn4X0r1eM10aDmuXZ7jVSRwl'

	scraper = Scraper(username, Cookie, CSRFToken)

	asyncio.run(scraper.start())
	
