import { categoryColor } from "@/lib/categories";
import { formatEventTime } from "@/lib/time";
import type { Event } from "@/lib/types";

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1).trim()}…`;
}

function plainText(value: string | null | undefined): string {
  if (!value) return "";
  let text = value.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  text = text.replace(/^highlights\s*/i, "");
  return text;
}

export type EventFeatureProps = {
  id: string;
  title: string;
  title_short: string;
  map_label: string;
  detail_label: string;
  category: string;
  color: string;
  hotspot_score: number;
  selected: number;
  radius: number;
  label_priority: number;
  label_show: number;
  label_anchor: string;
  start_label: string;
  venue: string;
  ticket_url: string;
};

type EventFeature = GeoJSON.Feature<GeoJSON.Point, EventFeatureProps>;

function venueGroupKey(lon: number, lat: number, venue: string): string {
  return `${lat.toFixed(4)}:${lon.toFixed(4)}:${venue.toLowerCase().trim()}`;
}

const DEFAULT_LABEL = { label_anchor: "top" };

/** Place label on the outward side of the dot relative to cluster center. */
function labelPlacementForAngle(angle: number) {
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);

  if (Math.abs(sin) >= Math.abs(cos)) {
    return { label_anchor: sin < 0 ? "bottom" : "top" };
  }
  return { label_anchor: cos > 0 ? "left" : "right" };
}

/** Fan out events at the same venue so dots and labels don't stack. */
function spreadOverlappingPoints(features: EventFeature[]): void {
  const groups = new Map<string, EventFeature[]>();

  for (const feature of features) {
    const [lon, lat] = feature.geometry.coordinates;
    const key = venueGroupKey(lon, lat, feature.properties.venue);
    const bucket = groups.get(key) ?? [];
    bucket.push(feature);
    groups.set(key, bucket);
  }

  for (const group of Array.from(groups.values())) {
    if (group.length < 2) continue;

    const [centerLon, centerLat] = group[0].geometry.coordinates;
    const count = group.length;
    const baseRadius = 0.00045 * (1 + Math.min(count - 1, 5) * 0.15);
    const lngScale = 1 / Math.cos((centerLat * Math.PI) / 180);

    group.forEach((feature, index) => {
      const angle = (2 * Math.PI * index) / count - Math.PI / 2;
      feature.geometry.coordinates = [
        centerLon + baseRadius * lngScale * Math.cos(angle),
        centerLat + baseRadius * Math.sin(angle),
      ];
      Object.assign(feature.properties, labelPlacementForAngle(angle));
    });
  }
}

export function eventsToGeoJson(
  events: Event[],
  selectedId: string | null,
): GeoJSON.FeatureCollection<GeoJSON.Point, EventFeatureProps> {
  const features: EventFeature[] = events
    .filter((e) => e.venue?.lat != null && e.venue?.lon != null)
    .map((e) => {
      const selected = e.id === selectedId;
      const radius = 6 + e.hotspot_score * 10 + (selected ? 4 : 0);
      const titleShort = truncate(e.title, 28);
      const startLabel = formatEventTime(e.start_at);
      const venue = e.venue?.name ?? "";
      const descShort = truncate(plainText(e.description), 55);

      // Keep labels short — venue is obvious from the map pin cluster
      const mapLabel = `${titleShort}\n${startLabel}`;
      const detailLabel = descShort ? `${mapLabel}\n${descShort}` : mapLabel;

      return {
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [e.venue!.lon!, e.venue!.lat!],
        },
        properties: {
          id: e.id,
          title: e.title,
          title_short: titleShort,
          map_label: mapLabel,
          detail_label: detailLabel,
          category: e.category,
          color: categoryColor(e.category),
          hotspot_score: e.hotspot_score,
          selected: selected ? 1 : 0,
          radius,
          label_priority: selected ? 10_000 : Math.round(e.hotspot_score * 1000),
          label_show: 0,
          ...DEFAULT_LABEL,
          start_label: startLabel,
          venue,
          ticket_url: e.ticket_url ?? "",
        },
      };
    });

  spreadOverlappingPoints(features);

  const labelCutoff = [...features]
    .sort((a, b) => b.properties.label_priority - a.properties.label_priority)
    .slice(0, 24)
    .at(-1)?.properties.label_priority;

  for (const feature of features) {
    const show =
      feature.properties.selected === 1 ||
      (labelCutoff != null && feature.properties.label_priority >= labelCutoff);
    feature.properties.label_show = show ? 1 : 0;
  }

  return { type: "FeatureCollection", features };
}
