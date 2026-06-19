import asyncio
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.core.config import settings


class LLMClient:
    def __init__(self):
        self.provider = settings.llm_provider
        self.model = settings.llm_model
        self._openai = None
        self._anthropic = None
        self._last_call = 0.0

    def _get_openai(self):
        if self._openai is None:
            kwargs = {"api_key": settings.openai_api_key}
            if settings.openai_base_url:
                kwargs["base_url"] = settings.openai_base_url
            self._openai = AsyncOpenAI(**kwargs)
        return self._openai

    def _get_anthropic(self):
        if self._anthropic is None:
            self._anthropic = AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._anthropic

    async def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        # Rate limit: max 1 call per 0.25 seconds
        now = asyncio.get_event_loop().time()
        since_last = now - self._last_call
        if since_last < 0.25:
            await asyncio.sleep(0.25 - since_last)
        self._last_call = asyncio.get_event_loop().time()

        if self.provider == "anthropic":
            client = self._get_anthropic()
            msg = await client.messages.create(
                model=self.model,
                system=system,
                messages=[{"role": "user", "content": user}],
                max_tokens=2000,
                temperature=temperature,
            )
            return msg.content[0].text
        else:
            client = self._get_openai()
            resp = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""


llm = LLMClient()
