import { afterEach, beforeEach, describe, expect, mock, spyOn, test } from "bun:test";
import {
  apiRequest,
  backendApiClient,
  setApiHooks,
} from "../../../src/shared/api/client.api";

type MockResult = {
  data?: unknown;
  error?: unknown;
  response: { status: number; statusText?: string };
};

const ok = (data: unknown): MockResult => ({
  data,
  error: undefined,
  response: { status: 200 },
});

const unauthorized = (): MockResult => ({
  error: { code: "access_token_expired" },
  response: { status: 401, statusText: "Unauthorized" },
});

describe("apiRequest refresh-and-retry", () => {
  let requestSpy: ReturnType<typeof spyOn>;

  beforeEach(() => {
    requestSpy = spyOn(backendApiClient, "request");
  });

  afterEach(() => {
    requestSpy.mockRestore();
    setApiHooks({
      onRefresh: async () => false,
      onUnauthorized: () => {},
      onForbidden: () => {},
    });
  });

  test("on 401 it refreshes once and replays the original request", async () => {
    requestSpy
      .mockResolvedValueOnce(unauthorized())
      .mockResolvedValueOnce(ok({ value: 42 }));
    const onRefresh = mock(async () => true);
    const onUnauthorized = mock(() => {});
    setApiHooks({ onRefresh, onUnauthorized });

    const result = await apiRequest<{ value: number }>("/samples");

    expect(result).toEqual({ value: 42 });
    expect(onRefresh).toHaveBeenCalledTimes(1);
    expect(requestSpy).toHaveBeenCalledTimes(2);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  test("when refresh fails it signs out and does not retry", async () => {
    requestSpy.mockResolvedValue(unauthorized());
    const onRefresh = mock(async () => false);
    const onUnauthorized = mock(() => {});
    setApiHooks({ onRefresh, onUnauthorized });

    await expect(apiRequest("/samples")).rejects.toMatchObject({ status: 401 });
    expect(onRefresh).toHaveBeenCalledTimes(1);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
    // Only the initial attempt — no replay after a failed refresh.
    expect(requestSpy).toHaveBeenCalledTimes(1);
  });

  test("a 401 on the refresh endpoint itself never recurses", async () => {
    requestSpy.mockResolvedValue(unauthorized());
    const onRefresh = mock(async () => true);
    const onUnauthorized = mock(() => {});
    setApiHooks({ onRefresh, onUnauthorized });

    await expect(
      apiRequest("/auth/refresh", { method: "POST" }),
    ).rejects.toMatchObject({ status: 401 });
    expect(onRefresh).not.toHaveBeenCalled();
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
    expect(requestSpy).toHaveBeenCalledTimes(1);
  });
});
