"use client";

import { categoryColor, CATEGORY_META } from "@/lib/categories";
import { formatEventTime } from "@/lib/time";
import type { Event } from "@/lib/types";

type Props = {
  event: Event;
  selected: boolean;
  onSelect: (id: string) => void;
};

export function EventCard({ event, selected, onSelect }: Props) {
  const meta = CATEGORY_META[event.category] ?? CATEGORY_META.other;
  const venue = event.venue?.name ?? "Venue TBD";
  const hood = event.venue?.neighborhood;

  return (
    <button
      type="button"
      onClick={() => onSelect(event.id)}
      className={`w-full rounded-xl border p-3 text-left transition ${
        selected
          ? "border-amber-400/60 bg-amber-400/10 shadow-lg shadow-amber-500/10"
          : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]"
      }`}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <span
          className="rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide"
          style={{
            backgroundColor: `${categoryColor(event.category)}22`,
            color: categoryColor(event.category),
          }}
        >
          {meta.emoji} {meta.label}
        </span>
        <span className="shrink-0 rounded-full bg-orange-500/20 px-2 py-0.5 text-[11px] font-semibold text-orange-300">
          {(event.hotspot_score * 100).toFixed(0)}° hot
        </span>
      </div>

      <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-white">
        {event.title}
      </h3>

      <p className="mt-1 text-xs text-slate-400">{formatEventTime(event.start_at)}</p>
      <p className="mt-1 line-clamp-1 text-xs text-slate-500">
        {venue}
        {hood ? ` · ${hood}` : ""}
      </p>

      {event.ticket_url && (
        <a
          href={event.ticket_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="mt-2 inline-block text-xs font-medium text-amber-400 hover:text-amber-300"
        >
          Get tickets →
        </a>
      )}
    </button>
  );
}
