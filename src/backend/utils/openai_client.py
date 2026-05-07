import os
from typing import Optional, Dict, Any

from loguru import logger
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.backend.llm.stt_cleaner import build_stt_cleanup_prompt


class AsyncOpenAIClient:
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        timeout: Optional[int] = None,
    ):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.timeout = timeout if timeout is not None else 30

    def _build_prompt(self, raw_text: str) -> str:
        return build_stt_cleanup_prompt(raw_text)

    @retry(
        stop=stop_after_attempt(2),  # retry max 2 times
        wait=wait_exponential(multiplier=1, min=1, max=10),  # backoff: 1s → 10s
        retry=retry_if_exception_type(Exception),  # can refine later
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        event_name: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sends prompt to OpenAI and returns:
        {
            "text": str,
            "usage": {
                "input": int,
                "output": int,
                "total": int
            }
        }
        """
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )

            # --- Guard: choices existence ---
            if not response.choices or len(response.choices) == 0:
                logger.error("Empty response choices received from OpenAI")
                raise ValueError("No choices returned from OpenAI API")

            message = response.choices[0].message

            # --- Guard: content existence ---
            if not message or not message.content:
                logger.error("Empty message content received from OpenAI")
                raise ValueError("No content in OpenAI response")

            text_output = message.content.strip()

            # --- Usage extraction with safety ---
            usage = response.usage or {}
            input_tokens = getattr(usage, "prompt_tokens", 0)
            output_tokens = getattr(usage, "completion_tokens", 0)
            total_tokens = getattr(usage, "total_tokens", 0)

            # Logging (structured)
            logger.info(
                {
                    "event": event_name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                }
            )

            return {
                "text": text_output,
                "usage": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens,
                },
            }

        except Exception as e:
            logger.exception(
                f"Error {e} : while generating response for event: {event_name}"
            )
            raise

    async def clean_stt_transcript(self, raw_text: str, event_name: str) -> str:
        prompt = self._build_prompt(raw_text)
        result = await self.generate(prompt, event_name=event_name)
        return result["text"], result["usage"]
