from __future__ import annotations

from datetime import datetime, timedelta
from html import unescape
import re
import ssl
import urllib.parse
import urllib.request
from typing import Any, Optional

import config

PRIORITY_ORDER = {"critical": 4, "high": 3, "moderate": 2, "low": 1}


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _html_to_text(html: str) -> str:
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", html or "")
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?is)</(?:p|div|li|tr|td|th|h\d)>", "\n", cleaned)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"[ \t\r\f\v]+", " ", cleaned)
    cleaned = re.sub(r"\n\s+", "\n", cleaned)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    return cleaned.strip()


def _extract_first(pattern: str, text: str, *, flags: int = 0) -> Optional[str]:
    match = re.search(pattern, text or "", flags)
    if not match:
        return None
    return _clean_text(match.group(1)) or None


def _http_get_text(url: str) -> str:
    timeout = int(getattr(config, "MIMIC_RSI_HTTP_TIMEOUT_SECONDS", 15) or 15)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
        },
    )
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def scrape_rsi_profile_summary(profile_url: str) -> dict[str, Any]:
    """Best-effort public RSI profile scrape, mirroring the MIMIC scraper fields we need.

    This does not write to MIMIC. It only extracts visible profile metadata so OnboardingBot
    can compare the applicant's current main org against MIMIC org/watchlist records.
    """
    html = _http_get_text(profile_url)
    text = _html_to_text(html)

    if "CITIZEN DOSSIER" not in text.upper():
        raise RuntimeError("RSI did not return a public Citizen Dossier.")

    parsed = urllib.parse.urlparse(profile_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    handle_from_url = path_parts[-1] if path_parts else None
    handle_from_url = urllib.parse.unquote(handle_from_url or "") or None

    canonical_handle = _extract_first(r"Handle name\s+(.+?)(?:\n|$)", text) or handle_from_url
    profile_name = _extract_first(r"Profile\s+(.+?)\s+Handle name", text, flags=re.S) or canonical_handle
    uee_record = _extract_first(r"UEE Citizen Record #(\d+)", text)
    main_org = _extract_first(r"Main organization\s+(.+?)\s+Spectrum Identification", text, flags=re.S)
    main_org_sid = _extract_first(r"Spectrum Identification \[SID\]\s+([A-Z0-9_-]+)", text)
    enlisted = _extract_first(r"Enlisted\s+(.+?)(?:\n|$)", text)

    return {
        "handle": canonical_handle,
        "profile_name": profile_name,
        "uee_citizen_record": uee_record,
        "main_organization": main_org,
        "main_organization_sid": main_org_sid,
        "enlisted": enlisted,
    }


def _connect():
    import pymysql

    missing = []
    for name, value in (
        ("MIMIC_DB_HOST", config.MIMIC_DB_HOST),
        ("MIMIC_DB_NAME", config.MIMIC_DB_NAME),
        ("MIMIC_DB_USER", config.MIMIC_DB_USER),
        ("MIMIC_DB_PASSWORD", config.MIMIC_DB_PASSWORD),
    ):
        if value is None or str(value).strip() == "":
            missing.append(name)
    if missing:
        raise RuntimeError("Missing MIMIC database settings: " + ", ".join(missing))

    return pymysql.connect(
        host=config.MIMIC_DB_HOST,
        port=int(config.MIMIC_DB_PORT or 3306),
        user=config.MIMIC_DB_USER,
        password=config.MIMIC_DB_PASSWORD,
        database=config.MIMIC_DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=int(getattr(config, "MIMIC_DB_CONNECT_TIMEOUT_SECONDS", 8) or 8),
        read_timeout=int(getattr(config, "MIMIC_DB_READ_TIMEOUT_SECONDS", 10) or 10),
        write_timeout=int(getattr(config, "MIMIC_DB_READ_TIMEOUT_SECONDS", 10) or 10),
    )


def _fetch_player(conn, handle: str) -> Optional[dict[str, Any]]:
    normalized = (handle or "").strip()
    if not normalized:
        return None

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ep.id,
                ep.handle,
                ep.in_game_name,
                ep.primary_org_id,
                ep.threat_level,
                ep.notes,
                ep.first_seen_at,
                ep.last_seen_at,
                'handle_or_ign' AS matched_by
            FROM entities_players ep
            WHERE LOWER(ep.handle) = LOWER(%s)
               OR LOWER(ep.in_game_name) = LOWER(%s)
            ORDER BY CASE WHEN LOWER(ep.handle) = LOWER(%s) THEN 0 ELSE 1 END, ep.id DESC
            LIMIT 1
            """,
            (normalized, normalized, normalized),
        )
        row = cursor.fetchone()
        if row:
            return row

        cursor.execute(
            """
            SELECT
                ep.id,
                ep.handle,
                ep.in_game_name,
                ep.primary_org_id,
                ep.threat_level,
                ep.notes,
                ep.first_seen_at,
                ep.last_seen_at,
                'alias' AS matched_by,
                pa.alias_value AS matched_alias
            FROM player_aliases pa
            INNER JOIN entities_players ep ON pa.player_id = ep.id
            WHERE LOWER(pa.alias_value) = LOWER(%s)
            ORDER BY pa.id DESC
            LIMIT 1
            """,
            (normalized,),
        )
        return cursor.fetchone()


def _fetch_org_by_id(conn, org_id: Optional[int]) -> Optional[dict[str, Any]]:
    if not org_id:
        return None
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, org_name, org_tag, hostility_level
            FROM entities_orgs
            WHERE id = %s
            LIMIT 1
            """,
            (int(org_id),),
        )
        return cursor.fetchone()


