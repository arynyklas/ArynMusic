from aiohttp import ClientSession

from json import load as load_json, dump as dump_json

from typing import List


def get_config(filename: str) -> dict:
    with open(filename, "r", encoding="utf-8") as file:
        return load_json(file)


def save_config(filename: str, data: dict) -> None:
    with open(filename, "w", encoding="utf-8") as file:
        dump_json(data, file, ensure_ascii=False, indent=4)


async def download_file(url: str, filename: str) -> None:
    async with ClientSession() as session:
        async with session.get(url) as response:
            chunks: List[bytes] = []

            while True:
                chunk = await response.content.readany()

                if not chunk:
                    break

                chunks.append(chunk)

            with open(filename, "wb") as file:
                file.write(b"".join(chunks))
