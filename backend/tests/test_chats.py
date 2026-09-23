"""WhatsApp exports: my messages are activity, the rest proofs, file kept."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.services import chat_read
from httpx import AsyncClient

TRACES = "/api/v1/traces/import"
_NAME = "Discussion WhatsApp avec Alex Martin.txt"
_IPHONE = (
    "[02/03/2026 21:56:42] Alex Martin : ‎Les messages et les appels "
    "sont chiffrés de bout en bout. Seules les personnes prenant part à "
    "cette discussion peuvent les lire.\n"
    "[02/03/2026 21:58:10] Alex Martin : Salut, le serveur est tombé\n"
    "Tu peux regarder ?\n"
    "[02/03/2026 22:10:05] Moi: Je regarde\n"
    "[02/03/2026 23:40:00] Moi: C'est réparé 🙂\n"
    "[08/03/2026 08:15:00] Alex Martin : ‎Appel vocal manqué\n"
    "[09/03/2026 07:30:00] Alex Martin : Merci pour hier\n"
)
_ANDROID = (
    "5/23/25, 9:56 PM - Messages and calls are end-to-end encrypted. "
    "No one outside of this chat can read them.\n"
    "5/23/25, 9:57 PM - Alex: hi\n"
    "5/24/25, 10:01 AM - Sam: hello: world\n"
)


async def _import(
    client: AsyncClient, auth: dict[str, str], **params: Any
) -> dict[str, Any]:
    person = params.pop("person", "")
    res = await client.post(
        TRACES,
        files=[("files", (_NAME, _IPHONE.encode(), "text/plain"))],
        data={"kinds": ["auto"], "person": person},
        params={k: str(v).lower() for k, v in params.items()},
        headers=auth,
    )
    assert res.status_code == 200, res.text
    file: dict[str, Any] = res.json()["files"][0]
    return file


def test_both_exports_are_read() -> None:
    tz = ZoneInfo("Europe/Paris")
    phone = chat_read.read(_IPHONE.encode(), _NAME, tz)
    assert phone.name == "Alex Martin"
    assert [m.who for m in phone.messages] == [
        "Alex Martin", "Moi", "Moi", "Alex Martin", "Alex Martin",
    ]  # fmt: skip
    assert phone.messages[0].text == (
        "Salut, le serveur est tombé\nTu peux regarder ?"
    )
    assert phone.messages[3].call
    android = chat_read.read(_ANDROID.encode(), "_chat.txt", tz)
    first, second = android.messages
    assert first.at == datetime(2025, 5, 23, 19, 57, tzinfo=UTC)  # May 23
    assert (second.who, second.text) == ("Sam", "hello: world")
    assert chat_read.is_chat(_ANDROID.encode(), "_chat.txt")
    assert not chat_read.is_chat(b"02/03/2026 08:10\n", "Embauche.txt")


async def test_my_messages_are_activity_and_the_file_is_kept(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    read = await _import(client, auth, dry_run=True)
    assert read["columns"]["person"] == "Moi"
    assert [p["name"] for p in read["columns"]["people"]] == [
        "Alex Martin", "Moi",
    ]  # fmt: skip
    kinds = [
        (t["day"], t["kind"], t["time"], t["end"]) for t in read["preview"]
    ]
    assert kinds == [
        ("2026-03-02", "activite", "22:10", "02/03 23:40"),
        ("2026-03-08", "appel", "08:15", None),
        ("2026-03-09", "sms", "07:30", None),
        ("2026-03-09", "document", "07:30", None),
    ]
    day = read["preview"][0]
    assert day["title"] == "WhatsApp — Alex Martin : 2 messages de moi, 1 reçu"
    assert (
        "21:58 Alex Martin : Salut, le serveur est tombé / Tu peux"
        in (day["what"])
    )
    stored = await _import(client, auth)
    assert stored["new"] == 4
    again = await _import(client, auth)
    assert again["duplicates"] == 4
    lines = await client.get(
        "/api/v1/work/days",
        params={"start": "2026-03-02", "end": "2026-03-02"},
        headers=auth,
    )
    (proof,) = lines.json()[0]["proofs"]
    assert (proof["kind"], proof["time"], proof["end"]) == (
        "activite", "22:10", "23:40",
    )  # fmt: skip


async def test_the_person_chosen_is_me(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    read = await _import(client, auth, dry_run=True, person="Alex Martin")
    kinds = [(t["day"], t["kind"]) for t in read["preview"]]
    assert kinds[0] == ("2026-03-02", "activite")
    assert read["preview"][0]["title"].endswith("1 message de moi, 2 reçus")
    assert ("2026-03-09", "activite") in kinds  # « Merci pour hier »
