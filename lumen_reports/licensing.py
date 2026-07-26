"""Entitlement checks for Lumen Reports.

Frappe Cloud writes a per-subscription secret into the customer's site config as
`sk_lumen_reports` (see press: MarketplaceAppSubscription.set_keys_in_site_config)
and exposes a guest API to validate it. We check that, cache the answer, and fail
*open* on network trouble — a Frappe Cloud outage must never take a customer's
dashboards down.

Deliberately not a DRM system. Anyone holding the source can remove this file. The
point is that unlicensed use is visible and deliberate rather than accidental.
"""

import frappe
import requests
from frappe import _

APP_NAME = "lumen_reports"
CONFIG_KEY = f"sk_{APP_NAME}"

FRAPPE_CLOUD_API = (
	"https://frappecloud.com/api/method/press.api.developer.marketplace.get_subscription_info"
)

CACHE_KEY = "lumen_reports:license"
CACHE_TTL = 6 * 60 * 60  # re-check a few times a day, not every request
# if Frappe Cloud is unreachable, keep trusting the last good answer this long
GRACE_SECONDS = 7 * 24 * 60 * 60

STATUS_LICENSED = "licensed"
STATUS_EXPIRED = "expired"  # known subscription, no longer active
STATUS_UNLICENSED = "unlicensed"  # no subscription key on this site at all
STATUS_UNKNOWN = "unknown"  # couldn't reach Frappe Cloud and no cached answer


def _secret_key():
	return frappe.conf.get(CONFIG_KEY)


def _cache_set(key, value, ttl):
	"""Write to the cache and drop Frappe's per-request copy.

	`set_value` with an expiry never populates frappe.local.cache, but `get_value`
	reads that dict *first* — so without this a second read inside the same request
	serves the answer from before the refresh.
	"""
	cache = frappe.cache()
	cache.set_value(key, value, expires_in_sec=ttl)
	frappe.local.cache.pop(cache.make_key(key), None)


def _fetch(secret_key):
	"""Ask Frappe Cloud about this site's subscription. Raises on any failure."""
	response = requests.post(FRAPPE_CLOUD_API, json={"secret_key": secret_key}, timeout=10)
	response.raise_for_status()
	return response.json().get("message") or {}


def get_status(force=False) -> dict:
	"""{status, plan, site, checked_on} — cached, never raises."""
	if not force:
		cached = frappe.cache().get_value(CACHE_KEY)
		if cached:
			return cached

	secret_key = _secret_key()
	if not secret_key:
		# self-hosted, or a copy taken from the repository
		result = {"status": STATUS_UNLICENSED, "plan": None, "site": None}
		_cache_set(CACHE_KEY, result, CACHE_TTL)
		return result

	try:
		info = _fetch(secret_key)
		result = {
			"status": STATUS_LICENSED if info.get("enabled") else STATUS_EXPIRED,
			"plan": info.get("plan"),
			"site": info.get("site"),
			"checked_on": frappe.utils.now(),
		}
		_cache_set(CACHE_KEY, result, CACHE_TTL)
		# a durable copy so an outage can fall back to it
		_cache_set(f"{CACHE_KEY}:last_good", result, GRACE_SECONDS)
		return result
	except Exception:
		# never let a network problem break the app
		last_good = frappe.cache().get_value(f"{CACHE_KEY}:last_good")
		if last_good:
			return last_good
		return {"status": STATUS_UNKNOWN, "plan": None, "site": None}


def is_licensed() -> bool:
	"""True unless we positively know the site is not entitled.

	`unknown` counts as licensed: we could not reach Frappe Cloud, and punishing a
	paying customer for our own connectivity problem is worse than the alternative.
	"""
	return get_status().get("status") in (STATUS_LICENSED, STATUS_UNKNOWN)


def notice() -> str | None:
	"""A short line for the UI banner, or None when nothing needs saying."""
	# a developer's own bench shouldn't nag on every page
	if frappe.conf.get("developer_mode"):
		return None

	status = get_status().get("status")
	if status == STATUS_EXPIRED:
		return _(
			"Your Lumen Reports subscription is no longer active. Dashboards stay "
			"visible, but you can't create or edit them until it's renewed."
		)
	if status == STATUS_UNLICENSED:
		return _(
			"This copy of Lumen Reports has no licence. It's free to evaluate — "
			"contact hello@lumen-solutions.co for a licence to use it in production."
		)
	return None


def require_license():
	"""Guard for write paths. Read paths stay open so a lapsed customer keeps
	seeing the dashboards they already built."""
	if frappe.conf.get("developer_mode"):
		return
	if get_status().get("status") == STATUS_EXPIRED:
		frappe.throw(
			_("Your Lumen Reports subscription is no longer active. Renew it to make changes."),
			title=_("Subscription inactive"),
		)


@frappe.whitelist()
def get_license_notice():
	"""Whitelisted for the UI banner. Returns no secrets — only a status word."""
	return {"status": get_status().get("status"), "notice": notice()}
