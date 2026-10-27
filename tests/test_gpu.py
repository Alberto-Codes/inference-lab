import asyncio

import httpx
import pytest

from inference_lab.client import infer
from inference_lab.corpus import generate
from inference_lab.experiment import load_corpus


@pytest.mark.gpu
def test_actual_nemotron_extracts_known_text(tmp_path):
    generate(tmp_path)
    page = load_corpus(tmp_path)[0]

    async def execute():
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:8017", timeout=120
        ) as client:
            return await infer(client, page, 120)

    record = asyncio.run(execute())
    assert record["status"] == "success", record
