import type { EventFilters, EventsResponse, HotspotsResponse } from "./types";
import { timeRangeForPreset } from "./time";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

const COLD_START_RETRIES = 8;
const COLD_START_BASE_MS = 2000;

let apiWarm = false;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchOnce(url: string): Promise<Response> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response;
}

/** Render free tier: retry only until the first successful response, then fetch directly. */
async function fetchWithRetry(
  url: string,
  onRetrying?: () => void,
): Promise<Response> {
  if (apiWarm) {
    try {
      return await fetchOnce(url);
    } catch {
      apiWarm = false;
    }
  }

  let lastError: Error | null = null;

  for (let attempt = 0; attempt < COLD_START_RETRIES; attempt++) {
    if (attempt > 0) onRetrying?.();
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (response.ok) {
        apiWarm = true;
        return response;
      }
      if (response.status >= 500 && attempt < COLD_START_RETRIES - 1) {
        await sleep(COLD_START_BASE_MS * (attempt + 1));
        continue;
      }
      throw new Error(`API error: ${response.status}`);
    } catch (err) {
      lastError = err instanceof Error ? err : new Error("API unreachable");
      if (attempt < COLD_START_RETRIES - 1) {
        await sleep(COLD_START_BASE_MS * (attempt + 1));
      }
    }
  }

  throw lastError ?? new Error("API unreachable");
}

function filterParams(filters: EventFilters): URLSearchParams {
  const params = new URLSearchParams();
  const range = timeRangeForPreset(filters.time);
  if (range.from) params.set("from", range.from);
  if (range.to) params.set("to", range.to);

  if (filters.categories.length === 1) {
    params.set("category", filters.categories[0]);
  } else if (filters.categories.length > 1) {
    params.set("category", filters.categories.join(","));
  }

  const query = filters.query.trim();
  if (query) params.set("q", query);

  return params;
}

export async function fetchEvents(
  filters: EventFilters,
  onRetrying?: () => void,
): Promise<EventsResponse> {
  const params = filterParams(filters);
  params.set("sort", filters.sort);
  params.set("limit", String(filters.limit));

  const response = await fetchWithRetry(
    `${API_BASE}/v1/events?${params.toString()}`,
    onRetrying,
  );
  return response.json();
}

export async function fetchHotspots(
  filters: EventFilters,
  onRetrying?: () => void,
): Promise<HotspotsResponse> {
  const params = filterParams(filters);
  params.set("grid_km", "2");
  params.set("limit", "80");

  const response = await fetchWithRetry(
    `${API_BASE}/v1/hotspots?${params.toString()}`,
    onRetrying,
  );
  return response.json();
}
