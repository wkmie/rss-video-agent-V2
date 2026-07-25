from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx


FAKE_TRANSLATION_PREFIXES = ("中文解读：", "中文标题：")
QUICK_TRANSLATION_TIMEOUT_SECONDS = 4


def is_effective_chinese(value: str | None) -> bool:
    if not value:
        return False
    text = value.strip()
    for prefix in FAKE_TRANSLATION_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()

    chinese_count = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    if chinese_count < 2:
        return False
    return chinese_count / max(chinese_count + latin_count, 1) >= 0.15


def needs_title_translation(title: str, title_zh: str | None = None) -> bool:
    return not is_effective_chinese(title_zh or title)


async def _google_translate(client: httpx.AsyncClient, title: str) -> str:
    response = await client.get(
        "https://translate.googleapis.com/translate_a/single",
        params={
            "client": "gtx",
            "sl": "auto",
            "tl": "zh-CN",
            "dt": "t",
            "q": title,
        },
    )
    response.raise_for_status()
    data = response.json()
    translated = "".join(part[0] for part in data[0] if part and part[0]).strip()
    return translated if is_effective_chinese(translated) else ""


async def _mymemory_translate(client: httpx.AsyncClient, title: str) -> str:
    response = await client.get(
        "https://api.mymemory.translated.net/get",
        params={"q": title, "langpair": "en|zh-CN"},
    )
    response.raise_for_status()
    data = response.json()
    if int(data.get("responseStatus") or 0) != 200:
        return ""
    translated = str((data.get("responseData") or {}).get("translatedText") or "").strip()
    if "MYMEMORY WARNING" in translated.upper():
        return ""
    return translated if is_effective_chinese(translated) else ""


async def translate_titles(items: list[Any]) -> tuple[dict[str, str], list[str]]:
    targets = [
        item
        for item in items
        if getattr(item, "title", "") and needs_title_translation(
            getattr(item, "title", ""),
            getattr(item, "title_zh", None),
        )
    ]
    if not targets:
        return {}, []

    translations: dict[str, str] = {}
    semaphore = asyncio.Semaphore(6)
    headers = {"User-Agent": "rss-video-agent/1.0"}

    async def translate_one(client: httpx.AsyncClient, item: Any) -> None:
        async with semaphore:
            title = str(item.title).strip()
            translated = ""
            try:
                translated = await _google_translate(client, title)
            except Exception:
                pass
            if not translated:
                try:
                    translated = await _mymemory_translate(client, title)
                except Exception:
                    pass
            if translated:
                translations[str(item.content_hash)] = translated

    async with httpx.AsyncClient(timeout=3, headers=headers, follow_redirects=False) as client:
        tasks = [asyncio.create_task(translate_one(client, item)) for item in targets]
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=QUICK_TRANSLATION_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    remaining = [item for item in targets if str(item.content_hash) not in translations]
    if remaining:
        translations.update(await _llm_batch_translate(remaining))

    failures = len(targets) - len(translations)
    errors = [f"{failures} 个非中文标题暂时翻译失败，可稍后重新抓取重试"] if failures else []
    return translations, errors


async def _llm_batch_translate(items: list[Any]) -> dict[str, str]:
    from app.llm.client import LLMClient, parse_json_object

    client = LLMClient()
    if not client.enabled:
        return {}

    source_items = [
        {"id": str(item.content_hash), "title": str(item.title).strip()}
        for item in items
    ]
    semaphore = asyncio.Semaphore(3)

    async def translate_batch(batch: list[dict[str, str]]) -> dict[str, str]:
        prompt = f"""将下面新闻标题翻译成简体中文。
要求：
1. 保留 BTC、ETH、Web3、AI、OpenAI、公司名和人名等必要专有名词；
2. 只做准确翻译，不扩写、不总结；
3. 严格输出 JSON 对象，键为 id，值为中文标题；
4. 不要输出 JSON 以外的内容。

输入：
{json.dumps(batch, ensure_ascii=False)}
"""
        async with semaphore:
            try:
                output = await asyncio.wait_for(
                    client.chat(prompt, temperature=0.1),
                    timeout=35,
                )
            except Exception:
                return {}
        parsed = parse_json_object(output)
        if not isinstance(parsed, dict):
            return {}

        translations: dict[str, str] = {}
        valid_ids = {item["id"] for item in batch}
        for content_hash, translated in parsed.items():
            key = str(content_hash)
            value = str(translated).strip()
            if key in valid_ids and is_effective_chinese(value):
                translations[key] = value
        return translations

    batches = [source_items[index : index + 15] for index in range(0, len(source_items), 15)]
    results = await asyncio.gather(*(translate_batch(batch) for batch in batches))
    return {
        content_hash: translated
        for result in results
        for content_hash, translated in result.items()
    }
