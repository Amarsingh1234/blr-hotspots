"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EventCard } from "@/components/EventCard";
import { ALL_CATEGORIES, CATEGORY_META } from "@/lib/categories";
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
    sort: "hotspot",
    limit: 150,
  });
  const [events, setEvents] = useState<Event[]>([]);
  const [hotspots, setHotspots] = useState<HotspotCluster[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = useCallback(async () => {
    setLoading(true);
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
        return data.events[0].id;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load events");
      setEvents([]);
      setHotspots([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  const mappableCount = useMemo(
    () => events.filter((e) => e.venue?.lat != null && e.venue?.lon != null).length,
    [events],
  );

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
    <div className="flex h-screen flex-col bg-[#0b0f14] text-slate-100">
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
          {loading ? "Loading…" : `${events.length} events · ${mappableCount} on map`}
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside className="flex w-full shrink-0 flex-col border-b border-white/10 lg:w-[380px] lg:border-b-0 lg:border-r">
          <div className="space-y-3 border-b border-white/10 p-4">
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

          <div className="min-h-0 flex-1 overflow-y-auto p-3">
            {error && (
              <div className="mb-3 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
                {error}
                <p className="mt-1 text-xs text-red-300/80">
                  Make sure the API is running: <code>make serve</code> (port 8001)
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
          </div>
        </aside>

        <main className="relative min-h-[320px] flex-1 bg-[#0b0f14] p-2 lg:p-3">
          <EventMap
            events={events}
            hotspots={hotspots}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </main>
      </div>
    </div>
  );
}
