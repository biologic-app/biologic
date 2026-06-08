import { describe, expect, test } from "bun:test";
import { useServerTable } from "../../../src/shared/composables/useServerTable";
import type { ApiViewResponse } from "../../../src/shared/types/api";

const response = <T>(
  items: T[],
  nextCursor: string | null,
  total = items.length,
): ApiViewResponse<T> => ({
  items,
  meta: {
    timestamp: "2026-06-08T00:00:00Z",
    requestId: null,
    version: "v1",
    includesRequested: [],
    includesApplied: [],
    includesAllowed: [],
    total,
    limit: 100,
    nextCursor,
    hasMore: Boolean(nextCursor),
  },
});

describe("useServerTable infinite pagination", () => {
  test("uses meta.nextCursor as the next cursor parameter", async () => {
    const calls: Array<Record<string, unknown>> = [];
    const table = useServerTable<{ id: number }>(
      async (params) => {
        calls.push(params);
        return calls.length === 1
          ? response([{ id: 1 }], "cursor-2", 2)
          : response([{ id: 2 }], null, 2);
      },
      { mode: "infinite", minimumLoadingMs: 0 },
    );

    await table.fetch();
    expect(table.hasMore.value).toBe(true);

    await table.loadMore();

    expect(calls).toHaveLength(2);
    expect(calls[0].cursor).toBeUndefined();
    expect(calls[1].cursor).toBe("cursor-2");
    expect(table.data.value.map((row) => row.id)).toEqual([1, 2]);
    expect(table.hasMore.value).toBe(false);
  });

  test("does not keep loading when only hasMore is true", async () => {
    const calls: Array<Record<string, unknown>> = [];
    const table = useServerTable<{ id: number }>(
      async (params) => {
        calls.push(params);
        return {
          ...response([{ id: 1 }], null),
          meta: {
            ...response([{ id: 1 }], null).meta,
            hasMore: true,
          },
        };
      },
      { mode: "infinite", minimumLoadingMs: 0 },
    );

    await table.fetch();
    await table.loadMore();

    expect(calls).toHaveLength(1);
    expect(table.hasMore.value).toBe(false);
  });
});
