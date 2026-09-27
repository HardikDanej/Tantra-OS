"""
ads_connector.py
================
Draft (PAUSED-only) campaign creation for Google Ads and Meta. This is the
first capability in this project that reaches into a real, live ad
account rather than reading exported/connected performance data — that is
a materially bigger blast radius than the CMS or rendering connectors, and
it exists ONLY because it was explicitly signed off on as such, not as a
default extension of "unwired infrastructure."

Neither platform has a true CMS-style "draft" state independent of a real
account object. The closest safe analog, and the one this module always
uses, is creating the campaign/ad group/adset/ad in PAUSED status:
- Google Ads: `status = PAUSED` on the Campaign, AdGroup, and AdGroupAd.
- Meta: `status = "PAUSED"` on the Campaign, AdSet, and Ad.

PAUSED-only is enforced in code, the same way the CMS connector enforces
draft-only: neither `create_google_ads_draft_campaign` nor
`create_meta_draft_campaign` accepts a status/state parameter. There is no
call shape that produces an ENABLED/ACTIVE campaign from this module. If a
future need for actually launching a campaign shows up, that is a
separate, explicit capability decision — add a distinctly-named function
for it, don't parameterize status on these two.

This module does NOT decide whether it's safe to call — that's
ads_campaign_draft.py's job (the CLI), which refuses to call anything here
unless a Human-In-The-Loop approval_gate.py gate for this specific action
is recorded as "approved". Read that file's docstring before wiring this
into anything.

A PAUSED campaign is still a real object in a live ad account: it consumes
account object quota, can appear in the platform's own UI to anyone with
account access, and — unlike an inert CMS draft — could be manually
switched to ENABLED/ACTIVE by a human working in that UI and start
spending real money. Treat every successful call here as "created
something real that a human must review," not as a harmless no-op.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger("ads_connector")

AdsPlatform = Literal["google_ads", "meta"]


class DraftError(BaseModel):
    reason: str
    detail: str | None = None


class CampaignDraftResult(BaseModel):
    """
    The result of ONE attempt to create ONE PAUSED campaign (+ ad group/adset
    + ad) on ONE platform. `is_paused` is always True here — there is no
    code path in this module that produces False. Kept as an explicit
    field, same reasoning as cms_connector.PublishResult.is_draft: a
    downstream reader should never have to assume PAUSED-only held, the
    result says so.
    """
    # Not typed as AdsPlatform: the unknown-platform error path (see
    # create_draft_campaign's fallback) must be able to construct a clean
    # error result for a platform string that ISN'T one of the two valid
    # literals — that's the whole point of that path. A Literal type here
    # would make pydantic reject exactly the result it's supposed to return,
    # turning "unsupported platform" into an unhandled ValidationError
    # instead of the typed error this module promises never to skip.
    platform: str
    status: Literal["ok", "error"]
    is_paused: bool = True
    campaign_id: str | None = None
    ad_group_id: str | None = None  # Google Ads ad group / Meta adset, either way "the group under the campaign"
    ad_id: str | None = None
    manage_url: str | None = None
    attempted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: DraftError | None = None

    def ok(self) -> bool:
        return self.status == "ok"


def _fail(platform: str, reason: str, detail: str | None = None) -> CampaignDraftResult:
    logger.error("[%s] draft campaign creation failed: %s (%s)", platform, reason, detail)
    return CampaignDraftResult(platform=platform, status="error", error=DraftError(reason=reason, detail=detail))


def _check_budget_ceiling(daily_budget_usd: float, max_daily_budget_usd: float) -> DraftError | None:
    if daily_budget_usd <= 0:
        return DraftError(reason="invalid_budget", detail=f"daily_budget_usd must be > 0, got {daily_budget_usd}")
    if daily_budget_usd > max_daily_budget_usd:
        return DraftError(
            reason="budget_exceeds_safety_ceiling",
            detail=(
                f"daily_budget_usd={daily_budget_usd} exceeds config's safety.max_daily_budget_usd="
                f"{max_daily_budget_usd}. This is a deliberate ceiling, not a bug — raise it in "
                f"config.json if the brief genuinely calls for a bigger daily budget, don't route "
                f"around it."
            ),
        )
    return None


# ---------------------------------------------------------------------------
# Google Ads — google-ads Python client
# https://developers.google.com/google-ads/api/docs/campaigns/overview
# ---------------------------------------------------------------------------

def create_google_ads_draft_campaign(
    config: dict[str, Any],
    *,
    campaign_name: str,
    ad_group_name: str,
    daily_budget_usd: float,
    final_url: str,
    headlines: list[str],
    descriptions: list[str],
) -> CampaignDraftResult:
    """
    Create a PAUSED Search campaign: Budget -> Campaign -> AdGroup ->
    AdGroupAd (Responsive Search Ad). Every mutable status field is
    hard-coded to PAUSED — see module docstring for why that's not a
    parameter.

    `config` is the `google_ads_write` block from config.json: requires
    `developer_token`, `client_id`, `client_secret`, `refresh_token`,
    `customer_id` (the account to write into, no hyphens), and
    `write_access_confirmed: true` (a distinct, explicit opt-in from the
    read-only `google_ads` block's `enabled` — reusing read credentials'
    `enabled` flag as if it authorized writes would silently grant more
    than the user confirmed).
    """
    if not config.get("write_access_confirmed"):
        return _fail(
            "google_ads", "write_access_not_confirmed",
            "google_ads_write.write_access_confirmed is not true in config.json — this is a "
            "separate, explicit opt-in from the read-only puller's config, by design.",
        )

    budget_error = _check_budget_ceiling(daily_budget_usd, config.get("safety", {}).get("max_daily_budget_usd", 20))
    if budget_error:
        return CampaignDraftResult(platform="google_ads", status="error", error=budget_error)

    customer_id = config.get("customer_id", "")
    if not customer_id or str(customer_id).startswith("REPLACE_WITH"):
        return _fail("google_ads", "config_missing", "google_ads_write.customer_id is not configured")

    try:
        from google.ads.googleads.client import GoogleAdsClient
        from google.ads.googleads.errors import GoogleAdsException
    except ImportError as e:
        return _fail("google_ads", "google_ads_not_installed", f"Run: pip install google-ads ({e})")

    try:
        client = GoogleAdsClient.load_from_dict({
            "developer_token": config["developer_token"],
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": config["refresh_token"],
            "login_customer_id": config.get("login_customer_id", ""),
            "use_proto_plus": True,
        })
    except Exception as e:
        return _fail("google_ads", "client_init_failed", str(e)[:500])

    try:
        # 1. Budget
        budget_service = client.get_service("CampaignBudgetService")
        budget_op = client.get_type("CampaignBudgetOperation")
        budget = budget_op.create
        budget.name = f"{campaign_name} Budget {datetime.now(timezone.utc).isoformat()}"
        budget.amount_micros = int(daily_budget_usd * 1_000_000)
        budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        budget_resp = budget_service.mutate_campaign_budgets(customer_id=customer_id, operations=[budget_op])
        budget_resource_name = budget_resp.results[0].resource_name

        # 2. Campaign — status is ALWAYS PAUSED, never a parameter
        campaign_service = client.get_service("CampaignService")
        campaign_op = client.get_type("CampaignOperation")
        campaign = campaign_op.create
        campaign.name = campaign_name
        campaign.status = client.enums.CampaignStatusEnum.PAUSED
        campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
        campaign.campaign_budget = budget_resource_name
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = True
        campaign.network_settings.target_content_network = False
        campaign_resp = campaign_service.mutate_campaigns(customer_id=customer_id, operations=[campaign_op])
        campaign_resource_name = campaign_resp.results[0].resource_name
        campaign_id = campaign_resource_name.split("/")[-1]

        # 3. Ad group — status is ALWAYS PAUSED
        ad_group_service = client.get_service("AdGroupService")
        ad_group_op = client.get_type("AdGroupOperation")
        ad_group = ad_group_op.create
        ad_group.name = ad_group_name
        ad_group.campaign = campaign_resource_name
        ad_group.status = client.enums.AdGroupStatusEnum.PAUSED
        ad_group_resp = ad_group_service.mutate_ad_groups(customer_id=customer_id, operations=[ad_group_op])
        ad_group_resource_name = ad_group_resp.results[0].resource_name
        ad_group_id = ad_group_resource_name.split("/")[-1]

        # 4. Responsive Search Ad — status is ALWAYS PAUSED
        ad_group_ad_service = client.get_service("AdGroupAdService")
        ad_group_ad_op = client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_group_ad_op.create
        ad_group_ad.ad_group = ad_group_resource_name
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.PAUSED
        rsa = ad_group_ad.ad.responsive_search_ad
        for h in headlines[:15]:
            asset = client.get_type("AdTextAsset")
            asset.text = h[:30]
            rsa.headlines.append(asset)
        for d in descriptions[:4]:
            asset = client.get_type("AdTextAsset")
            asset.text = d[:90]
            rsa.descriptions.append(asset)
        ad_group_ad.ad.final_urls.append(final_url)
        ad_resp = ad_group_ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=[ad_group_ad_op])
        ad_resource_name = ad_resp.results[0].resource_name
        ad_id = ad_resource_name.split("~")[-1] if "~" in ad_resource_name else ad_resource_name.split("/")[-1]

    except GoogleAdsException as e:
        details = "; ".join(err.message for err in e.failure.errors) if e.failure else str(e)
        return _fail("google_ads", "google_ads_api_error", details[:500])
    except Exception as e:
        return _fail("google_ads", "request_failed", str(e)[:500])

    return CampaignDraftResult(
        platform="google_ads",
        status="ok",
        is_paused=True,
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        ad_id=ad_id,
        manage_url=f"https://ads.google.com/aw/campaigns?ocid={customer_id}",
    )


# ---------------------------------------------------------------------------
# Meta — Marketing API (Graph API), direct requests (same pattern the
# existing ad_data_pull.py pull_meta() uses for reads)
# https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group
# ---------------------------------------------------------------------------

def create_meta_draft_campaign(
    config: dict[str, Any],
    *,
    campaign_name: str,
    adset_name: str,
    daily_budget_usd: float,
    objective: str,
    optimization_goal: str,
    billing_event: str,
    link: str,
    message: str,
    headline: str,
    description: str = "",
    page_id: str = "",
    targeting: dict[str, Any] | None = None,
    timeout: int = 30,
) -> CampaignDraftResult:
    """
    Create a PAUSED campaign -> adset -> ad (link ad, no image/video asset
    required). Every mutable status field is hard-coded to `"PAUSED"` — see
    module docstring for why that's not a parameter.

    `config` is the `meta_write` block from config.json: requires
    `access_token`, `ad_account_id`, `page_id` (unless passed per-call), and
    `write_access_confirmed: true` (same reasoning as Google Ads — a
    separate, explicit opt-in from the read-only puller's config).

    `targeting` is Meta's raw targeting spec (e.g. `{"geo_locations":
    {"countries": ["US", "CA"]}}`) and defaults to `{"geo_locations":
    {"countries": ["US"]}}` if not given — this is a real, load-bearing
    default, not a placeholder, so don't skip naming the actual target
    market in the brief just because a fallback exists.
    """
    if not config.get("write_access_confirmed"):
        return _fail(
            "meta", "write_access_not_confirmed",
            "meta_write.write_access_confirmed is not true in config.json — this is a separate, "
            "explicit opt-in from the read-only puller's config, by design.",
        )

    budget_error = _check_budget_ceiling(daily_budget_usd, config.get("safety", {}).get("max_daily_budget_usd", 20))
    if budget_error:
        return CampaignDraftResult(platform="meta", status="error", error=budget_error)

    access_token = config.get("access_token", "")
    ad_account_id = config.get("ad_account_id", "")
    page_id = page_id or config.get("page_id", "")

    if not access_token or str(access_token).startswith("REPLACE_WITH"):
        return _fail("meta", "config_missing", "meta_write.access_token is not configured")
    if not ad_account_id or str(ad_account_id).startswith("REPLACE_WITH"):
        return _fail("meta", "config_missing", "meta_write.ad_account_id is not configured")
    if not page_id or str(page_id).startswith("REPLACE_WITH"):
        return _fail("meta", "config_missing", "meta_write.page_id is not configured (and no page_id was passed)")

    base = f"https://graph.facebook.com/v19.0/act_{ad_account_id}"

    def _post(path: str, payload: dict[str, Any]) -> tuple[dict | None, DraftError | None]:
        try:
            r = requests.post(f"{base}/{path}", data={**payload, "access_token": access_token}, timeout=timeout)
        except requests.RequestException as e:
            return None, DraftError(reason="request_failed", detail=str(e)[:500])
        if r.status_code not in (200, 201):
            detail = r.text[:500]
            try:
                body = r.json()
                detail = body.get("error", {}).get("message", detail)
            except ValueError:
                pass
            return None, DraftError(reason=f"http_{r.status_code}", detail=detail)
        try:
            return r.json(), None
        except ValueError as e:
            return None, DraftError(reason="invalid_response_json", detail=str(e)[:500])

    # 1. Campaign — status is ALWAYS "PAUSED"
    campaign_body, err = _post("campaigns", {
        "name": campaign_name,
        "objective": objective,
        "status": "PAUSED",
        "special_ad_categories": json.dumps([]),
    })
    if err:
        return CampaignDraftResult(platform="meta", status="error", error=err)
    campaign_id = campaign_body["id"]

    # 2. AdSet — status is ALWAYS "PAUSED"
    adset_body, err = _post("adsets", {
        "name": adset_name,
        "campaign_id": campaign_id,
        "daily_budget": int(daily_budget_usd * 100),  # Meta budgets are in the account currency's smallest unit (cents for USD)
        "billing_event": billing_event,
        "optimization_goal": optimization_goal,
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "targeting": json.dumps(targeting or {"geo_locations": {"countries": ["US"]}}),
        "status": "PAUSED",
    })
    if err:
        return CampaignDraftResult(platform="meta", status="error", campaign_id=campaign_id, error=err)
    adset_id = adset_body["id"]

    # 3. Ad creative — a plain link ad, no image/video asset required
    creative_body, err = _post("adcreatives", {
        "name": f"{campaign_name} Creative",
        "object_story_spec": json.dumps({
            "page_id": page_id,
            "link_data": {
                "link": link,
                "message": message,
                "name": headline,
                "description": description,
            },
        }),
    })
    if err:
        return CampaignDraftResult(platform="meta", status="error", campaign_id=campaign_id, ad_group_id=adset_id, error=err)
    creative_id = creative_body["id"]

    # 4. Ad — status is ALWAYS "PAUSED"
    ad_body, err = _post("ads", {
        "name": f"{campaign_name} Ad",
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": "PAUSED",
    })
    if err:
        return CampaignDraftResult(platform="meta", status="error", campaign_id=campaign_id, ad_group_id=adset_id, error=err)
    ad_id = ad_body["id"]

    return CampaignDraftResult(
        platform="meta",
        status="ok",
        is_paused=True,
        campaign_id=campaign_id,
        ad_group_id=adset_id,
        ad_id=ad_id,
        manage_url=f"https://business.facebook.com/adsmanager/manage/campaigns?act={ad_account_id}",
    )


def create_draft_campaign(platform: str, config: dict[str, Any], **kwargs: Any) -> CampaignDraftResult:
    """Dispatch to the right connector by platform name. See ads_campaign_draft.py for the CLI."""
    if platform == "google_ads":
        return create_google_ads_draft_campaign(config, **kwargs)
    if platform == "meta":
        return create_meta_draft_campaign(config, **kwargs)
    return _fail(platform, "unknown_platform", f"no connector for {platform!r}")
