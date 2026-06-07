export type MapArea = {
  id: string;
  label: string;
  center: [number, number]; // [lon, lat]
  zoom: number;
  radiusKm: number;
};

export type SearchSuggestion = {
  label: string;
  value: string;
  kind: "area" | "topic";
  area?: MapArea;
};

/** Static Bangalore areas — good enough for autocomplete without server indexing. */
export const BANGALORE_AREAS: MapArea[] = [
  { id: "koramangala", label: "Koramangala", center: [77.6245, 12.9352], zoom: 13, radiusKm: 2.5 },
  { id: "indiranagar", label: "Indiranagar", center: [77.6408, 12.9784], zoom: 13, radiusKm: 2.5 },
  { id: "hsr", label: "HSR Layout", center: [77.6389, 12.9116], zoom: 13, radiusKm: 2.5 },
  { id: "jayanagar", label: "Jayanagar", center: [77.5938, 12.925], zoom: 13, radiusKm: 2.5 },
  { id: "mg-road", label: "MG Road", center: [77.6063, 12.975], zoom: 13.2, radiusKm: 2 },
  { id: "malleshwaram", label: "Malleshwaram", center: [77.5647, 13.0035], zoom: 13, radiusKm: 2.5 },
  { id: "whitefield", label: "Whitefield", center: [77.75, 12.9698], zoom: 12.5, radiusKm: 3.5 },
  { id: "btm", label: "BTM Layout", center: [77.6101, 12.9166], zoom: 13, radiusKm: 2.5 },
  { id: "church-street", label: "Church Street", center: [77.6045, 12.9745], zoom: 14, radiusKm: 1.5 },
  { id: "electronic-city", label: "Electronic City", center: [77.6784, 12.8456], zoom: 12, radiusKm: 4 },
  { id: "hebbal", label: "Hebbal", center: [77.5971, 13.0358], zoom: 12.5, radiusKm: 3 },
  { id: "marathahalli", label: "Marathahalli", center: [77.6974, 12.9591], zoom: 12.5, radiusKm: 3 },
];

export const KORAMANGALA = BANGALORE_AREAS[0];

const TOPIC_SUGGESTIONS: SearchSuggestion[] = [
  { kind: "topic", label: "Comedy & standup", value: "comedy" },
  { kind: "topic", label: "Live music", value: "music" },
  { kind: "topic", label: "Workshops", value: "workshop" },
  { kind: "topic", label: "Tech meetups", value: "tech meetup" },
  { kind: "topic", label: "Open mic", value: "open mic" },
];

const AREA_ALIASES: Record<string, string> = {
  kormangala: "koramangala",
  koramangla: "koramangala",
  indira: "indiranagar",
  hsr: "hsr",
  "mg road": "mg-road",
  mgroad: "mg-road",
  brigade: "mg-road",
};

export function normalizeSearchTerm(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

export function findAreaByQuery(query: string): MapArea | null {
  const term = normalizeSearchTerm(query);
  if (!term) return null;

  const aliasId = AREA_ALIASES[term];
  if (aliasId) {
    return BANGALORE_AREAS.find((area) => area.id === aliasId) ?? null;
  }

  return (
    BANGALORE_AREAS.find((area) => {
      const id = area.id.replace(/-/g, " ");
      return (
        area.label.toLowerCase().includes(term) ||
        id.includes(term) ||
        term.includes(id) ||
        term.includes(area.label.toLowerCase())
      );
    }) ?? null
  );
}

export function getSearchSuggestions(input: string, limit = 7): SearchSuggestion[] {
  const term = normalizeSearchTerm(input);
  if (!term) return [];

  const areaMatches: SearchSuggestion[] = BANGALORE_AREAS.filter((area) => {
    const id = area.id.replace(/-/g, " ");
    return area.label.toLowerCase().includes(term) || id.includes(term);
  }).map((area) => ({
    kind: "area" as const,
    label: area.label,
    value: area.label,
    area,
  }));

  const topicMatches = TOPIC_SUGGESTIONS.filter(
    (item) =>
      item.label.toLowerCase().includes(term) || item.value.toLowerCase().includes(term),
  );

  return [...areaMatches, ...topicMatches].slice(0, limit);
}

export function centroidFromHotspots(
  hotspots: Array<{ lat: number; lon: number; event_count: number }>,
): [number, number] | null {
  if (!hotspots.length) return null;
  let sumLon = 0;
  let sumLat = 0;
  let weight = 0;
  for (const spot of hotspots) {
    const w = Math.max(1, spot.event_count);
    sumLon += spot.lon * w;
    sumLat += spot.lat * w;
    weight += w;
  }
  return [sumLon / weight, sumLat / weight];
}

export function mapTargetForSearch(
  query: string,
  hotspots: Array<{ lat: number; lon: number; event_count: number }>,
  events: Array<{ venue?: { lat?: number | null; lon?: number | null } | null }>,
): { center: [number, number]; zoom: number; area: MapArea | null } {
  const area = findAreaByQuery(query);
  if (area) {
    return { center: area.center, zoom: area.zoom, area };
  }

  const hotspotCenter = centroidFromHotspots(hotspots);
  if (hotspotCenter) {
    return { center: hotspotCenter, zoom: 12.8, area: null };
  }

  const coords = events
    .map((e) => e.venue)
    .filter((v): v is { lat: number; lon: number } => v?.lat != null && v?.lon != null)
    .map((v) => [v.lon!, v.lat!] as [number, number]);
  if (coords.length) {
    const lon = coords.reduce((s, c) => s + c[0], 0) / coords.length;
    const lat = coords.reduce((s, c) => s + c[1], 0) / coords.length;
    return { center: [lon, lat], zoom: 13, area: null };
  }

  return { center: KORAMANGALA.center, zoom: KORAMANGALA.zoom, area: null };
}

/** Rough haversine distance in km — fine for neighborhood filtering. */
export function distanceKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function eventsInArea<T extends { venue?: { lat?: number | null; lon?: number | null } | null }>(
  events: T[],
  area: MapArea,
): T[] {
  return events.filter((event) => {
    const lat = event.venue?.lat;
    const lon = event.venue?.lon;
    if (lat == null || lon == null) return false;
    return distanceKm(lat, lon, area.center[1], area.center[0]) <= area.radiusKm;
  });
}
