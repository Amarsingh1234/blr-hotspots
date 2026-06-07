export type EventCategory =
  | "music"
  | "comedy"
  | "games"
  | "workshop"
  | "sports"
  | "food"
  | "art"
  | "party"
  | "tech"
  | "theater"
  | "other";

export type TimePreset = "all" | "tonight" | "weekend";

export type Venue = {
  name: string;
  address?: string | null;
  lat?: number | null;
  lon?: number | null;
  neighborhood?: string | null;
};

export type Event = {
  id: string;
  title: string;
  start_at: string;
  end_at?: string | null;
  category: EventCategory;
  vibe_tags: string[];
  description?: string | null;
  image_url?: string | null;
  price_min?: number | null;
  price_max?: number | null;
  is_free: boolean;
  ticket_url?: string | null;
  hotspot_score: number;
  confidence: number;
  venue?: Venue | null;
  distance_km?: number | null;
};

export type EventsResponse = {
  count: number;
  events: Event[];
};

export type HotspotCluster = {
  id: string;
  lat: number;
  lon: number;
  event_count: number;
  score_sum: number;
  score_peak: number;
  top_category: EventCategory;
  neighborhood?: string | null;
  sample_titles: string[];
};

export type HotspotsResponse = {
  count: number;
  hotspots: HotspotCluster[];
};

export type EventFilters = {
  time: TimePreset;
  categories: EventCategory[];
  query: string;
  sort: "hotspot" | "time" | "distance";
  limit: number;
};