def _fetch_org_by_name_or_tag(conn, *, org_name: Optional[str], org_tag: Optional[str]) -> Optional[dict[str, Any]]:
    cleaned_name = _clean_text(org_name)
    cleaned_tag = _clean_text(org_tag).upper()
    if not cleaned_name and not cleaned_tag:
        return None

    with conn.cursor() as cursor:
        if cleaned_tag and cleaned_name:
            cursor.execute(
                """
                SELECT id, org_name, org_tag, hostility_level
                FROM entities_orgs
                WHERE UPPER(org_tag) = %s OR LOWER(org_name) = LOWER(%s)
                ORDER BY CASE WHEN UPPER(org_tag) = %s THEN 0 ELSE 1 END, id DESC
                LIMIT 1
                """,
                (cleaned_tag, cleaned_name, cleaned_tag),
            )
        elif cleaned_tag:
            cursor.execute(
                """
                SELECT id, org_name, org_tag, hostility_level
                FROM entities_orgs
                WHERE UPPER(org_tag) = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (cleaned_tag,),
            )
        else:
            cursor.execute(
                """
                SELECT id, org_name, org_tag, hostility_level
                FROM entities_orgs
                WHERE LOWER(org_name) = LOWER(%s)
                ORDER BY id DESC
                LIMIT 1
                """,
                (cleaned_name,),
            )
        return cursor.fetchone()


def _fetch_watchlists(conn, *, entity_type: str, entity_id: Optional[int], limit: int = 3) -> list[dict[str, Any]]:
    if not entity_id:
        return []
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, priority, watch_reason, active, created_at
            FROM watchlists
            WHERE entity_type = %s
              AND entity_id = %s
            ORDER BY active DESC,
                     CASE priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'moderate' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                     END ASC,
                     created_at DESC,
                     id DESC
            LIMIT %s
            """,
            (entity_type, int(entity_id), int(limit)),
        )
        return list(cursor.fetchall())


