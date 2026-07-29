"""HTTP helpers used by the Streamlit ticket-management workspace."""

import httpx


def _headers(admin_token: str) -> dict[str, str]:
    return {"X-Admin-Token": admin_token}


def fetch_tickets(
    api_url: str,
    admin_token: str,
    status: str | None = None,
    risk_level: str | None = None,
) -> list[dict]:
    params = {
        key: value
        for key, value in {"status": status, "risk_level": risk_level}.items()
        if value is not None
    }
    response = httpx.get(
        f"{api_url.rstrip('/')}/tickets",
        headers=_headers(admin_token),
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def update_ticket_status(
    api_url: str, admin_token: str, ticket_id: str, status: str
) -> dict:
    response = httpx.patch(
        f"{api_url.rstrip('/')}/tickets/{ticket_id}",
        headers=_headers(admin_token),
        json={"status": status},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
