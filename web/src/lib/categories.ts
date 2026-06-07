import type { EventCategory } from "./types";

export const CATEGORY_META: Record<
  EventCategory,
  { label: string; color: string; emoji: string }
> = {
  music: { label: "Music", color: "#ec4899", emoji: "🎵" },
  comedy: { label: "Comedy", color: "#f59e0b", emoji: "🎤" },
  games: { label: "Games", color: "#06b6d4", emoji: "🎲" },
  workshop: { label: "Workshop", color: "#3b82f6", emoji: "🛠️" },
  sports: { label: "Sports", color: "#22c55e", emoji: "🏃" },
  food: { label: "Food", color: "#f97316", emoji: "🍽️" },
  art: { label: "Art", color: "#a855f7", emoji: "🎨" },
  party: { label: "Party", color: "#8b5cf6", emoji: "🪩" },
  tech: { label: "Tech", color: "#6366f1", emoji: "💻" },
  theater: { label: "Theater", color: "#ef4444", emoji: "🎭" },
  other: { label: "Other", color: "#94a3b8", emoji: "✨" },
};

export const ALL_CATEGORIES = Object.keys(CATEGORY_META) as EventCategory[];

export function categoryColor(category: EventCategory): string {
  return CATEGORY_META[category]?.color ?? CATEGORY_META.other.color;
}
