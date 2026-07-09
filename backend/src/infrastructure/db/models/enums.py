from __future__ import annotations

from enum import StrEnum


class RoleScopeType(StrEnum):
    GLOBAL = "global"
    OWN_BRANCH = "own_branch"
    OWN_LAB = "own_lab"
    OWN_OBJECTS = "own_objects"


class AccessScopeType(StrEnum):
    OWN = "own"
    OWN_LAB = "own_lab"
    ALL_LABS = "all_labs"
    OWN_BRANCH = "own_branch"
    ALL_BRANCHES = "all_branches"
    ALL = "all"