def _fetch_report_summary(conn, *, player_id: Optional[int], days_back: int) -> dict[str, Any]:
    if not player_id:
        return {"total_reports": 0, "piracy_count": 0, "griefer_count": 0, "confirmed_count": 0}
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_reports,
                SUM(CASE WHEN r.report_type = 'piracy' THEN 1 ELSE 0 END) AS piracy_count,
                SUM(CASE WHEN r.report_type = 'griefer' THEN 1 ELSE 0 END) AS griefer_count,
                SUM(CASE WHEN r.status = 'confirmed' THEN 1 ELSE 0 END) AS confirmed_count
            FROM report_players rp
            INNER JOIN reports r ON rp.report_id = r.id
            WHERE rp.player_id = %s
              AND r.observed_at >= %s
            """,
            (int(player_id), cutoff),
        )
        return cursor.fetchone() or {"total_reports": 0, "piracy_count": 0, "griefer_count": 0, "confirmed_count": 0}


def _fetch_associated_orgs(conn, *, player_id: Optional[int], days_back: int) -> list[dict[str, Any]]:
    if not player_id:
        return []
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                eo.id,
                eo.org_name,
                eo.org_tag,
                eo.hostility_level,
                COUNT(*) AS occurrences
            FROM report_players rp
            INNER JOIN reports r ON rp.report_id = r.id
            INNER JOIN report_orgs ro ON r.id = ro.report_id
            INNER JOIN entities_orgs eo ON ro.org_id = eo.id
            WHERE rp.player_id = %s
              AND r.observed_at >= %s
            GROUP BY eo.id, eo.org_name, eo.org_tag, eo.hostility_level
            ORDER BY occurrences DESC, eo.org_name ASC
            LIMIT 5
            """,
            (int(player_id), cutoff),
        )
        return list(cursor.fetchall())


