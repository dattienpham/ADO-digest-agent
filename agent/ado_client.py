import base64
from datetime import datetime, timezone
import requests
from config import ADO_PAT, ADO_BASE_URL, ADO_PROJECT

_token = base64.b64encode(f":{ADO_PAT}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {_token}",
    "Content-Type": "application/json",
}


def _wiql(query: str) -> list[int]:
    resp = requests.post(
        f"{ADO_BASE_URL}/_apis/wit/wiql?api-version=7.1&timePrecision=true",
        headers=HEADERS,
        json={"query": query},
        timeout=30,
    )
    if not resp.ok:
        print(f"[ado_client] WIQL {resp.status_code} — body: {resp.text}")
    resp.raise_for_status()
    return [item["id"] for item in resp.json().get("workItems", [])]


def _get_items_by_ids(ids: list[int]) -> list[dict]:
    if not ids:
        return []
    # ADO allows up to 200 IDs per batch call
    results = []
    for i in range(0, len(ids), 200):
        chunk = ids[i:i + 200]
        ids_str = ",".join(str(x) for x in chunk)
        fields = (
            "System.Id,System.Title,System.State,System.AssignedTo,"
            "System.CreatedDate,System.ChangedDate,System.AreaPath,"
            "System.CreatedBy,Microsoft.VSTS.Common.Priority,"
            "Microsoft.VSTS.Scheduling.TargetDate"
        )
        resp = requests.get(
            f"{ADO_BASE_URL}/_apis/wit/workItems?ids={ids_str}&fields={fields}&api-version=7.1",
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        results.extend(resp.json().get("value", []))
    return results


def get_new_stories(start_iso: str, end_iso: str) -> list[dict]:
    query = f"""
    SELECT [System.Id]
    FROM WorkItems
    WHERE [System.TeamProject] = '{ADO_PROJECT}'
      AND [System.WorkItemType] = 'User Story'
      AND [System.CreatedDate] >= '{start_iso}'
      AND [System.CreatedDate] < '{end_iso}'
    ORDER BY [System.CreatedDate] DESC
    """
    ids = _wiql(query)
    return _get_items_by_ids(ids)


def get_active_stories_changed_since(since_iso: str) -> list[dict]:
    query = f"""
    SELECT [System.Id]
    FROM WorkItems
    WHERE [System.TeamProject] = '{ADO_PROJECT}'
      AND [System.WorkItemType] = 'User Story'
      AND [System.State] NOT IN ('Closed', 'Removed')
      AND [System.ChangedDate] >= '{since_iso}'
    ORDER BY [System.ChangedDate] DESC
    """
    ids = _wiql(query)
    return _get_items_by_ids(ids)


def _parse_ado_date(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def get_recent_comments(work_item_ids: list[int], since_iso: str) -> dict[int, list]:
    from config import MAX_COMMENTS_PER_STORY
    # since_iso is 'YYYY-MM-DD HH:MM:SS' (UTC naive) — convert to aware datetime for comparison
    since_dt = datetime.strptime(since_iso, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    results = {}
    for wid in work_item_ids:
        try:
            resp = requests.get(
                f"{ADO_BASE_URL}/_apis/wit/workItems/{wid}/comments?api-version=7.1-preview.3",
                headers=HEADERS,
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            comments = resp.json().get("comments", [])
            new_comments = [
                c for c in comments
                if c.get("createdDate") and _parse_ado_date(c["createdDate"]) >= since_dt
            ]
            if new_comments:
                sorted_comments = sorted(new_comments, key=lambda c: c["createdDate"], reverse=True)
                results[wid] = sorted_comments[:MAX_COMMENTS_PER_STORY]
        except requests.exceptions.RequestException:
            continue
    return results
