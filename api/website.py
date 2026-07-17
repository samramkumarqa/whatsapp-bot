from fastapi import APIRouter
from pydantic import BaseModel
import asyncio
import logging

from crawler import discover_links
from incremental_ingest import incremental_ingest

from website_manager import (
    add_website as save_website,
    delete_website,
    get_websites,
)
logger = logging.getLogger(__name__)

router = APIRouter()

class WebsiteRequest(BaseModel):
    user_id: str
    url: str
    crawl: bool = False
    max_pages: int = 50

def schedule_reindex(user_id: str):

    logger.info(
        f"Scheduling background reindex for {user_id}"
    )
    asyncio.create_task(
        asyncio.to_thread(
            incremental_ingest,
            user_id
        )
    )

@router.post("/reindex/{user_id}")
async def reindex(user_id: str):

    try:
        await asyncio.to_thread(
            incremental_ingest,
            user_id
        )

        return {
            "status": "success",
            "message": f"Reindexed {user_id}"
        }

    except Exception as e:

        logger.exception(e)

        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/websites")
async def websites():

    sites = get_websites()

    return {
        "status": "success",
        "count": len(sites),
        "websites": sorted(sites)
    }


@router.post("/website")
async def add_site(request: WebsiteRequest):

    try:

        logger.info(
            f"Adding website(s) for {request.user_id}"
        )

        added_urls = []

        # ------------------------------------
        # Crawl entire website
        # ------------------------------------

        if request.crawl:

            discovered_urls = discover_links(
                request.url,
                max_pages=request.max_pages
            )

            logger.info(
                f"Discovered {len(discovered_urls)} pages"
            )

            for url in discovered_urls:

                logger.info(
                    f"Discovered: {url}"
                )

                if save_website(
                    request.user_id,
                    url
                ):
                    added_urls.append(url)

        # ------------------------------------
        # Single page
        # ------------------------------------

        else:

            if save_website(
                request.user_id,
                request.url
            ):
                added_urls.append(request.url)

        # ------------------------------------
        # Nothing new
        # ------------------------------------

        if not added_urls:

            return {
                "status": "exists",
                "message": "Website(s) already exist."
            }

        # ------------------------------------
        # Background Reindex
        # ------------------------------------

        logger.info(
            f"Starting background indexing for {request.user_id}"
        )

        schedule_reindex(request.user_id)

        return {

            "status": "success",

            "added_count": len(added_urls),

            "added_urls": added_urls,

            "message": "Background indexing started."

        }

    except Exception as e:

        logger.exception(
            f"Website add failed: {e}"
        )

        return {

            "status": "error",

            "message": str(e)

        }

@router.delete("/website")
async def remove_site(
    request: WebsiteRequest
):

    try:

        removed = delete_website(
            request.user_id,
            request.url
        )

        if not removed:
            return {
                "status": "not_found",
                "message": "Website not found"
            }

        schedule_reindex(request.user_id)

        return {
            "status": "success",
            "message": "Website removed and reindex started"
        }

    except Exception as e:

        logger.exception(
            f"Delete website error: {e}"
        )

        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/websites/{user_id}")
async def list_websites(user_id: str):

    websites = get_websites(user_id)

    return {
        "status": "success",
        "count": len(websites),
        "websites": websites
    }

