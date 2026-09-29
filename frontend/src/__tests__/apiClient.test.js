import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL, ApiError, api, tokenStore } from "../services/apiClient.js";

describe("apiClient", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the base URL from the environment (no hardcoded deployment URL)", () => {
    expect(API_BASE_URL).not.toContain("onrender.com");
    expect(API_BASE_URL.endsWith("/")).toBe(false);
  });

  it("sends the bearer token and JSON body", async () => {
    tokenStore.set("abc");
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: 1 }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const data = await api("/x", { method: "POST", body: { a: 1 } });
    expect(data).toEqual({ ok: 1 });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/x`);
    expect(init.headers.Authorization).toBe("Bearer abc");
    expect(init.body).toBe('{"a":1}');
  });

  it("throws ApiError with the server message and emits auth:expired on 401", async () => {
    tokenStore.set("expired");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: "Invalid or expired token" }), { status: 401 })));
    const listener = vi.fn();
    window.addEventListener("auth:expired", listener);
    await expect(api("/secure")).rejects.toMatchObject({ status: 401, message: "Invalid or expired token" });
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener("auth:expired", listener);
  });

  it("maps network failures to a friendly error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const err = await api("/x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
  });
});
