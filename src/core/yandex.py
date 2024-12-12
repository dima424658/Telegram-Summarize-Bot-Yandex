import asyncio
import logging
import random
import httpx
from telegram.constants import ReactionEmoji

from fastapi import status


class YandexError(Exception):
    def __init__(
        self,
        message: str,
    ) -> None:
        self.message = message

    def __str__(self) -> str:
        return f"Got error from yandex: {self.message}"


class YandexSummarize:
    def __init__(self, session_id: str) -> None:
        self.logger = logging.getLogger(__name__)
        self.domain: str = "300.ya.ru"
        self.headers: dict = {
            "Content-Type": "application/json",
        }
        self.session_id = session_id

    async def request(self, method: str, endpoint: str, body: dict, headers: dict):
        async with httpx.AsyncClient(http2=True) as client:
            r = await client.request(
                method=method,
                url=f"https://{self.domain}/api/{endpoint}",
                json=body,
                headers=headers,
            )
            if r.status_code != status.HTTP_200_OK:
                raise YandexError("Got wrong response, code {r.status_code}")
            return r.json()

    def parse(self, data: dict):
        text = ""
        for chapter in data["chapters"]:
            emoji = str(random.choice(list(ReactionEmoji)))
            text += f"<b>{emoji}{chapter["content"]}{emoji}</b>\n"
            for thesis in chapter["theses"]:
                text += f"- {thesis["content"]}\n"
            text += "\n"

        text += "<tg-spoiler>#summary</tg-spoiler>"

        return text

    async def generation(self, text: str):
        if len(text) < 200:
            raise YandexError("text is too short")

        headers = self.headers.copy()
        headers["Cookie"] = f"Session_id={self.session_id}"
        res = await self.request(
            method="POST",
            endpoint="generation",
            body={"text": text, "type": "text"},
            headers=headers,
        )

        while True:
            status_code = res["status_code"]
            if status_code == 2:
                break

            have_chapters = res["have_chapters"]
            if have_chapters == False:
                raise YandexError("response has no chapters")

            session_id = res["session_id"]
            if session_id == False:
                raise YandexError("response has no session_id")

            sid = res["session_id"]
            pool_ms = res["poll_interval_ms"]
            await asyncio.sleep(pool_ms / 1000)
            res = await self.request(
                method="POST",
                endpoint="generation",
                body={"session_id": sid, "type": "text"},
                headers=headers,
            )

        return self.parse(res)
