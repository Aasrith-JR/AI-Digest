import asyncio
from datetime import date
import logging
import time

from services.config import load_config
from services.logging import setup_logging
from workflows.genai_news import GenAINewsPipeline
from workflows.product_ideas import ProductIdeasPipeline
from delivery.file_delivery import FileDelivery
from delivery.email_delivery import EmailDelivery
from delivery.telegram_delivery import TelegramDelivery
from delivery.base import DeliveryChannel


async def main() -> None:
    start_time = time.perf_counter()
    setup_logging()
    logger = logging.getLogger(__name__)

    config = load_config()
    today = date.today().isoformat()

    logger.info("Starting intelligence digest run")

    pipelines = []

    if config.PERSONA_GENAI_NEWS_ENABLED:
        pipelines.append(GenAINewsPipeline())

    if config.PERSONA_PRODUCT_IDEAS_ENABLED:
        pipelines.append(ProductIdeasPipeline())

    # ----------------------------
    # Initialize delivery channels
    # ----------------------------
    deliveries = list[DeliveryChannel]([FileDelivery()])

    if config.EMAIL_ENABLED:
        deliveries.append(
            EmailDelivery(
                smtp_host=config.EMAIL_SMTP_HOST,
                smtp_port=config.EMAIL_SMTP_PORT,
                username=config.EMAIL_USERNAME,
                password=config.EMAIL_PASSWORD,
                sender=config.EMAIL_FROM,
                recipient=config.EMAIL_TO,
            )
        )

    if config.TELEGRAM_ENABLED:
        deliveries.append(
            TelegramDelivery(
                bot_token=config.TELEGRAM_BOT_TOKEN,
                chat_id=config.TELEGRAM_CHAT_ID,
            )
        )

    # ----------------------------
    # Execute pipelines
    # ----------------------------
    for pipeline in pipelines:
        try:
            logger.info(f"Running persona pipeline: {pipeline.name}")
            entries = await pipeline.run()

            if not entries:
                logger.info(f"No entries for persona {pipeline.name}")
                continue

            for delivery in deliveries:
                try:
                    await delivery.deliver(
                        persona=pipeline.name,
                        digest_date=today,
                        entries=entries,
                    )
                    logger.info(
                        f"Delivered {pipeline.name} digest via {delivery.name}"
                    )
                except Exception as e:
                    logger.error(
                        f"Delivery failed: persona={pipeline.name}, channel={delivery.name}, error={e}"
                    )

        except Exception as e:
            logger.exception(f"Pipeline failed: {pipeline.name}: {e}")

    logger.info("Digest run completed")
    end_time = time.perf_counter()
    logger.info(f"Total time: {end_time - start_time}")


if __name__ == "__main__":
    asyncio.run(main())
