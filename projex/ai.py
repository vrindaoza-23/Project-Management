# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Provider-agnostic AI layer.

All AI features degrade gracefully: with no provider key configured, every
helper reports ``enabled = False`` and the SPA hides the AI surfaces. A key is
read from site config (never hardcoded, never committed):

    bench --site <site> set-config projex_ai_provider openai
    bench --site <site> set-config projex_ai_api_key sk-...

To add a real provider, implement ``_complete()`` for that vendor. v1 ships the
abstraction + safe heuristic fallbacks so the product works with or without AI.
"""

import frappe


def is_ai_enabled() -> bool:
	conf = frappe.conf
	return bool(conf.get("projex_ai_provider") and conf.get("projex_ai_api_key"))


def provider_name() -> str | None:
	return frappe.conf.get("projex_ai_provider")


def _complete(prompt: str, **kw) -> str | None:
	"""Dispatch to the configured provider. Returns None if AI is disabled.

	Intentionally not wired to a network call in v1 — the provider switch is
	here so adding a vendor is a localized change, not a refactor.
	"""
	if not is_ai_enabled():
		return None
	# provider = provider_name()
	# if provider == "openai": return _openai_complete(prompt, **kw)
	# if provider == "anthropic": return _anthropic_complete(prompt, **kw)
	raise NotImplementedError(
		f"AI provider '{provider_name()}' is configured but not implemented yet"
	)


def result(enabled: bool, **payload):
	return {"enabled": enabled, **payload}
