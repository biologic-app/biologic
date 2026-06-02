# Catalog CRUD Status Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow ordinary catalog dictionaries to keep full CRUD while status dictionaries support only list/read and `name` rename.

**Architecture:** Reuse the existing `contexts/catalogs` repository/use-case/router stack. Add status update methods that accept only `name`; keep status create/delete rejected through the existing `resource_read_only` path. Adjust frontend status dictionary configs so forms submit only `name`.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async, pytest, Vue 3, TypeScript, Nuxt UI, Bun.

---

## File Map

- Modify `bio-new-backend/tests/contexts/catalogs/test_catalog_crud_contract.py`: add failing contract tests for status rename and forbidden status code changes/deletes.
- Modify `bio-new-backend/src/contexts/catalogs/presentation/schemas.py`: add strict `StatusUpdateRequest`.
- Modify `bio-new-backend/src/contexts/catalogs/infrastructure/repositories.py`: add update methods to the four status repositories.
- Modify `bio-new-backend/src/contexts/catalogs/application/crud.py`: add four status update use-case methods.
- Modify `bio-new-backend/src/contexts/catalogs/presentation/router.py`: wire status `PATCH` routes to update methods and keep `POST`/`DELETE` forbidden.
- Modify `bio-frontend/src/shared/config/crud-modules.ts`: make status dictionary form fields contain only editable `name`.

## Task 1: Backend Contract Tests

**Files:**
- Modify: `tests/contexts/catalogs/test_catalog_crud_contract.py`

- [ ] **Step 1: Write failing tests for status rename**

Add fake use-case methods:

```python
    async def update_direction_status(
        self,
        item_id: str,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={
                "id": str(item_id),
                "code": "draft",
                "name": payload.model_dump()["name"],
            },
            meta=ResponseMeta(operation="direction_statuses.update"),
        )
```

Add tests:

```python
def test_status_resource_allows_name_update(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.patch(
            "/api/v1/direction_statuses/00000000-0000-0000-0000-000000000001",
            json={"name": "Черновик"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["code"] == "draft"
        assert payload["data"]["name"] == "Черновик"
        assert payload["meta"]["operation"] == "direction_statuses.update"
    finally:
        get_settings.cache_clear()


def test_status_resource_rejects_code_update(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.patch(
            "/api/v1/direction_statuses/00000000-0000-0000-0000-000000000001",
            json={"code": "renamed", "name": "Renamed"},
        )

        assert response.status_code == 422
        payload = response.json()
        assert payload["status"] == 422
        assert any(error["type"] == "extra_forbidden" for error in payload["errors"])
    finally:
        get_settings.cache_clear()
```

Keep the existing status write test for `POST`, and add a specific delete test:

```python
def test_status_resource_rejects_delete(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.delete(
            "/api/v1/direction_statuses/00000000-0000-0000-0000-000000000001",
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "resource_read_only"
    finally:
        get_settings.cache_clear()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest -v tests/contexts/catalogs/test_catalog_crud_contract.py
```

Expected: status rename test fails because `PATCH /direction_statuses/{id}` still returns `409`.

## Task 2: Backend Status Rename Implementation

**Files:**
- Modify: `src/contexts/catalogs/presentation/schemas.py`
- Modify: `src/contexts/catalogs/infrastructure/repositories.py`
- Modify: `src/contexts/catalogs/application/crud.py`
- Modify: `src/contexts/catalogs/presentation/router.py`

- [ ] **Step 1: Add strict status update schema**

Add:

```python
class StatusUpdateRequest(StrictRequest):
    name: str
```

- [ ] **Step 2: Add repository update methods**

For each status repository, add:

```python
    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(self.session, row, _pick(values, ("name",)))
```

- [ ] **Step 3: Add use-case update methods**

Add methods equivalent to:

```python
    async def update_direction_status(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.direction_statuses.update(item_id, _payload(payload))
        return _single_response(row, _status_fields(), operation="direction_statuses.update")
```

Repeat for `sample_statuses`, `research_statuses`, and `test_statuses`.

- [ ] **Step 4: Wire router PATCH endpoints**

Change status `PATCH` handlers to accept `StatusUpdateRequest` and call the matching use-case update method:

```python
@router.patch("/direction_statuses/{item_id}")
async def update_direction_status(
    item_id: UUID,
    payload: StatusUpdateRequest,
    use_case: Annotated[CatalogCrudUseCase, Depends(get_catalog_use_case)],
) -> SingleResponse[dict[str, object]]:
    return await use_case.update_direction_status(item_id, payload)
```

Repeat for `sample_statuses`, `research_statuses`, and `test_statuses`.

Keep status `POST` and `DELETE` handlers calling `reject_read_only_status_write`.

- [ ] **Step 5: Run backend catalog tests**

Run:

```bash
uv run pytest -v tests/contexts/catalogs/test_catalog_crud_contract.py
```

Expected: all tests in the file pass.

## Task 3: Frontend Status Form Config

**Files:**
- Modify: `/home/tminww/Projects/bio/bio-frontend/src/shared/config/crud-modules.ts`

- [ ] **Step 1: Remove `code` from status form fields**

For these configs:

- `direction-statuses`
- `sample-statuses`
- `research-statuses`
- `test-statuses`

Change:

```typescript
fields: [
  { key: 'code', label: 'Код' },
  { key: 'name', label: 'Название', required: true }
]
```

to:

```typescript
fields: [
  { key: 'name', label: 'Название', required: true }
]
```

Columns stay unchanged so `code` remains visible in the table.

- [ ] **Step 2: Run frontend checks**

Run:

```bash
bun run typecheck
bun run build
```

Expected: both commands exit 0.

## Task 4: Final Verification

**Files:**
- Verify modified backend and frontend files.

- [ ] **Step 1: Run backend catalog tests**

Run:

```bash
uv run pytest -v tests/contexts/catalogs/test_catalog_crud_contract.py
```

Expected: all tests in the file pass.

- [ ] **Step 2: Run frontend typecheck and build**

Run in `/home/tminww/Projects/bio/bio-frontend`:

```bash
bun run typecheck
bun run build
```

Expected: both commands exit 0.

- [ ] **Step 3: Review diff**

Run:

```bash
git diff --stat
git diff
```

Expected: diff only touches catalog status rename contracts, status frontend fields, and docs/plan files.
