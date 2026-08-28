from __future__ import annotations

from typing import Literal, get_args


CommitmentAction = Literal[
    "accept",
    "activate",
    "wait",
    "submit",
    "request_takeover",
    "pause",
]

ACTION_TARGET = {
    "accept": "accepted",
    "activate": "active",
    "wait": "waiting",
    "submit": "submitted",
    "request_takeover": "manual_takeover",
    "pause": "paused",
}


def allowed_commitment_actions() -> tuple[str, ...]:
    return get_args(CommitmentAction)


def target_commitment_status(action: CommitmentAction) -> str:
    return ACTION_TARGET[action]
