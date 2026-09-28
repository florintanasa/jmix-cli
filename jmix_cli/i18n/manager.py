# -
# Copyright (c) 2026 Florin Tanasă <florin.tanasa@gmail.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# -

import http.client
import json
import threading
from pathlib import Path
from typing import Any

from jmix_cli.core.config import get_ollama_endpoint, get_ollama_model


class TranslationError(Exception):
    """Base exception for translation errors."""
    pass


class TranslationServiceError(TranslationError):
    """Raised when the translation service is unavailable."""
    pass


class TranslationDecodeError(TranslationError):
    """Raised when translation response cannot be parsed."""
    pass


class TranslationCache:
    """Thread-safe translation cache with persistence."""
    
    _CACHE_FILE = Path(".ollama_translation_cache.json")
    _cache_lock = threading.Lock()
    _translation_cache: dict[str, str] = {}
    _cache_loaded = False
    
    @classmethod
    def load(cls) -> None:
        """Load cache from disk. Thread-safe."""
        if cls._cache_loaded:
            return
        with cls._cache_lock:
            if cls._cache_loaded:
                return
            if cls._CACHE_FILE.exists():
                try:
                    cls._translation_cache = json.loads(
                        cls._CACHE_FILE.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError, OSError):
                    cls._translation_cache = {}
            cls._cache_loaded = True
    
    @classmethod
    def persist(cls) -> None:
        """Persist cache to disk. Thread-safe."""
        with cls._cache_lock:
            try:
                cls._CACHE_FILE.write_text(
                    json.dumps(cls._translation_cache, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except OSError:
                pass
    
    @classmethod
    def get(cls, key: str) -> str | None:
        """Get value from cache."""
        return cls._translation_cache.get(key)
    
    @classmethod
    def set(cls, key: str, value: str) -> None:
        """Set value in cache."""
        cls._translation_cache[key] = value
    
    @classmethod
    def clear(cls) -> None:
        """Clear cache."""
        with cls._cache_lock:
            cls._translation_cache = {}
            cls._cache_loaded = False
    
    @classmethod
    def get_stats(cls) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(cls._translation_cache),
            "file": str(cls._CACHE_FILE)
        }


class TranslationManager:
    """Centralized translation management with caching and connection pooling."""
    
    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the translation manager.
        
        Args:
            cache_dir: Optional directory for cache file. If None, uses current dir.
        """
        if cache_dir:
            TranslationCache._CACHE_FILE = cache_dir / ".ollama_translation_cache.json"
        self._host, self._port = get_ollama_endpoint()
        self._model = get_ollama_model()
        self._connection: http.client.HTTPConnection | None = None
        self._lock = threading.Lock()
    
    def _ensure_connection(self) -> None:
        """Ensure HTTP connection is established. Thread-safe."""
        if self._connection is not None:
            return
        with self._lock:
            if self._connection is None:
                self._connection = http.client.HTTPConnection(
                    self._host, self._port, timeout=10
                )
    
    def _close_connection(self) -> None:
        """Close HTTP connection. Thread-safe."""
        if self._connection is not None:
            with self._lock:
                if self._connection is not None:
                    try:
                        self._connection.close()
                    except Exception:
                        pass
                    finally:
                        self._connection = None
    
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "en",
        use_cache: bool = True
    ) -> str:
        """Translate text using Ollama.
        
        Args:
            text: Text to translate
            target_language: Target language name (e.g., "Romanian", "German")
            source_language: Source language (default: "en")
            use_cache: Whether to use cache (default: True)
            
        Returns:
            Translated text or original text if translation fails
            
        Raises:
            TranslationServiceError: If translation service is unavailable
            TranslationDecodeError: If response cannot be parsed
        """
        if not text or not target_language:
            return text
            
        cache_key = f"{target_language}:{text}"
        
        if use_cache:
            TranslationCache.load()
            cached = TranslationCache.get(cache_key)
            if cached is not None:
                return cached
        
        self._ensure_connection()
        
        prompt = (
            f"Translate the following software UI label from {source_language} "
            f"into {target_language}. Return ONLY the translated string, without "
            f"quotes, explanations, or introductory text. Label: {text}"
        )
        
        try:
            payload = json.dumps({
                "model": self._model,
                "prompt": prompt,
                "stream": False
            })
            headers = {"Content-Type": "application/json"}
            self._connection.request("POST", "/api/generate", payload, headers)
            response = self._connection.getresponse()
            
            if response.status != 200:
                raise TranslationServiceError(
                    f"Translation service returned status {response.status}"
                )
            
            data = json.loads(response.read().decode("utf-8"))
            translated_text = data.get("response", "").strip()
            
            translated_text = translated_text.replace('"', "").replace("'", "")
            result = translated_text if translated_text else text
            
            if use_cache:
                TranslationCache.set(cache_key, result)
                TranslationCache.persist()
            
            return result
            
        except (ConnectionError, TimeoutError, http.client.HTTPException) as e:
            raise TranslationServiceError(f"Cannot connect to translation service: {e}")
        except json.JSONDecodeError as e:
            raise TranslationDecodeError(f"Cannot parse translation response: {e}")
        finally:
            self._close_connection()
    
    def bulk_translate(
        self,
        items: list[dict[str, str]],
        target_language: str
    ) -> dict[str, str]:
        """Translate multiple items at once.
        
        Args:
            items: List of dicts with "text" and optional "key" keys
            target_language: Target language name
            
        Returns:
            Dict mapping keys to translations
        """
        results: dict[str, str] = {}
        
        for item in items:
            text = item.get("text", "")
            key = item.get("key", text)
            
            try:
                results[key] = self.translate(text, target_language)
            except (TranslationServiceError, TranslationDecodeError):
                results[key] = text
        
        return results
    
    def clear_cache(self) -> None:
        """Clear the translation cache."""
        TranslationCache.clear()
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return TranslationCache.get_stats()
    
    def close(self) -> None:
        """Close manager and release resources."""
        self._close_connection()


_manager: TranslationManager | None = None


def _get_manager() -> TranslationManager:
    """Get or create global translation manager."""
    global _manager
    if _manager is None:
        _manager = TranslationManager()
    return _manager


def ask_ollama_translation(
    text_to_translate: str,
    target_language_name: str
) -> str:
    """Translate text using Ollama (backward compatible).
    
    This function maintains backward compatibility with existing code.
    New code should use TranslationManager directly.
    
    Args:
        text_to_translate: Text to translate
        target_language_name: Target language name
        
    Returns:
        Translated text or original text if translation fails
    """
    try:
        manager = _get_manager()
        return manager.translate(text_to_translate, target_language_name)
    except (TranslationServiceError, TranslationDecodeError):
        return text_to_translate


def get_translation_stats() -> dict[str, Any]:
    """Get translation cache statistics."""
    return TranslationCache.get_stats()


def clear_translation_cache() -> None:
    """Clear the translation cache."""
    TranslationCache.clear()


def translate_many(
    items: list[dict[str, str]],
    target_language: str
) -> dict[str, str]:
    """Translate multiple items (convenience function).
    
    Args:
        items: List of dicts with "text" and optional "key" keys
        target_language: Target language name
        
    Returns:
        Dict mapping keys to translations
    """
    manager = _get_manager()
    return manager.bulk_translate(items, target_language)
