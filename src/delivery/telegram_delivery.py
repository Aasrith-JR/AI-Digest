from typing import List
from telegram import Bot

from core.entities import DigestEntry
from delivery.base import DeliveryChannel


class TelegramDelivery(DeliveryChannel):
    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    async def deliver(
        self,
        *,
        persona: str,
        digest_date: str,
        entries: List[DigestEntry],
    ) -> None:
        header = f"*{persona} Digest – {digest_date}*\n\n"
        message = [header]

        for entry in entries:
            message.append(f"*{entry.title}*")
            message.append(entry.summary)
            message.append(f"_Why it matters:_ {entry.why_it_matters}")
            for url in entry.source_urls:
                message.append(url)
            message.append("\n")

        await self.bot.send_message(
            chat_id=self.chat_id,
            text="\n".join(message),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
