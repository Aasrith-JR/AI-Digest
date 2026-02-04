import asyncio
from datetime import date
import logging
import time

from services.config import load_config
from services.logging import setup_logging
from services.database import Database
from services.vector_store import VectorStore
from services.digest_tracker import DigestTracker
from services.llm import OllamaClient
from workflows.pipeline_factory import create_pipelines_from_config
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

    # ----------------------------
    # Initialize shared services
    # ----------------------------
    llm = OllamaClient(
        base_url=config.OLLAMA_BASE_URL,
        model=config.OLLAMA_MODEL,
    )

    db = Database(config.DATABASE_PATH)
    vector_store = VectorStore(config.FAISS_INDEX_PATH)
    tracker = DigestTracker(db, vector_store)

    # ----------------------------
    # Create pipelines from config
    # ----------------------------
    if config.pipelines:
        # Use new modular pipeline configuration
        pipelines = create_pipelines_from_config(
            pipelines_config=config.pipelines,
            llm=llm,
            tracker=tracker,
        )
        logger.info(f"Created {len(pipelines)} pipelines from config")
    else:
        # Fallback to legacy pipeline configuration
        logger.warning("No pipelines configured, using legacy configuration")
        from workflows.genai_news import GenAINewsPipeline
        from workflows.product_ideas import ProductIdeasPipeline

        pipelines = []
        if config.PERSONA_GENAI_NEWS_ENABLED:
            pipelines.append(GenAINewsPipeline(llm=llm, tracker=tracker))
        if config.PERSONA_PRODUCT_IDEAS_ENABLED:
            pipelines.append(ProductIdeasPipeline(llm=llm, tracker=tracker))

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
                colors=config.email_colors.model_dump(),
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
