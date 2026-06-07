import type { EventFilters, EventsResponse, HotspotsResponse } from "./types";
import { timeRangeForPreset } from "./time";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

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

export async function fetchEvents(filters: EventFilters): Promise<EventsResponse> {
  const params = filterParams(filters);
  params.set("sort", filters.sort);
  params.set("limit", String(filters.limit));

  const response = await fetch(`${API_BASE}/v1/events?${params.toString()}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export async function fetchHotspots(filters: EventFilters): Promise<HotspotsResponse> {
  const params = filterParams(filters);
  params.set("grid_km", "2");
  params.set("limit", "80");

  const response = await fetch(`${API_BASE}/v1/hotspots?${params.toString()}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}
