import os
import time
from abc import ABC, abstractmethod
from typing import Generator, Any
from app.config import settings


class LLMProvider(ABC):
    """Abstract interface for LLM operations."""

    @abstractmethod
    def summarize(self, text: str, style: str = "detailed", length: str = "standard") -> str:
        """Summarize input text according to specified style and length."""
        pass

    @abstractmethod
    def chat_stream(self, messages: list[dict], document_context: str = "") -> Generator[str, None, None]:
        """Stream conversational responses grounded in document context."""
        pass


class GeminiProvider(LLMProvider):
    """Official Google Gemini SDK Implementation."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or settings.gemini_model or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
        self._client = None
        self._last_call_time = 0.0

    def _get_client(self):
        if not self.api_key:
            return None
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Gemini Client: {str(e)}")
        return self._client

    def _rate_limit_pause(self):
        """Basic rate limiter to ensure we don't exceed rate bounds."""
        now = time.time()
        elapsed = now - self._last_call_time
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        self._last_call_time = time.time()

    def _call_with_retry(self, fn, max_retries: int = 3):
        """Execute callable with exponential backoff on transient errors."""
        delay = 1.0
        last_error = None
        for attempt in range(max_retries):
            try:
                self._rate_limit_pause()
                return fn()
            except Exception as e:
                err_str = str(e).lower()
                last_error = e
                # Retry on rate limit (429) or temporary server errors (503)
                if "429" in err_str or "resource_exhausted" in err_str or "503" in err_str or "timeout" in err_str:
                    time.sleep(delay)
                    delay *= 2.0
                else:
                    raise
        raise last_error

    def summarize(self, text: str, style: str = "detailed", length: str = "standard") -> str:
        if not text.strip():
            return "The document is empty; no text could be extracted for summarization."

        client = self._get_client()
        if not client:
            return (
                "**Gemini API Key Required**\n\n"
                "To enable AI document summarization, please configure your Gemini API key:\n"
                "1. Add `GEMINI_API_KEY=your_key_here` to your `.env` file\n"
                "2. Restart the server"
            )

        # Style specifications
        style_prompts = {
            "short": "Provide a concise, 1-2 paragraph executive summary capturing the core premise.",
            "detailed": "Provide an in-depth summary covering background, key arguments, data, and conclusions.",
            "bullet_points": "Format the summary strictly as a clean, structured list of bullet points with bold section headers.",
            "key_takeaways": "Highlight the 3-5 most critical actionable takeaways, obligations, or findings from this document.",
        }
        style_instruction = style_prompts.get(style, style_prompts["detailed"])

        length_prompts = {
            "brief": "Keep it under 150 words.",
            "standard": "Provide a balanced overview of 300-500 words.",
            "comprehensive": "Provide an exhaustive breakdown of 700-1000 words.",
        }
        length_instruction = length_prompts.get(length, length_prompts["standard"])

        # Map-Reduce for long documents (> 12,000 characters)
        chunk_size = 10000
        overlap = 500
        if len(text) > 12000:
            chunks = []
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunks.append(text[start:end])
                if end == len(text):
                    break
                start = end - overlap

            intermediate_summaries = []
            for i, chunk in enumerate(chunks):
                prompt = (
                    f"Summarize the key information from Part {i + 1} of this document:\n\n{chunk}"
                )
                try:
                    res = self._call_with_retry(
                        lambda: client.models.generate_content(
                            model=self.model_name,
                            contents=prompt
                        )
                    )
                    if res and res.text:
                        intermediate_summaries.append(res.text.strip())
                except Exception as e:
                    intermediate_summaries.append(f"[Part {i + 1} summary error: {str(e)}]")

            combined_intermediates = "\n\n".join(intermediate_summaries)
            final_prompt = (
                f"Below are summaries of each section of a large document. Combine them into a coherent final summary.\n"
                f"Style: {style_instruction}\n"
                f"Length: {length_instruction}\n\n"
                f"SECTION SUMMARIES:\n{combined_intermediates}"
            )
            res = self._call_with_retry(
                lambda: client.models.generate_content(
                    model=self.model_name,
                    contents=final_prompt
                )
            )
            return res.text.strip() if res and res.text else "Unable to generate final summary."

        # Direct single-pass for standard documents
        prompt = (
            f"You are an expert document analysis assistant. Analyze the document provided below and generate a summary.\n"
            f"Style requirement: {style_instruction}\n"
            f"Length requirement: {length_instruction}\n\n"
            f"DOCUMENT CONTENT:\n{text}"
        )

        res = self._call_with_retry(
            lambda: client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
        )
        return res.text.strip() if res and res.text else "Unable to generate summary."

    def chat_stream(self, messages: list[dict], document_context: str = "") -> Generator[str, None, None]:
        client = self._get_client()
        if not client:
            yield "Gemini API key is not configured. Please add `GEMINI_API_KEY=your_key` in `.env` to enable interactive document intelligence."
            return

        # Prepare system instruction and grounding
        system_instruction = (
            "You are a helpful, professional document analysis assistant. "
            "You answer questions grounded strictly in the provided document context whenever applicable. "
            "If the information is not present in the document, acknowledge that clearly and provide helpful guidance. "
            "Never fabricate clauses or factual claims."
        )

        conversation_parts = [system_instruction]
        if document_context:
            # Truncate context to safe token budget for prompt
            bounded_context = document_context[:30000]
            conversation_parts.append(f"GROUNDING DOCUMENT CONTEXT:\n{bounded_context}\n--- END OF CONTEXT ---")

        # Append conversation turns
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            conversation_parts.append(f"{role.upper()}: {content}")

        conversation_parts.append("ASSISTANT: ")
        full_prompt = "\n\n".join(conversation_parts)

        try:
            self._rate_limit_pause()
            response_stream = client.models.generate_content_stream(
                model=self.model_name,
                contents=full_prompt
            )
            for chunk in response_stream:
                if chunk and chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"\n[Error connecting to Gemini: {str(e)}]"


# Default singleton provider
_provider_instance: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = GeminiProvider()
    return _provider_instance


def set_llm_provider(provider: LLMProvider):
    """Allow mocking or swapping LLM provider for tests."""
    global _provider_instance
    _provider_instance = provider
