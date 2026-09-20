"""Generate a pre-filled, importable Apple Shortcut (``.shortcut``).

The file embeds the ingest endpoint and a scoped token, so the user
imports it once and syncs the day's weight in a single tap — no data
picking, no JSON editing. Unsigned shortcuts need the one-time iOS
"Autoriser les raccourcis non fiables" toggle. The exhaustive history
(millions of samples, ECG, workouts) stays the zip-upload path.

Only action identifiers and the variable-token serialisation that are
stable across Shortcuts versions are used, so the file imports cleanly.
"""

from __future__ import annotations

import plistlib
import uuid
from typing import Any

#: Object-replacement char marking an embedded variable inside a string.
_OBJ = "￼"
_WEIGHT_HK = "HKQuantityTypeIdentifierBodyMass"

_INPUT_CLASSES = [
    "WFAppStoreAppContentItem",
    "WFArticleContentItem",
    "WFContactContentItem",
    "WFDateContentItem",
    "WFEmailAddressContentItem",
    "WFGenericFileContentItem",
    "WFImageContentItem",
    "WFiTunesProductContentItem",
    "WFLocationContentItem",
    "WFDCMapsLinkContentItem",
    "WFAVAssetContentItem",
    "WFPDFContentItem",
    "WFPhoneNumberContentItem",
    "WFRichTextContentItem",
    "WFSafariWebPageContentItem",
    "WFStringContentItem",
    "WFURLContentItem",
]


def build_shortcut(endpoint: str, token: str) -> bytes:
    """Return a binary-plist ``.shortcut`` that posts the day's weight."""
    ask_id = str(uuid.uuid4()).upper()
    actions = [
        _comment(),
        _ask(ask_id),
        _post(endpoint, token, ask_id),
        _notify(),
    ]
    return plistlib.dumps(_workflow(actions), fmt=plistlib.FMT_BINARY)


def _workflow(actions: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap the actions in the top-level workflow plist structure."""
    return {
        "WFWorkflowClientVersion": "1146.14",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {
            "WFWorkflowIconStartColor": 4271458815,
            "WFWorkflowIconGlyphNumber": 59511,
        },
        "WFWorkflowImportQuestions": [],
        "WFWorkflowTypes": ["NCWidget", "WatchKit"],
        "WFWorkflowInputContentItemClasses": _INPUT_CLASSES,
        "WFWorkflowActions": actions,
    }


def _comment() -> dict[str, Any]:
    """A human note shown at the top of the shortcut."""
    text = (
        "Phoenix Santé — envoie ton poids du jour vers ton serveur en un "
        "tap. Rien à configurer : le jeton et l'adresse sont déjà inclus."
    )
    return _action("comment", {"WFCommentActionText": text})


def _ask(ask_id: str) -> dict[str, Any]:
    """Ask the user for the day's weight (a number)."""
    return _action(
        "ask",
        {
            "UUID": ask_id,
            "WFInputType": "Number",
            "WFAskActionPrompt": "Poids du jour (kg)",
        },
    )


def _post(endpoint: str, token: str, ask_id: str) -> dict[str, Any]:
    """POST the weight as JSON with the embedded bearer token."""
    body = _dict_field([_var_item(_WEIGHT_HK, ask_id)])
    headers = _dict_field([_str_item("Authorization", f"Bearer {token}")])
    return _action(
        "downloadurl",
        {
            "WFURL": endpoint,
            "WFHTTPMethod": "POST",
            "WFHTTPBodyType": "JSON",
            "WFJSONValues": body,
            "WFHTTPHeaders": headers,
        },
    )


def _notify() -> dict[str, Any]:
    """Confirm the sync with a local notification."""
    return _action(
        "notification",
        {
            "WFNotificationActionTitle": "Phoenix Santé",
            "WFNotificationActionBody": "Poids envoyé ✅",
        },
    )


def _action(name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Build one workflow action entry."""
    return {
        "WFWorkflowActionIdentifier": f"is.workflow.actions.{name}",
        "WFWorkflowActionParameters": params,
    }


def _dict_field(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Serialise a dictionary parameter (headers / JSON body)."""
    return {
        "WFSerializationType": "WFDictionaryFieldValue",
        "Value": {"WFDictionaryFieldValueItems": items},
    }


def _str_item(key: str, value: str) -> dict[str, Any]:
    """A dictionary item whose value is a literal string."""
    return {"WFItemType": 0, "WFKey": _text(key), "WFValue": _text(value)}


def _var_item(key: str, out_id: str) -> dict[str, Any]:
    """A dictionary item whose value is a prior action's output."""
    return {"WFItemType": 0, "WFKey": _text(key), "WFValue": _var(out_id)}


def _text(value: str) -> dict[str, Any]:
    """A plain text token."""
    return {
        "WFSerializationType": "WFTextTokenString",
        "Value": {"string": value, "attachmentsByRange": {}},
    }


def _var(out_id: str) -> dict[str, Any]:
    """A text token that embeds a single variable (magic variable)."""
    attach = {
        "OutputUUID": out_id,
        "OutputName": "Provided Input",
        "Type": "ActionOutput",
    }
    return {
        "WFSerializationType": "WFTextTokenString",
        "Value": {"string": _OBJ, "attachmentsByRange": {"{0, 1}": attach}},
    }
