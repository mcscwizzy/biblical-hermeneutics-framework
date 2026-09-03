"""Orchestrate generation, validation, cache fallback, and offline rendering."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Mapping

from .cache import MemoryPresentationCache, PresentationCache, presentation_cache_key
from .coalescing import RequestCoalescer
from .fallback import deterministic_presentation
from .metrics import PresentationMetrics
from .models import (
    PRESENTATION_SCHEMA_VERSION,
    EvidenceBundle,
    GeneratedFrom,
    PresentationPacket,
)
from .providers import (
    PRESENTATION_PROMPT_VERSION,
    PresentationProvider,
    PresentationResponseParseError,
)
from .provider_gate import ProviderRequestGate
from .ranking import RankedEvidence, rank_evidence
from .validation import validate_presentation_packet


LOGGER = logging.getLogger(__name__)


def _failure_diagnostic(stage: str, exc: BaseException) -> str:
    """Describe a failure without retaining arbitrary exception payload text."""

    return f"{stage}: {type(exc).__name__}"


def _diagnostic_log_summary(
    diagnostics: list[str],
    *,
    maximum_items: int = 4,
    maximum_item_characters: int = 240,
) -> str:
    """Compact BHF-authored diagnostics and neutralize control-character noise."""

    visible = []
    for diagnostic in diagnostics[:maximum_items]:
        compact = " ".join(str(diagnostic).split())
        if len(compact) > maximum_item_characters:
            compact = f"{compact[:maximum_item_characters - 3]}..."
        visible.append(compact)
    omitted = len(diagnostics) - len(visible)
    if omitted:
        visible.append(f"... (+{omitted} more)")
    return "; ".join(visible)


def _provider_generation_profile(provider: PresentationProvider | None) -> str | None:
    """Return a credential-free cache identity, preserving generic providers."""

    if provider is None:
        return None
    configured = str(getattr(provider, "generation_profile", "") or "").strip()
    return configured or str(provider.model)


def _provider_log_metadata(
    provider: PresentationProvider,
    bundle: EvidenceBundle,
) -> dict[str, str]:
    return {
        "evidence_hash_prefix": bundle.evidence_hash[:12],
        "model": str(getattr(provider, "model", "") or ""),
        "provider": str(
            getattr(provider, "adapter_name", "")
            or type(provider).__name__
        ),
        "reference": bundle.passage_ref,
    }


def _is_rate_limit_error(exc: BaseException) -> bool:
    name = type(exc).__name__.casefold()
    status_code = getattr(exc, "status_code", None)
    return "ratelimit" in name or "rate_limit" in name or status_code == 429


@dataclass(frozen=True)
class PresentationResult:
    packet: PresentationPacket
    mode: str
    diagnostics: tuple[str, ...] = ()

    def to_dict(self, *, include_diagnostics: bool = False) -> dict[str, Any]:
        """Serialize reader-safe output, with internal failures only by opt-in."""

        value = self.packet.to_dict()
        value["presentation_mode"] = self.mode
        if include_diagnostics and self.diagnostics:
            value["diagnostics"] = list(self.diagnostics)
        return value


class PresentationEngine:
    """Treat generated prose as disposable output over permanent evidence."""

    def __init__(
        self,
        *,
        provider: PresentationProvider | None = None,
        cache: PresentationCache | None = None,
        bundled_packets: Mapping[str, Any] | None = None,
        prompt_version: str = PRESENTATION_PROMPT_VERSION,
        maximum_cards: int = 3,
        candidate_limit: int = 8,
        maximum_concurrent_provider_requests: int | None = None,
    ) -> None:
        self.provider = provider
        self.cache = cache if cache is not None else MemoryPresentationCache()
        self.bundled_packets = dict(bundled_packets or {})
        self.prompt_version = prompt_version
        self.maximum_cards = max(0, int(maximum_cards))
        self.candidate_limit = max(1, int(candidate_limit))
        self._provider_requests = (
            ProviderRequestGate(maximum_concurrent_provider_requests)
            if maximum_concurrent_provider_requests is not None
            else None
        )
        self.metrics = PresentationMetrics()
        self._generation_requests = RequestCoalescer[PresentationResult]()

    def present(self, bundle: EvidenceBundle) -> PresentationResult:
        return self.present_with_provider(bundle, self.provider)

    def present_with_provider(
        self,
        bundle: EvidenceBundle,
        provider: PresentationProvider | None,
        *,
        generation_profile: str | None = None,
    ) -> PresentationResult:
        """Generate with a request-scoped provider on the shared guarded engine."""

        started = time.perf_counter()
        try:
            result = self._present(
                bundle,
                provider,
                generation_profile=generation_profile,
            )
        except BaseException:
            self.metrics.record_unhandled_failure(time.perf_counter() - started)
            raise
        self.metrics.record_result(result.mode, time.perf_counter() - started)
        return result

    def present_local(self, bundle: EvidenceBundle) -> PresentationResult:
        """Return cache, bundled, or deterministic output without a provider call."""

        started = time.perf_counter()
        try:
            result = self._present_local(bundle)
        except BaseException:
            self.metrics.record_unhandled_failure(time.perf_counter() - started)
            raise
        self.metrics.record_result(result.mode, time.perf_counter() - started)
        return result

    @property
    def enhancement_available(self) -> bool:
        return self.provider is not None

    def _present(
        self,
        bundle: EvidenceBundle,
        provider: PresentationProvider | None,
        *,
        generation_profile: str | None,
    ) -> PresentationResult:
        ranked = rank_evidence(bundle, limit=self.candidate_limit)
        profile = generation_profile or _provider_generation_profile(provider)
        cache_key = presentation_cache_key(
            bundle,
            prompt_version=self.prompt_version,
            generation_profile=profile,
        )
        bundle_key = presentation_cache_key(bundle, prompt_version=self.prompt_version)
        diagnostics: list[str] = []

        local = self._read_reusable(bundle, cache_key, bundle_key, diagnostics)
        if local is not None:
            return local
        if provider is None or not ranked:
            return self._deterministic(bundle, ranked, diagnostics)
        return self._generation_requests.run(
            cache_key,
            lambda: self._generate_after_recheck(
                bundle,
                ranked,
                cache_key,
                bundle_key,
                diagnostics,
                provider,
            ),
        )

    def _present_local(self, bundle: EvidenceBundle) -> PresentationResult:
        ranked = rank_evidence(bundle, limit=self.candidate_limit)
        cache_key = presentation_cache_key(
            bundle,
            prompt_version=self.prompt_version,
            generation_profile=_provider_generation_profile(self.provider),
        )
        bundle_key = presentation_cache_key(bundle, prompt_version=self.prompt_version)
        diagnostics: list[str] = []
        reusable = self._read_reusable(bundle, cache_key, bundle_key, diagnostics)
        if reusable is not None:
            return reusable
        return self._deterministic(bundle, ranked, diagnostics)

    def _generate_after_recheck(
        self,
        bundle: EvidenceBundle,
        ranked: list[RankedEvidence],
        cache_key: str,
        bundle_key: str,
        diagnostics: list[str],
        provider: PresentationProvider,
    ) -> PresentationResult:
        reusable = self._read_reusable(bundle, cache_key, bundle_key, diagnostics)
        if reusable is not None:
            return reusable

        if provider is not None and ranked:
            expected = GeneratedFrom(
                evidence_hash=bundle.evidence_hash,
                evidence_bundle_version=bundle.version,
                presentation_schema_version=PRESENTATION_SCHEMA_VERSION,
                prompt_version=self.prompt_version,
                model=provider.model,
            )
            provider_slot_acquired = (
                self._provider_requests is None
                or self._provider_requests.try_acquire()
            )
            if not provider_slot_acquired:
                self.metrics.record_event("provider_saturation")
                diagnostics.append(
                    "provider capacity unavailable: concurrent request limit reached"
                )
                LOGGER.warning(
                    "presentation provider capacity unavailable; deterministic fallback used",
                    extra={
                        "event": "presentation_provider_request",
                        **_provider_log_metadata(provider, bundle),
                    },
                )
            else:
                self.metrics.record_event("provider_attempts")
                try:
                    LOGGER.info(
                        "presentation provider request started",
                        extra={
                            "event": "presentation_provider_request",
                            **_provider_log_metadata(provider, bundle),
                        },
                    )
                    generated = provider.generate(bundle, ranked, expected)
                    generated_value = (
                        generated.to_dict() if hasattr(generated, "to_dict") else generated
                    )
                    validation = validate_presentation_packet(
                        generated_value,
                        bundle,
                        maximum_cards=self.maximum_cards,
                        expected_prompt_version=self.prompt_version,
                        expected_model=provider.model,
                    )
                    generated_card_count = (
                        len(generated_value.get("cards"))
                        if isinstance(generated_value, Mapping)
                        and isinstance(generated_value.get("cards"), list)
                        else 0
                    )
                    accepted_card_count = len(validation.accepted_cards)
                    rejected_card_count = len(
                        [result for result in validation.card_results if not result.valid]
                    )
                    for index, card_result in enumerate(validation.card_results):
                        if card_result.valid:
                            continue
                        reason = (
                            card_result.reason_codes[0]
                            if card_result.reason_codes
                            else "MALFORMED_CARD"
                        )
                        LOGGER.warning(
                            "presentation card rejected",
                            extra={
                                "event": "presentation_card_rejected",
                                "card_index": index,
                                "reason": reason,
                                **_provider_log_metadata(provider, bundle),
                            },
                        )
                    if validation.packet is not None and accepted_card_count:
                        diagnostics.extend(
                            f"validation rejection: {error}"
                            for error in validation.errors
                        )
                        LOGGER.info(
                            "presentation generation completed",
                            extra={
                                "event": "presentation_generation_completed",
                                "generated_cards": generated_card_count,
                                "accepted_cards": accepted_card_count,
                                "rejected_cards": rejected_card_count,
                                **_provider_log_metadata(provider, bundle),
                            },
                        )
                        try:
                            self.cache.put(cache_key, validation.packet.to_dict())
                        except Exception as exc:  # noqa: BLE001 - cache is optional
                            self.metrics.record_event("cache_write_failures")
                            diagnostics.append(
                                _failure_diagnostic("cache write failure", exc)
                            )
                            LOGGER.warning(
                                "presentation cache write failed: %s",
                                diagnostics[-1],
                            )
                        return PresentationResult(
                            validation.packet,
                            "generated",
                            tuple(diagnostics),
                        )
                    self.metrics.record_event("provider_rejections")
                    if validation.packet is not None and not accepted_card_count:
                        diagnostics.append("provider returned no valid cards")
                    diagnostics.extend(
                        f"validation rejection: {error}"
                        for error in validation.errors
                    )
                    LOGGER.warning(
                        "presentation provider output failed validation; deterministic fallback used",
                        extra={
                            "event": "presentation_validation",
                            "validation_error_count": len(validation.errors),
                            "generated_cards": generated_card_count,
                            "accepted_cards": accepted_card_count,
                            "rejected_cards": rejected_card_count,
                            "packet_valid": validation.packet_valid,
                            **_provider_log_metadata(provider, bundle),
                        },
                    )
                except PresentationResponseParseError as exc:
                    self.metrics.record_event("provider_parse_failures")
                    diagnostics.append(
                        _failure_diagnostic("provider response parse failure", exc)
                    )
                    LOGGER.warning(
                        "presentation provider returned malformed structured output; deterministic fallback used",
                        extra={
                            "event": "presentation_provider_parse",
                            "exception_class": type(exc).__name__,
                            **_provider_log_metadata(provider, bundle),
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    self.metrics.record_event("provider_failures")
                    diagnostics.append(_failure_diagnostic("provider failure", exc))
                    message = (
                        "presentation provider rate limited; deterministic fallback used"
                        if _is_rate_limit_error(exc)
                        else "presentation provider request failed; deterministic fallback used"
                    )
                    LOGGER.warning(
                        message,
                        extra={
                            "event": "presentation_provider_request",
                            "exception_class": type(exc).__name__,
                            **_provider_log_metadata(provider, bundle),
                        },
                    )
                finally:
                    if self._provider_requests is not None:
                        self._provider_requests.release()
                LOGGER.warning(
                    "presentation generation rejected; falling back (%d): %s",
                    len(diagnostics),
                    _diagnostic_log_summary(diagnostics),
                )

        return self._deterministic(bundle, ranked, diagnostics)

    def _read_reusable(
        self,
        bundle: EvidenceBundle,
        cache_key: str,
        bundle_key: str,
        diagnostics: list[str],
    ) -> PresentationResult | None:
        cached_result = self._read_cached(bundle, cache_key, diagnostics)
        if cached_result is not None:
            return cached_result
        bundled = self.bundled_packets.get(bundle_key)
        if bundled is not None:
            validation = validate_presentation_packet(
                bundled,
                bundle,
                maximum_cards=self.maximum_cards,
            )
            if validation.valid and validation.packet is not None:
                return PresentationResult(validation.packet, "bundled", tuple(diagnostics))
            self.metrics.record_event("bundle_rejections")
            diagnostics.extend(f"bundled: {error}" for error in validation.errors)
        return None

    def _deterministic(
        self,
        bundle: EvidenceBundle,
        ranked: list[RankedEvidence],
        diagnostics: list[str],
    ) -> PresentationResult:
        if diagnostics:
            LOGGER.warning(
                "presentation deterministic fallback selected",
                extra={
                    "event": "presentation_fallback",
                    "diagnostic_count": len(diagnostics),
                    "evidence_hash_prefix": bundle.evidence_hash[:12],
                    "reference": bundle.passage_ref,
                },
            )
        fallback = deterministic_presentation(
            bundle,
            ranked,
            maximum_cards=self.maximum_cards,
        )
        validation = validate_presentation_packet(
            fallback.to_dict(),
            bundle,
            maximum_cards=self.maximum_cards,
        )
        if not validation.valid or validation.packet is None:
            # This indicates a programming error, but returning an empty valid
            # packet still keeps Bible reading available.
            diagnostics.extend(f"deterministic: {error}" for error in validation.errors)
            empty = deterministic_presentation(bundle, [], maximum_cards=0)
            return PresentationResult(empty, "deterministic_fallback", tuple(diagnostics))
        return PresentationResult(validation.packet, "deterministic_fallback", tuple(diagnostics))

    def _read_cached(
        self,
        bundle: EvidenceBundle,
        cache_key: str,
        diagnostics: list[str],
    ) -> PresentationResult | None:
        try:
            cached = self.cache.get(cache_key)
        except Exception as exc:  # noqa: BLE001 - cache is optional
            self.metrics.record_event("cache_read_failures")
            diagnostics.append(_failure_diagnostic("cache read failure", exc))
            LOGGER.warning("presentation cache read failed: %s", diagnostics[-1])
            return None
        if cached is None:
            return None

        validation = validate_presentation_packet(
            cached,
            bundle,
            maximum_cards=self.maximum_cards,
            expected_prompt_version=self.prompt_version,
        )
        if validation.packet is not None and validation.packet.cards:
            return PresentationResult(validation.packet, "cached", tuple(diagnostics))

        diagnostics.extend(f"cached: {error}" for error in validation.errors)
        discard = getattr(self.cache, "discard", None)
        if callable(discard):
            try:
                discard(cache_key)
            except Exception as exc:  # noqa: BLE001 - cache is optional
                self.metrics.record_event("cache_discard_failures")
                diagnostics.append(_failure_diagnostic("cache discard failure", exc))
        return None

    def diagnostics(self) -> dict[str, Any]:
        result = self.metrics.snapshot()
        result["coalescing"] = self._generation_requests.diagnostics()
        result["provider_gate"] = (
            self._provider_requests.diagnostics()
            if self._provider_requests is not None
            else {"enabled": False}
        )
        return result
