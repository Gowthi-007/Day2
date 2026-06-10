import asyncio
import time
from typing import Any, Dict

import aiohttp


async def fetch_user_profile(user_id: int) -> Dict[str, Any]:
	"""Fetch a user profile from an external API and print the runtime.

	Uses jsonplaceholder.typicode.com for demo purposes.
	"""
	url = f"https://jsonplaceholder.typicode.com/users/{user_id}"
	start = time.perf_counter()
	async with aiohttp.ClientSession() as session:
		async with session.get(url) as resp:
			resp.raise_for_status()
			data = await resp.json()
	runtime = time.perf_counter() - start
	print(f"Fetched user {user_id} in {runtime:.4f} seconds")
	return data


if __name__ == "__main__":
	async def main():
		profile = await fetch_user_profile(1)
		print(profile)

	asyncio.run(main())

