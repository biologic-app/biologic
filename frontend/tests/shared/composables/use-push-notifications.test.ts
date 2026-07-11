import { afterAll, afterEach, beforeEach, describe, expect, mock, test } from "bun:test";

const VAPID_PUBLIC_KEY = "BEl62iUYgUivxIkv69yViEuiBIa40HI6DLQqAxMh8EQ";

interface FakePushSubscription {
  endpoint: string;
  toJSON: () => { keys: { p256dh: string; auth: string } };
  unsubscribe: ReturnType<typeof mock>;
}

const fakeSubscription: FakePushSubscription = {
  endpoint: "https://push.example/endpoint-abc",
  toJSON: () => ({ keys: { p256dh: "p256dh-value", auth: "auth-value" } }),
  unsubscribe: mock(async () => true),
};

const pushManagerSubscribe = mock(async () => fakeSubscription);
let pushManagerGetSubscription = mock(async (): Promise<FakePushSubscription | null> => null);

const fakeRegistration = {
  pushManager: {
    subscribe: pushManagerSubscribe,
    getSubscription: (...args: unknown[]) => pushManagerGetSubscription(...(args as [])),
  },
};

let requestPermission = mock(async (): Promise<NotificationPermission> => "granted");

const originalFetch = globalThis.fetch;

// usePushNotifications computes `isSupported` and the initial `permission`
// ref at module *import* time, so every browser global it reads has to be
// stubbed synchronously here — a `beforeAll` hook runs too late (hooks fire
// during the test-run phase, after this file has already finished loading
// and its top-level `await import` below has already resolved).
(globalThis as unknown as { window: unknown }).window = globalThis;
(globalThis as unknown as { PushManager: unknown }).PushManager = class {};
Object.defineProperty(globalThis.navigator, "serviceWorker", {
  configurable: true,
  value: {
    ready: Promise.resolve(fakeRegistration),
    register: mock(async () => fakeRegistration),
  },
});
(globalThis as unknown as { Notification: unknown }).Notification = {
  permission: "default",
  requestPermission: (...args: unknown[]) => requestPermission(...(args as [])),
};

const { usePushNotifications } = await import("@/shared/composables/usePushNotifications");

// These globals are shared process-wide across every test file bun:test
// runs in this invocation — left in place, `window` alone breaks unrelated
// suites that branch on `typeof window !== 'undefined'` (e.g. useServerTable
// assumes a real window with `.location`). Restore a clean slate once this
// file's tests are done.
afterAll(() => {
  delete (globalThis as { window?: unknown }).window;
  delete (globalThis as { PushManager?: unknown }).PushManager;
  delete (globalThis as { Notification?: unknown }).Notification;
  (globalThis as unknown as { fetch: unknown }).fetch = originalFetch;
  delete (globalThis.navigator as { serviceWorker?: unknown }).serviceWorker;
});

interface CapturedRequest {
  url: string;
  method: string;
  body: unknown;
}

describe("usePushNotifications", () => {
  let requests: CapturedRequest[];

  beforeEach(() => {
    requests = [];
    const fetchMock = mock(async (input: RequestInfo | URL, init?: RequestInit) => {
      // The generated API client calls `fetch(request)` with a single
      // `Request` object rather than `fetch(url, init)` — read both shapes
      // so the mock works regardless of which one shows up, and log every
      // call so assertions don't have to re-derive this from `mock.calls`.
      const isRequestObject = input instanceof Request;
      const url = isRequestObject ? input.url : String(input);
      const method = (isRequestObject ? input.method : init?.method || "GET").toUpperCase();
      const rawBody = isRequestObject
        ? await input.clone().text()
        : init?.body
          ? String(init.body)
          : "";
      requests.push({ url, method, body: rawBody ? JSON.parse(rawBody) : undefined });

      if (url.includes("/push/vapid-public-key") && method === "GET") {
        return new Response(JSON.stringify({ public_key: VAPID_PUBLIC_KEY }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("/push/subscriptions") && method === "POST") {
        return new Response(
          JSON.stringify({
            data: {
              id: "00000000-0000-0000-0000-000000000001",
              endpoint: fakeSubscription.endpoint,
            },
            meta: { operation: "push.subscribe" },
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.includes("/push/subscriptions") && method === "DELETE") {
        return new Response(null, { status: 204 });
      }
      throw new Error(`Unexpected fetch: ${method} ${url}`);
    });
    (globalThis as unknown as { fetch: unknown }).fetch = fetchMock;

    pushManagerSubscribe.mockClear();
    fakeSubscription.unsubscribe.mockClear();
    requestPermission = mock(async (): Promise<NotificationPermission> => "granted");
    pushManagerGetSubscription = mock(async () => null);
    // usePushNotifications' subscribed/permission state is a module-level
    // singleton (by design — see the composable) so it survives across
    // tests in this file; reset it explicitly for test isolation.
    usePushNotifications().isSubscribed.value = false;
  });

  afterEach(() => {
    mock.restore();
  });

  test("enable() requests permission, subscribes, and posts the subscription", async () => {
    const push = usePushNotifications();

    await push.enable();

    expect(pushManagerSubscribe).toHaveBeenCalledTimes(1);
    const subscribeCall = pushManagerSubscribe.mock.calls[0]![0] as {
      userVisibleOnly: boolean;
      applicationServerKey: Uint8Array;
    };
    expect(subscribeCall.userVisibleOnly).toBe(true);
    expect(subscribeCall.applicationServerKey).toBeInstanceOf(Uint8Array);

    const postRequest = requests.find(
      (r) => r.url.includes("/push/subscriptions") && r.method === "POST",
    );
    expect(postRequest?.body).toEqual({
      endpoint: fakeSubscription.endpoint,
      keys: { p256dh: "p256dh-value", auth: "auth-value" },
    });

    expect(push.isSubscribed.value).toBe(true);
    expect(push.permission.value).toBe("granted");
  });

  test("enable() stops before subscribing when permission is denied", async () => {
    requestPermission = mock(async (): Promise<NotificationPermission> => "denied");
    const push = usePushNotifications();

    await push.enable();

    expect(pushManagerSubscribe).not.toHaveBeenCalled();
    expect(requests).toEqual([]);
    expect(push.isSubscribed.value).toBe(false);
  });

  test("disable() unsubscribes locally and deletes the server-side subscription", async () => {
    pushManagerGetSubscription = mock(async () => fakeSubscription);
    const push = usePushNotifications();

    await push.disable();

    expect(fakeSubscription.unsubscribe).toHaveBeenCalledTimes(1);
    const deleteRequest = requests.find(
      (r) => r.url.includes("/push/subscriptions") && r.method === "DELETE",
    );
    expect(deleteRequest?.body).toEqual({ endpoint: fakeSubscription.endpoint });
    expect(push.isSubscribed.value).toBe(false);
  });

  test("disable() is a no-op when there is no active subscription", async () => {
    pushManagerGetSubscription = mock(async () => null);
    const push = usePushNotifications();

    await push.disable();

    expect(fakeSubscription.unsubscribe).not.toHaveBeenCalled();
    expect(requests).toEqual([]);
  });
});