def _fetch_recent_reports(conn, *, player_id: Optional[int], days_back: int) -> list[dict[str, Any]]:
    if not player_id:
        return []
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                r.id,
                r.report_type,
                r.status,
                r.observed_at,
                LEFT(COALESCE(r.summary, ''), 120) AS summary
            FROM report_players rp
            INNER JOIN reports r ON rp.report_id = r.id
            WHERE rp.player_id = %s
              AND r.observed_at >= %s
            ORDER BY r.observed_at DESC, r.id DESC
            LIMIT 3
            """,
            (int(player_id), cutoff),
        )
        return list(cursor.fetchall())


def _active_highest_watch(watches: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    active = [row for row in watches if int(row.get("active") or 0) == 1]
    if not active:
        return None
    return sorted(active, key=lambda row: PRIORITY_ORDER.get(str(row.get("priority") or "").lower(), 0), reverse=True)[0]


def _risk_from_watch(watch: Optional[dict[str, Any]]) -> int:
    if not watch or int(watch.get("active") or 0) != 1:
        return 0
    priority = str(watch.get("priority") or "").lower()
    if priority == "critical":
        return 100
    if priority == "high":
        return 75
    if priority == "moderate":
        return 40
    if priority == "low":
        return 15
    return 10


def _risk_label(score: int, *, player_watch: Optional[dict[str, Any]], org_watch: Optional[dict[str, Any]]) -> tuple[str, str]:
    high_watch = player_watch or org_watch
    if high_watch and str(high_watch.get("priority") or "").lower() in {"critical", "high"}:
        return "critical", "🚨 HOLD / ESCALATE"
    if score >= 75:
        return "critical", "🚨 HOLD / ESCALATE"
    if score >= 25:
        return "warning", "⚠️ REVIEW"
    return "clear", "✅ CLEAR"


def _format_org_label(org: Optional[dict[str, Any]], *, fallback_name: Optional[str] = None, fallback_tag: Optional[str] = None) -> str:
    if org:
        name = org.get("org_name") or fallback_name or "Unknown Org"
        tag = org.get("org_tag") or fallback_tag
    else:
        name = fallback_name or "Unknown Org"
        tag = fallback_tag
    return f"{name} [{tag}]" if tag else str(name)


def _format_watch_line(prefix: str, watch: Optional[dict[str, Any]]) -> Optional[str]:
    if not watch:
        return None
    active_label = "ACTIVE" if int(watch.get("active") or 0) == 1 else "inactive"
    priority = str(watch.get("priority") or "unknown").upper()
    reason = _clean_text(watch.get("watch_reason"))
    if len(reason) > 160:
        reason = reason[:157] + "..."
    return f"{prefix}: {active_label} #{watch.get('id')} {priority}" + (f" — {reason}" if reason else "")


def _format_date(value: Any) -> str:
    if not value:
        return "unknown date"
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def check_rsi_profile(*, rsi_handle: str, rsi_profile_url: str) -> dict[str, Any]:
    """Run a read-only MIMIC check for a submitted RSI profile.

    Returns a compact dict meant for command-channel embeds. It never blocks onboarding
    by raising; failures are captured as status='error'.
    """
    handle = urllib.parse.unquote((rsi_handle or "").strip())
    result: dict[str, Any] = {
        "enabled": bool(getattr(config, "MIMIC_DB_ENABLED", False)),
        "status": "not_configured",
        "label": "⚪ MIMIC CHECK NOT CONFIGURED",
        "risk_score": 0,
        "rsi_handle": handle,
        "rsi_profile_url": rsi_profile_url,
        "profile": None,
        "player": None,
        "primary_org": None,
        "profile_org": None,
        "player_watchlist": None,
        "org_watchlist": None,
        "report_summary": {"total_reports": 0, "piracy_count": 0, "griefer_count": 0, "confirmed_count": 0},
        "associated_orgs": [],
        "recent_reports": [],
        "summary_text": "MIMIC database lookup is disabled for this OnboardingBot instance.",
    }

    if not result["enabled"]:
        return result

    days_back = int(getattr(config, "MIMIC_RECRUIT_SCAN_DAYS", 180) or 180)

    try:
        profile_summary = None
        if getattr(config, "MIMIC_RSI_PROFILE_SCRAPE_ENABLED", True):
            try:
                profile_summary = scrape_rsi_profile_summary(rsi_profile_url)
                result["profile"] = profile_summary
                if profile_summary.get("handle"):
                    handle = str(profile_summary["handle"]).strip() or handle
                    result["rsi_handle"] = handle
            except Exception as exc:
                result["profile_error"] = str(exc)

        conn = _connect()
        try:
            player = _fetch_player(conn, handle)
            result["player"] = player
            player_id = int(player["id"]) if player and player.get("id") else None

            player_watches = _fetch_watchlists(conn, entity_type="player", entity_id=player_id)
            player_watch = _active_highest_watch(player_watches) or (player_watches[0] if player_watches else None)
            result["player_watchlist"] = player_watch

            primary_org = _fetch_org_by_id(conn, player.get("primary_org_id") if player else None)
            result["primary_org"] = primary_org

            profile_org = None
            if profile_summary and (profile_summary.get("main_organization") or profile_summary.get("main_organization_sid")):
                profile_org = _fetch_org_by_name_or_tag(
                    conn,
                    org_name=profile_summary.get("main_organization"),
                    org_tag=profile_summary.get("main_organization_sid"),
                )
                result["profile_org"] = profile_org or {
                    "org_name": profile_summary.get("main_organization"),
                    "org_tag": profile_summary.get("main_organization_sid"),
                    "hostility_level": None,
                    "id": None,
                }

            org_watches: list[dict[str, Any]] = []
            watched_org_ids: set[int] = set()
            for org in (primary_org, profile_org):
                if org and org.get("id") and int(org["id"]) not in watched_org_ids:
                    watched_org_ids.add(int(org["id"]))
                    org_watches.extend(_fetch_watchlists(conn, entity_type="org", entity_id=int(org["id"])))
            org_watch = _active_highest_watch(org_watches) or (org_watches[0] if org_watches else None)
            result["org_watchlist"] = org_watch

            report_summary = _fetch_report_summary(conn, player_id=player_id, days_back=days_back)
            result["report_summary"] = report_summary
            result["associated_orgs"] = _fetch_associated_orgs(conn, player_id=player_id, days_back=days_back)
            result["recent_reports"] = _fetch_recent_reports(conn, player_id=player_id, days_back=days_back)
        finally:
            try:
                conn.close()
            except Exception:
                pass

        score = 0
        score += _risk_from_watch(result.get("player_watchlist"))
        score += _risk_from_watch(result.get("org_watchlist"))
        score += int((result.get("report_summary") or {}).get("piracy_count") or 0) * 20
        score += int((result.get("report_summary") or {}).get("griefer_count") or 0) * 20
        score += int((result.get("report_summary") or {}).get("confirmed_count") or 0) * 10
        result["risk_score"] = score

        player_active_watch = result.get("player_watchlist") if result.get("player_watchlist") and int(result["player_watchlist"].get("active") or 0) == 1 else None
        org_active_watch = result.get("org_watchlist") if result.get("org_watchlist") and int(result["org_watchlist"].get("active") or 0) == 1 else None
        status, label = _risk_label(score, player_watch=player_active_watch, org_watch=org_active_watch)
        result["status"] = status
        result["label"] = label
        result["summary_text"] = format_mimic_result_for_embed(result)
        return result

    except Exception as exc:
        result["status"] = "error"
        result["label"] = "⚠️ MIMIC CHECK UNAVAILABLE"
        result["summary_text"] = (
            "The MIMIC database/profile check could not be completed. "
            f"Manual S-2 review recommended. Error: `{_clean_text(exc)[:180]}`"
        )
        return result


def format_mimic_result_for_embed(result: dict[str, Any]) -> str:
    days_back = int(getattr(config, "MIMIC_RECRUIT_SCAN_DAYS", 180) or 180)
    lines: list[str] = [f"{result.get('label', 'MIMIC Intel Check')} — Risk score: `{result.get('risk_score', 0)}`"]
    lines.append(f"RSI Handle: `{result.get('rsi_handle') or 'Unknown'}`")

    profile = result.get("profile") or {}
    if profile.get("profile_name") and profile.get("profile_name") != result.get("rsi_handle"):
        lines.append(f"RSI Display: `{profile['profile_name']}`")
    if profile.get("uee_citizen_record"):
        lines.append(f"UEE Record: `{profile['uee_citizen_record']}`")

    profile_org = result.get("profile_org")
    primary_org = result.get("primary_org")
    if profile_org:
        lines.append(f"Current RSI Main Org: {_format_org_label(profile_org)}")
    elif primary_org:
        lines.append(f"Known MIMIC Primary Org: {_format_org_label(primary_org)}")
    elif result.get("profile_error"):
        lines.append(f"Current RSI Main Org: unavailable (`{_clean_text(result['profile_error'])[:90]}`)")

    player = result.get("player")
    if player:
        lines.append(f"MIMIC Player Match: `{player.get('handle') or 'Unknown'}` via `{player.get('matched_by') or 'record'}`")
    else:
        lines.append("MIMIC Player Match: none found.")

    player_watch_line = _format_watch_line("Player Watch", result.get("player_watchlist"))
    org_watch_line = _format_watch_line("Org Watch", result.get("org_watchlist"))
    if player_watch_line:
        lines.append(player_watch_line)
    if org_watch_line:
        lines.append(org_watch_line)

    summary = result.get("report_summary") or {}
    lines.append(
        f"Report history ({days_back}d): total={summary.get('total_reports') or 0}, "
        f"piracy={summary.get('piracy_count') or 0}, griefer={summary.get('griefer_count') or 0}, "
        f"confirmed={summary.get('confirmed_count') or 0}."
    )

    associated_orgs = result.get("associated_orgs") or []
    if associated_orgs:
        org_bits = []
        for row in associated_orgs[:3]:
            org_bits.append(f"{_format_org_label(row)} ({row.get('occurrences') or 0})")
        lines.append("Associated reported orgs: " + ", ".join(org_bits))

    recent_reports = result.get("recent_reports") or []
    if recent_reports:
        report_bits = []
        for row in recent_reports[:2]:
            report_bits.append(
                f"#{row.get('id')} {row.get('report_type') or 'report'} / {row.get('status') or 'unknown'} / {_format_date(row.get('observed_at'))}"
            )
        lines.append("Recent reports: " + "; ".join(report_bits))

    if result.get("status") == "clear":
        lines.append("No active player/org watchlist hit or recent report history found.")

    value = "\n".join(lines)
    if len(value) > 1024:
        value = value[:1000].rstrip() + "\n… truncated; review MIMIC manually."
    return value
