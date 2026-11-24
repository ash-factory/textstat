"""Names and policies for the factory's GitHub issue and pull request labels.

Values are the wire names. Keep the default hold tuple in station-config order.
An explicit station override is applied by the caller.
"""

import re


AT = "at@"
AGENT = "agent:"
TRY = "try:"
TYPE = "type:"
CHECK = "check:"
PRIORITY = "priority:"
CAUSE = "cause:"
ROUTE = "route:"
LEDGER = "factory:ledger:"

READY = "ready-for-dev"
REVIEW = "openhands-review"
NO_REVIEW = "review:none"
NEEDS_OWNER = "needs-owner"
NEEDS_INPUT = "needs-input"
NEEDS_DECISION = "needs-decision"
STOP = "factory:stop"
STUCK = "factory-stuck"
ENDED = "factory-ended"
WAITS_MODEL = "factory:waits-model"
COVERED = "factory:covered"
PRE_EMPTED = "factory:pre-empted"
CONTROL = "factory:control"
ATTENTION = "factory:attention"
REQUEST = "factory:request"
LEARN = "factory:learn"
PATTERN_CLEANUP = "factory:pattern-cleanup"
FIRST_CARD = "factory:first-card"
FOUNDATIONS = "factory:foundations"
FOUNDATIONS_HOLD = "factory:foundations-missing"
RED_MAIN = "red-main"
FAILURE_SEEN = "failure-seen"
CONTRACT_CHANGED = "contract-changed"
DEPLOY_FAILED = "deploy-failed"
DEPLOY_REPAIR = "deploy-repair"
URGENT = PRIORITY + "urgent"
HIGH = PRIORITY + "high"
MEDIUM = PRIORITY + "medium"
LOW = PRIORITY + "low"
RUNNING_APP = CHECK + "running-app"
WALK = CHECK + "walk"

OWNER_ASKS = frozenset((NEEDS_OWNER, NEEDS_DECISION))
BOARD_INPUT_WAITS = OWNER_ASKS | {NEEDS_INPUT}
HOLD_LABELS = (NEEDS_OWNER, NEEDS_DECISION, NEEDS_INPUT, STOP, STUCK, ENDED, WAITS_MODEL, COVERED)
MOVE_BLOCKERS = frozenset(HOLD_LABELS) - {STOP, COVERED}
RECOVERY_HOLDS = (STUCK, ENDED, NEEDS_INPUT)
ORCHESTRATOR_QUEUE_WAITS = (NEEDS_INPUT, NEEDS_OWNER, STUCK)

# Preserve the doorbell's existing classification of hand-written issues, including
# the broad factory prefix and the absence of a review: prefix.
FACTORY_NAMES = BOARD_INPUT_WAITS | {
    READY, RED_MAIN, FAILURE_SEEN, CONTRACT_CHANGED, DEPLOY_FAILED, DEPLOY_REPAIR, REVIEW,
}
FACTORY_PREFIXES = ("factory", AT, AGENT, TRY, TYPE, CHECK, PRIORITY, CAUSE, ROUTE)


_STATION_LABELS = {
    "{{label_ready}}": READY,
    "{{label_review}}": REVIEW,
    "{{label_needs_owner}}": NEEDS_OWNER,
}


def resolve_station_labels(value):
    """Resolve only factory label references. Leave machine template variables for the station builder."""
    if isinstance(value, dict):
        return {key: resolve_station_labels(item) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_station_labels(item) for item in value]
    if isinstance(value, str):
        if value == "{{label_holds}}":
            return list(HOLD_LABELS)
        return _STATION_LABELS.get(value, value)
    return value


_WORKFLOW_LABELS = {
    "ATTENTION": ATTENTION,
    "CONTROL": CONTROL,
    "HIGH": HIGH,
    "NEEDS_OWNER": NEEDS_OWNER,
    "PATTERN_CLEANUP": PATTERN_CLEANUP,
    "READY": READY,
    "RED_MAIN": RED_MAIN,
    "STOP": STOP,
    "STUCK": STUCK,
    "TYPE_HARNESS": TYPE + "harness",
}
_WORKFLOW_REFERENCE = re.compile(r"\{\{LABEL_(\w+)\}\}")


def render_workflow(text):
    """Bind shared labels in a project workflow before it is copied to its repository."""
    return _WORKFLOW_REFERENCE.sub(lambda match: _WORKFLOW_LABELS[match[1]], text)
