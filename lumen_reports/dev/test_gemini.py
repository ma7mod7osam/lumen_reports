"""Gemini connection checks.

`ping` and `models` need a key on the site and talk to Google. `chain` needs
neither: it drives the retry and model-fallback logic with a stubbed API, which
is the only way to test an overload without waiting for a real one.
"""

import json
import time

import frappe
import requests

from lumen_reports import ai


def _try(model, key, attempts=3):
	out = []
	for i in range(attempts):
		started = time.time()
		try:
			response = requests.post(
				ai.GEMINI_URL.format(model=model),
				headers={"x-goog-api-key": key},
				json={
					"contents": [{"role": "user", "parts": [{"text": 'Reply {"ok": true}'}]}],
					"generationConfig": {"responseMimeType": "application/json"},
				},
				timeout=30,
			)
			detail = ""
			if response.status_code != 200:
				try:
					detail = str(response.json().get("error", {}).get("message", ""))[:120]
				except Exception:
					detail = response.text[:120]
			out.append(
				{
					"attempt": i + 1,
					"status": response.status_code,
					"seconds": round(time.time() - started, 1),
					"detail": detail,
				}
			)
		except Exception as e:
			out.append({"attempt": i + 1, "error": str(e)[:120]})
		if out[-1].get("status") == 200:
			break
		time.sleep(2)
	return out


def whose_key():
	"""Which settings row holds a key, without ever printing one."""
	rows = []
	for name in frappe.get_all("Lumen AI Settings", pluck="name"):
		doc = frappe.get_doc("Lumen AI Settings", name)
		try:
			key = doc.get_password("gemini_api_key", raise_exception=False)
			state = "set" if key else "empty"
		except Exception as e:
			state = f"error: {type(e).__name__}"
		rows.append({"user": doc.user, "model": doc.model, "key": state})
	site = frappe.get_cached_doc("Lumen AI Site Settings")
	try:
		site_key = site.get_password("gemini_api_key", raise_exception=False)
		site_state = "set" if site_key else "empty"
	except Exception as e:
		site_state = f"error: {type(e).__name__}"
	print(
		json.dumps(
			{
				"session_user": frappe.session.user,
				"personal": rows,
				"site": {"key": site_state, "model": site.model},
			},
			indent=1,
		)
	)


def ping(as_user: str | None = None):
	if as_user:
		frappe.set_user(as_user)
	key, model, source = ai._resolve_key()
	if not key:
		print(json.dumps({"configured": False, "session_user": frappe.session.user}))
		return
	result = {
		"source": source,
		"configured_model": model,
		"fallback_model": ai.FALLBACK_MODEL,
		model: _try(model, key),
		ai.FALLBACK_MODEL: _try(ai.FALLBACK_MODEL, key, attempts=1),
	}
	print(json.dumps(result, indent=1))


def models():
	"""What this key is actually allowed to call."""
	key, _model, _source = ai._resolve_key()
	if not key:
		print(json.dumps({"configured": False}))
		return
	response = requests.get(
		ai.GEMINI_MODELS_URL, headers={"x-goog-api-key": key}, params={"pageSize": 100}, timeout=30
	)
	names = [
		m.get("name", "").replace("models/", "")
		for m in (response.json().get("models") or [])
		if "generateContent" in (m.get("supportedGenerationMethods") or [])
	]
	print(json.dumps({"status": response.status_code, "count": len(names), "models": names}, indent=1))


# ------------------------------------------------------------------ chain


def _drive(failures: dict, chosen="gemini-flash-latest"):
	"""Run _generate against a stubbed API. `failures` maps a model to the
	exception class it should raise, anything else answers normally."""
	calls, slept = [], []
	real_once, real_sleep = ai._generate_once, ai.time.sleep

	def fake_once(prompt, key, model):
		calls.append(model)
		problem = failures.get(model)
		if problem:
			raise problem("stubbed")
		return {"model_used": model}

	ai._generate_once = fake_once
	ai.time.sleep = lambda s: slept.append(s)
	try:
		result = ai._generate("prompt", "key", chosen)
		error = None
	except Exception as e:
		result = None
		error = frappe.utils.strip_html(str(e))[:150].strip()
	finally:
		ai._generate_once = real_once
		ai.time.sleep = real_sleep
		frappe.clear_last_message()
	return {"calls": calls, "waited": round(sum(slept), 1), "result": result, "error": error}


def chain():
	"""What happens when Google is overloaded, out of quota, or picky."""
	busy, limited, missing = ai._Busy, ai._RateLimited, ai._NoSuchModel
	primary = "gemini-flash-latest"
	alternates = [m for m in ai.ALTERNATE_MODELS if m != primary]

	cases = {}

	# nothing wrong: one call, no waiting
	cases["healthy"] = _drive({})

	# the chosen model is overloaded: retried, then handed to the next model
	cases["primary_overloaded"] = _drive({primary: busy})

	# everything is overloaded: a sentence a person can act on, not a 503
	cases["all_overloaded"] = _drive({m: busy for m in [primary] + alternates})

	# quota is per model and per day, so it moves on without waiting
	cases["primary_quota_gone"] = _drive({primary: limited})
	cases["all_quota_gone"] = _drive({m: limited for m in [primary] + alternates})

	# a model this key cannot call is a settings mistake, not a capacity one
	cases["chosen_model_unknown"] = _drive({primary: missing})
	# but an alternate that is not available is simply skipped
	cases["alternate_unknown"] = _drive({primary: busy, alternates[0]: missing})

	ok = {
		"healthy": cases["healthy"]["result"] == {"model_used": primary} and cases["healthy"]["calls"] == [primary],
		"primary_retried_then_switched": cases["primary_overloaded"]["calls"][:3] == [primary] * 3
		and cases["primary_overloaded"]["result"] == {"model_used": alternates[0]},
		"overload_ends_in_advice": "busy right now" in (cases["all_overloaded"]["error"] or ""),
		"overload_wait_stays_short": cases["all_overloaded"]["waited"] <= 12,
		"quota_switches_without_waiting": cases["primary_quota_gone"]["waited"] == 0
		and cases["primary_quota_gone"]["result"] == {"model_used": alternates[0]},
		"quota_ends_in_advice": "used up for today" in (cases["all_quota_gone"]["error"] or ""),
		"unknown_chosen_model_is_named": "cannot use" in (cases["chosen_model_unknown"]["error"] or ""),
		"unknown_alternate_is_skipped": cases["alternate_unknown"]["result"] == {"model_used": alternates[1]},
		"every_model_tried_once": cases["all_overloaded"]["calls"].count(alternates[-1]) == 1,
	}
	print(json.dumps({"cases": cases, "ok": ok, "all_ok": all(ok.values())}, indent=1))
