import { CATEGORY_META } from "@/lib/categories";
import type { HotspotCluster } from "@/lib/types";

export function hotspotsToGeoJson(hotspots: HotspotCluster[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: hotspots.map((hotspot) => {
      const color = CATEGORY_META[hotspot.top_category]?.color ?? CATEGORY_META.other.color;
      const radius = Math.min(34, 12 + hotspot.event_count * 2 + hotspot.score_peak * 10);

      return {
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [hotspot.lon, hotspot.lat],
        },
        properties: {
          id: hotspot.id,
          event_count: hotspot.event_count,
          score_sum: hotspot.score_sum,
          score_peak: hotspot.score_peak,
          top_category: hotspot.top_category,
          neighborhood: hotspot.neighborhood ?? "",
          sample_titles: hotspot.sample_titles.join(" · "),
          color,
          radius,
        },
      };
    }),
  };
}
