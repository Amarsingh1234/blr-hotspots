"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EventCard } from "@/components/EventCard";
import { SearchBox } from "@/components/SearchBox";
import { ALL_CATEGORIES, CATEGORY_META } from "@/lib/categories";
import {
  eventsInArea,
  findAreaByQuery,
  KORAMANGALA,
  mapTargetForSearch,
} from "@/lib/areas";
import { fetchEvents, fetchHotspots } from "@/lib/api";
import type { Event, EventCategory, EventFilters, HotspotCluster, TimePreset } from "@/lib/types";

const EventMap = dynamic(() => import("@/components/EventMap").then((m) => m.EventMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-sm text-slate-400">
      Loading map…
    </div>
  ),
});

const TIME_PRESETS: { id: TimePreset; label: string }[] = [
  { id: "all", label: "All upcoming" },
  { id: "tonight", label: "Tonight" },
  { id: "weekend", label: "This weekend" },
];

export function HomePage() {
  const [filters, setFilters] = useState<EventFilters>({
    time: "all",
    categories: [],
    query: "",
    sort: "hotspot",
    limit: 150,
  });
  const [searchInput, setSearchInput] = useState("");
  const [events, setEvents] = useState<Event[]>([]);
  const [hotspots, setHotspots] = useState<HotspotCluster[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [wakingApi, setWakingApi] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setWakingApi(true);
    setError(null);
    try {
      const [data, hotspotData] = await Promise.all([
        fetchEvents(filters),
        fetchHotspots(filters),
      ]);
      setEvents(data.events);
      setHotspots(hotspotData.hotspots);
      setSelectedId((current) => {
        if (!data.events.length) return null;
        if (current && data.events.some((e) => e.id === current)) return current;
        return null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load events");
      setEvents([]);
      setHotspots([]);
    } finally {
      setLoading(false);
      setWakingApi(false);
    }
  }, [filters]);

  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  const applySearch = useCallback((value: string) => {
    const trimmed = value.trim();
    setSearchInput(trimmed);
    setFilters((prev) => ({ ...prev, query: trimmed }));
  }, []);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      const trimmed = searchInput.trim();
      setFilters((prev) => (prev.query === trimmed ? prev : { ...prev, query: trimmed }));
    }, 250);
    return () => window.clearTimeout(handle);
  }, [searchInput]);

  const matchedArea = useMemo(
    () => findAreaByQuery(filters.query) ?? (filters.query ? null : KORAMANGALA),
    [filters.query],
  );

  const mapTarget = useMemo(() => {
    if (!filters.query.trim()) {
      return {
        center: KORAMANGALA.center,
        zoom: KORAMANGALA.zoom,
        key: "default-koramangala",
      };
    }

    const target = mapTargetForSearch(filters.query, hotspots, events);
    return {
      center: target.center,
      zoom: target.area?.zoom ?? 12.8,
      key: `${filters.query}|${hotspots.length}|${events.length}|${target.center.join(",")}`,
    };
  }, [filters.query, hotspots, events]);

  const headerStats = useMemo(() => {
    if (filters.query) {
      return { count: events.length, areaLabel: matchedArea?.label ?? null };
    }
    return {
      count: eventsInArea(events, KORAMANGALA).length,
      areaLabel: KORAMANGALA.label,
    };
  }, [events, matchedArea, filters.query]);

  const toggleCategory = (category: EventCategory) => {
    setFilters((prev) => {
      const exists = prev.categories.includes(category);
      return {
        ...prev,
        categories: exists
          ? prev.categories.filter((c) => c !== category)
          : [...prev.categories, category],
      };
    });
  };

  return (
    <div className="flex min-h-screen flex-col bg-[#0b0f14] text-slate-100 lg:h-screen lg:overflow-hidden">
      <header className="flex shrink-0 items-center justify-between border-b border-white/10 px-4 py-3 md:px-6">
        <div>
          <h1 className="text-lg font-bold tracking-tight text-white md:text-xl">
            blr-hotspots
          </h1>
          <p className="text-xs text-slate-400">
            What&apos;s happening in Bangalore · data via{" "}
            <a
              href="https://blr.today"
              target="_blank"
              rel="noopener noreferrer"
              className="text-amber-400/90 hover:text-amber-300"
            >
              blr.today
            </a>
          </p>
        </div>
        <div className="text-right text-xs text-slate-500">
          {loading ? (
            "Loading…"
          ) : (
            <>
              <span className="text-amber-400/90">
                {headerStats.count} {filters.query ? "matches" : `in ${headerStats.areaLabel}`}
              </span>
              {filters.query && headerStats.areaLabel && (
                <>
                  <span className="text-slate-600"> · </span>
                  <span className="text-slate-400">{headerStats.areaLabel}</span>
                </>
              )}
              <span className="text-slate-600"> · </span>
              {events.length} on map
            </>
          )}
        </div>
      </header>

      <div className="flex flex-1 flex-col lg:grid lg:min-h-0 lg:grid-cols-[380px_1fr] lg:grid-rows-[auto_1fr] lg:overflow-hidden">
        <div className="space-y-3 border-b border-white/10 p-4 lg:col-start-1 lg:row-start-1 lg:border-r">
          <div className="flex flex-wrap gap-2">
            {TIME_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => setFilters((p) => ({ ...p, time: preset.id }))}
                className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                  filters.time === preset.id
                    ? "bg-amber-400 text-slate-900"
                    : "bg-white/10 text-slate-300 hover:bg-white/15"
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>

            <SearchBox
              value={searchInput}
              onChange={setSearchInput}
              onSubmit={applySearch}
            />

            <div className="flex flex-wrap gap-1.5">
              {ALL_CATEGORIES.map((category) => {
              const active = filters.categories.includes(category);
              const meta = CATEGORY_META[category];
              return (
                <button
                  key={category}
                  type="button"
                  onClick={() => toggleCategory(category)}
                  className={`rounded-full px-2.5 py-1 text-[11px] transition ${
                    active
                      ? "bg-white text-slate-900"
                      : "bg-white/5 text-slate-400 hover:bg-white/10"
                  }`}
                >
                  {meta.emoji} {meta.label}
                </button>
              );
            })}
          </div>
        </div>

        <main className="relative h-[42vh] min-h-[280px] shrink-0 bg-[#0b0f14] p-2 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:h-auto lg:min-h-0 lg:p-3">
          {wakingApi && (
            <div className="pointer-events-none absolute inset-2 z-10 flex items-center justify-center rounded-2xl bg-[#0b0f14]/80 backdrop-blur-sm lg:inset-3">
              <p className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300">
                Waking up API… cluster counts load in a moment
              </p>
            </div>
          )}
          <EventMap
            events={events}
            hotspots={hotspots}
            selectedId={selectedId}
            mapTarget={mapTarget}
            onSelect={setSelectedId}
          />
        </main>

        <aside className="border-t border-white/10 p-3 lg:col-start-1 lg:row-start-2 lg:min-h-0 lg:overflow-y-auto lg:border-r lg:border-t-0">
          {error && (
            <div className="mb-3 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
              {error}
              <p className="mt-1 text-xs text-red-300/80">
                The API may be waking from sleep on Render free tier — try refreshing in a minute.
              </p>
            </div>
          )}

          {!error && !loading && events.length === 0 && (
            <p className="p-4 text-center text-sm text-slate-500">No events match these filters.</p>
          )}

          <div className="space-y-2">
            {events.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                selected={event.id === selectedId}
                onSelect={setSelectedId}
              />
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
