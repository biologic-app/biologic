#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8081/api/v1}"
RUN_ID="${RUN_ID:-httpie-crud-$(date +%Y%m%d%H%M%S)}"

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 127
  }
}

request() {
  http --ignore-stdin --check-status --body "$@"
}

expect_json() {
  local json="$1"
  local filter="$2"
  local expected="$3"
  local actual

  actual="$(jq -r "$filter" <<<"$json")"
  if [[ "$actual" != "$expected" ]]; then
    echo "Assertion failed: $filter" >&2
    echo "Expected: $expected" >&2
    echo "Actual:   $actual" >&2
    exit 1
  fi
}

cleanup() {
  if [[ -n "${ROLE_PERMISSION_ID:-}" ]]; then
    request DELETE "$BASE_URL/role_permissions/$ROLE_PERMISSION_ID" >/dev/null || true
  fi
  if [[ -n "${USER_ID:-}" ]]; then
    request DELETE "$BASE_URL/users/$USER_ID" >/dev/null || true
  fi
  if [[ -n "${PERMISSION_ID:-}" ]]; then
    request DELETE "$BASE_URL/permissions/$PERMISSION_ID" >/dev/null || true
  fi
  if [[ -n "${ROLE_ID:-}" ]]; then
    request DELETE "$BASE_URL/roles/$ROLE_ID" >/dev/null || true
  fi
  if [[ -n "${BRANCH_ID:-}" ]]; then
    request DELETE "$BASE_URL/branches/$BRANCH_ID" >/dev/null || true
  fi
}

require http
require jq
trap cleanup EXIT

echo "Running CRUD smoke test against $BASE_URL"
echo "RUN_ID=$RUN_ID"

health="$(request GET "$BASE_URL/health")"
expect_json "$health" ".status" "ok"

branch="$(request POST "$BASE_URL/branches" code="$RUN_ID-branch" name="HTTPie Branch")"
BRANCH_ID="$(jq -r ".data.id" <<<"$branch")"
expect_json "$branch" ".meta.operation" "branches.create"
expect_json "$branch" ".data.code" "$RUN_ID-branch"

branches="$(request GET "$BASE_URL/branches" limit==5)"
expect_json "$branches" ".meta.limit" "5"

branch="$(request PATCH "$BASE_URL/branches/$BRANCH_ID" name="HTTPie Branch Updated")"
expect_json "$branch" ".meta.operation" "branches.update"
expect_json "$branch" ".data.name" "HTTPie Branch Updated"

branch="$(request GET "$BASE_URL/branches/$BRANCH_ID")"
expect_json "$branch" ".data.id" "$BRANCH_ID"

role="$(request POST "$BASE_URL/roles" key="$RUN_ID-role" name="HTTPie Role" scope_type=global)"
ROLE_ID="$(jq -r ".data.id" <<<"$role")"
expect_json "$role" ".meta.operation" "roles.create"
expect_json "$role" ".data.key" "$RUN_ID-role"

role="$(request PATCH "$BASE_URL/roles/$ROLE_ID" name="HTTPie Role Updated")"
expect_json "$role" ".meta.operation" "roles.update"
expect_json "$role" ".data.name" "HTTPie Role Updated"

role="$(request GET "$BASE_URL/roles/$ROLE_ID")"
expect_json "$role" ".data.id" "$ROLE_ID"

permission="$(request POST "$BASE_URL/permissions" resource="$RUN_ID-resource" action=read)"
PERMISSION_ID="$(jq -r ".data.id" <<<"$permission")"
expect_json "$permission" ".meta.operation" "permissions.create"
expect_json "$permission" ".data.resource" "$RUN_ID-resource"

permission="$(request PATCH "$BASE_URL/permissions/$PERMISSION_ID" action=manage)"
expect_json "$permission" ".meta.operation" "permissions.update"
expect_json "$permission" ".data.action" "manage"

permission="$(request GET "$BASE_URL/permissions/$PERMISSION_ID")"
expect_json "$permission" ".data.id" "$PERMISSION_ID"

role_permission="$(
  request POST "$BASE_URL/role_permissions" \
    role_id="$ROLE_ID" \
    permission_id="$PERMISSION_ID" \
    scope=all
)"
ROLE_PERMISSION_ID="$(jq -r ".data.id" <<<"$role_permission")"
expect_json "$role_permission" ".meta.operation" "role_permissions.create"
expect_json "$role_permission" ".data.scope" "all"

role_permissions="$(request GET "$BASE_URL/roles/$ROLE_ID/permissions")"
expect_json "$role_permissions" ".meta.operation" "roles.permissions.read"
expect_json "$role_permissions" ".data.permissions[0].id" "$PERMISSION_ID"

role_permission="$(request GET "$BASE_URL/role_permissions/$ROLE_PERMISSION_ID")"
expect_json "$role_permission" ".data.id" "$ROLE_PERMISSION_ID"

role_permission="$(request PATCH "$BASE_URL/role_permissions/$ROLE_PERMISSION_ID" scope=own_lab)"
expect_json "$role_permission" ".meta.operation" "role_permissions.update"
expect_json "$role_permission" ".data.scope" "own_lab"

request DELETE "$BASE_URL/role_permissions/$ROLE_PERMISSION_ID" >/dev/null
unset ROLE_PERMISSION_ID
request DELETE "$BASE_URL/permissions/$PERMISSION_ID" >/dev/null
unset PERMISSION_ID
request DELETE "$BASE_URL/roles/$ROLE_ID" >/dev/null
unset ROLE_ID

roles="$(request GET "$BASE_URL/roles" limit==100)"
ADMIN_ROLE_ID="$(jq -r '.items[] | select(.key == "admin") | .id' <<<"$roles" | head -n 1)"
if [[ -z "$ADMIN_ROLE_ID" ]]; then
  echo "Seeded admin role was not found" >&2
  exit 1
fi

user="$(
  request POST "$BASE_URL/users" \
    username="$RUN_ID-user" \
    password_hash="$RUN_ID-password-hash" \
    code="$RUN_ID-user-code" \
    first_name=HTTPie \
    last_name=User \
    is_registrar:=false \
    is_lab_head:=false \
    is_branch_head:=false \
    role_id="$ADMIN_ROLE_ID"
)"
USER_ID="$(jq -r ".data.id" <<<"$user")"
expect_json "$user" ".meta.operation" "users.create"
expect_json "$user" ".data.username" "$RUN_ID-user"

user="$(request PATCH "$BASE_URL/users/$USER_ID" first_name="HTTPie Updated")"
expect_json "$user" ".meta.operation" "users.update"
expect_json "$user" ".data.first_name" "HTTPie Updated"

user="$(request GET "$BASE_URL/users/$USER_ID")"
expect_json "$user" ".data.id" "$USER_ID"

user_permissions="$(request GET "$BASE_URL/users/$USER_ID/permissions")"
expect_json "$user_permissions" ".meta.operation" "users.permissions.read"
expect_json "$user_permissions" "(.data.permissions | length) > 0" "true"

current_user_permissions="$(request GET "$BASE_URL/user/me/permissions" "X-Actor-Id:$USER_ID")"
expect_json "$current_user_permissions" ".meta.operation" "users.permissions.read"
expect_json "$current_user_permissions" "(.data.permissions | length) > 0" "true"

request DELETE "$BASE_URL/users/$USER_ID" >/dev/null
unset USER_ID
request DELETE "$BASE_URL/branches/$BRANCH_ID" >/dev/null
unset BRANCH_ID

echo "CRUD smoke test passed"
