"use client";

import { memo, useEffect, useMemo, useRef } from "react";

import { KORAMANGALA } from "@/lib/areas";
import { eventsToGeoJson } from "@/lib/eventGeoJson";
import { hotspotsToGeoJson } from "@/lib/hotspotGeoJson";
import type { Event, HotspotCluster } from "@/lib/types";

const CLUSTER_MAX_ZOOM = 15;
const EVENTS_MIN_ZOOM = 15;
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

// MapLibre data expressions — maplibre-gl layout types are narrower than runtime.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const LABEL_ANCHOR: any = [
  "match",
  ["get", "label_anchor"],
  "top",
  "top",
  "bottom",
  "bottom",
  "left",
  "left",
  "right",
  "right",
  "top",
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const LABEL_OFFSET: any = [
  "match",
  ["get", "label_anchor"],
  "top",
  ["literal", [0, 1.15]],
  "bottom",
  ["literal", [0, -1.2]],
  "left",
  ["literal", [1.2, 0]],
  "right",
  ["literal", [-1.2, 0]],
  ["literal", [0, 1.15]],
];

type MapTarget = {
  center: [number, number];
  zoom: number;
  key: string;
};

type Props = {
  events: Event[];
  hotspots: HotspotCluster[];
  selectedId: string | null;
  mapTarget: MapTarget;
  onSelect: (id: string) => void;
};

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function popupHtml(props: {
  title: string;
  start_label: string;
  venue: string;
  ticket_url: string;
}): string {
  const ticket = props.ticket_url
    ? `<a href="${escapeHtml(props.ticket_url)}" target="_blank" rel="noopener noreferrer"
         style="display:inline-block;margin-top:8px;font-size:12px;color:#2563eb;">Tickets</a>`
    : "";

  return `<div style="font-size:14px;color:#0f172a;min-width:180px;">
    <p style="font-weight:600;margin:0;">${escapeHtml(props.title)}</p>
    <p style="margin:4px 0 0;font-size:12px;color:#475569;">${escapeHtml(props.start_label)}</p>
    <p style="margin:4px 0 0;font-size:12px;color:#64748b;">${escapeHtml(props.venue)}</p>
    ${ticket}
  </div>`;
}

// MapLibre is browser-only — loaded dynamically to avoid SSR issues
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type MapInstance = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PopupInstance = any;

function hoverPopupHtml(props: { title: string; start_label: string }): string {
  return `<div style="font-size:12px;color:#0f172a;max-width:200px;">
    <p style="font-weight:600;margin:0;line-height:1.3;">${escapeHtml(props.title)}</p>
    <p style="margin:3px 0 0;font-size:11px;color:#64748b;">${escapeHtml(props.start_label)}</p>
  </div>`;
}

function hotspotPopupHtml(props: {
  event_count: number;
  neighborhood: string;
  sample_titles: string;
}): string {
  const hood = props.neighborhood
    ? `<p style="margin:4px 0 0;font-size:12px;color:#64748b;">${escapeHtml(props.neighborhood)}</p>`
    : "";
  const titles = props.sample_titles
    ? `<p style="margin:6px 0 0;font-size:12px;color:#475569;">${escapeHtml(props.sample_titles)}</p>`
    : "";

  return `<div style="font-size:14px;color:#0f172a;min-width:180px;">
    <p style="font-weight:600;margin:0;">${props.event_count} events nearby</p>
    ${hood}
    ${titles}
    <p style="margin:8px 0 0;font-size:11px;color:#94a3b8;">Zoom in to see individual events</p>
  </div>`;
}

function EventMapInner({ events, hotspots, selectedId, mapTarget, onSelect }: Props) {
  const shellRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const popupRef = useRef<PopupInstance | null>(null);
  const hoverPopupRef = useRef<PopupInstance | null>(null);
  const onSelectRef = useRef(onSelect);
  const lastFlownRef = useRef<string | null>(null);
  const lastMapTargetRef = useRef<string | null>(null);
  const readyRef = useRef(false);
  const observerRef = useRef<ResizeObserver | null>(null);

  const geojson = useMemo(
    () => eventsToGeoJson(events, selectedId),
    [events, selectedId],
  );

  const hotspotsGeojson = useMemo(() => hotspotsToGeoJson(hotspots), [hotspots]);

  onSelectRef.current = onSelect;

  // Init MapLibre once.
  useEffect(() => {
    const el = containerRef.current;
    if (!el || mapRef.current) return;

    let cancelled = false;

    void (async () => {
      const maplibregl = (await import("maplibre-gl")).default;
      if (cancelled) return;

      const map = new maplibregl.Map({
        container: el,
        style: MAP_STYLE,
        center: KORAMANGALA.center,
        zoom: KORAMANGALA.zoom,
        fadeDuration: 0,
      });

      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");

      map.on("load", () => {
        readyRef.current = true;

        map.addSource("hotspots", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });

        map.addSource("events", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });

        map.addLayer({
          id: "hotspots-glow",
          type: "circle",
          source: "hotspots",
          maxzoom: CLUSTER_MAX_ZOOM,
          paint: {
            "circle-radius": ["+", ["get", "radius"], 10],
            "circle-color": ["get", "color"],
            "circle-opacity": 0.18,
            "circle-blur": 0.9,
          },
        });

        map.addLayer({
          id: "hotspots-circles",
          type: "circle",
          source: "hotspots",
          maxzoom: CLUSTER_MAX_ZOOM,
          paint: {
            "circle-radius": ["get", "radius"],
            "circle-color": ["get", "color"],
            "circle-opacity": 0.55,
            "circle-stroke-width": +2,
            "circle-stroke-color": "#f8fafc",
            "circle-stroke-opacity": 0.35,
          },
        });

        map.addLayer({
          id: "hotspots-labels",
          type: "symbol",
          source: "hotspots",
          maxzoom: CLUSTER_MAX_ZOOM,
          layout: {
            "text-field": [
              "case",
              ["!=", ["get", "neighborhood"], ""],
              [
                "format",
                ["to-string", ["get", "event_count"]],
                { "font-scale": 1.1 },
                "\n",
                {},
                ["get", "neighborhood"],
                { "font-scale": 0.8 },
              ],
              ["to-string", ["get", "event_count"]],
            ],
            "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
            "text-size": 11,
            "text-anchor": "center",
            "text-allow-overlap": true,
          },
          paint: {
            "text-color": "#f8fafc",
            "text-halo-color": "#0b0f14",
            "text-halo-width": 1.5,
          },
        });

        map.addLayer({
          id: "events-glow",
          type: "circle",
          source: "events",
          minzoom: EVENTS_MIN_ZOOM,
          paint: {
            "circle-radius": ["+", ["get", "radius"], 6],
            "circle-color": ["get", "color"],
            "circle-opacity": 0.15,
            "circle-blur": 0.8,
          },
        });

        map.addLayer({
          id: "events-circles",
          type: "circle",
          source: "events",
          minzoom: EVENTS_MIN_ZOOM,
          layout: {
            "circle-sort-key": ["get", "label_priority"],
          },
          paint: {
            "circle-radius": ["get", "radius"],
            "circle-color": ["get", "color"],
            "circle-opacity": 0.82,
            "circle-stroke-width": [
              "case",
              ["==", ["get", "selected"], 1],
              3,
              1.5,
            ],
            "circle-stroke-color": [
              "case",
              ["==", ["get", "selected"], 1],
              "#fbbf24",
              ["get", "color"],
            ],
          },
        });

        // Top hotspots only — MapLibre drops colliding labels (text-optional).
        map.addLayer({
          id: "events-labels",
          type: "symbol",
          source: "events",
          minzoom: 15,
          filter: [
            "all",
            ["==", ["get", "selected"], 0],
            ["==", ["get", "label_show"], 1],
          ],
          layout: {
            "text-field": ["get", "title_short"],
            "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
            "text-size": 10,
            "text-anchor": LABEL_ANCHOR,
            "text-offset": LABEL_OFFSET,
            "text-max-width": 9,
            "text-line-height": 1.2,
            "text-padding": 4,
            "text-allow-overlap": false,
            "text-optional": true,
            "symbol-sort-key": ["get", "label_priority"],
          },
          paint: {
            "text-color": "#e2e8f0",
            "text-halo-color": "#0b0f14",
            "text-halo-width": 1.5,
          },
        });

        // Selected event: label from street-level zoom
        map.addLayer({
          id: "events-labels-selected",
          type: "symbol",
          source: "events",
          minzoom: EVENTS_MIN_ZOOM,
          filter: ["==", ["get", "selected"], 1],
          layout: {
            "text-field": [
              "step",
              ["zoom"],
              ["get", "title_short"],
              15,
              ["get", "map_label"],
              16,
              ["get", "detail_label"],
            ],
            "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
            "text-size": 12,
            "text-anchor": LABEL_ANCHOR,
            "text-offset": LABEL_OFFSET,
            "text-max-width": 12,
            "text-line-height": 1.25,
            "text-padding": 4,
            "text-allow-overlap": true,
            "text-optional": false,
            "symbol-sort-key": 10_000,
          },
          paint: {
            "text-color": "#fbbf24",
            "text-halo-color": "#0b0f14",
            "text-halo-width": 2,
          },
        });

        const handleFeatureClick = (e: {
          features?: Array<{ geometry: GeoJSON.Geometry; properties: Record<string, unknown> }>;
        }) => {
          const feature = e.features?.[0];
          if (!feature?.geometry || feature.geometry.type !== "Point") return;

          const props = feature.properties;
          onSelectRef.current(String(props.id));

          popupRef.current?.remove();
          popupRef.current = new maplibregl.Popup({
            closeButton: false,
            offset: 12,
          })
            .setLngLat(feature.geometry.coordinates as [number, number])
            .setHTML(
              popupHtml({
                title: String(props.title),
                start_label: String(props.start_label),
                venue: String(props.venue),
                ticket_url: String(props.ticket_url ?? ""),
              }),
            )
            .addTo(map);
        };

        const handleHotspotClick = (e: {
          features?: Array<{ geometry: GeoJSON.Geometry; properties: Record<string, unknown> }>;
        }) => {
          const feature = e.features?.[0];
          if (!feature?.geometry || feature.geometry.type !== "Point") return;

          popupRef.current?.remove();
          const props = feature.properties;
          popupRef.current = new maplibregl.Popup({
            closeButton: false,
            offset: 12,
          })
            .setLngLat(feature.geometry.coordinates as [number, number])
            .setHTML(
              hotspotPopupHtml({
                event_count: Number(props.event_count),
                neighborhood: String(props.neighborhood ?? ""),
                sample_titles: String(props.sample_titles ?? ""),
              }),
            )
            .addTo(map);

          map.flyTo({
            center: feature.geometry.coordinates as [number, number],
            zoom: 15.5,
            duration: 700,
            essential: true,
          });
        };

        map.on("mouseenter", "events-circles", (e) => {
          map.getCanvas().style.cursor = "pointer";
          const feature = e.features?.[0];
          if (!feature?.geometry || feature.geometry.type !== "Point") return;

          const props = feature.properties;
          hoverPopupRef.current?.remove();
          hoverPopupRef.current = new maplibregl.Popup({
            closeButton: false,
            closeOnClick: false,
            offset: 10,
          })
            .setLngLat(feature.geometry.coordinates as [number, number])
            .setHTML(
              hoverPopupHtml({
                title: String(props.title),
                start_label: String(props.start_label),
              }),
            )
            .addTo(map);
        });

        map.on("mouseleave", "events-circles", () => {
          map.getCanvas().style.cursor = "";
          hoverPopupRef.current?.remove();
          hoverPopupRef.current = null;
        });

        const interactiveLayers = [
          "hotspots-circles",
          "hotspots-labels",
          "events-circles",
          "events-labels",
          "events-labels-selected",
        ];

        for (const layerId of interactiveLayers) {
          const handler =
            layerId.startsWith("hotspots-") ? handleHotspotClick : handleFeatureClick;
          map.on("click", layerId, handler);
          if (layerId !== "events-circles") {
            map.on("mouseenter", layerId, () => {
              map.getCanvas().style.cursor = "pointer";
            });
            map.on("mouseleave", layerId, () => {
              map.getCanvas().style.cursor = "";
            });
          }
        }
      });

      mapRef.current = map;

      const resize = () => map.resize();
      resize();
      requestAnimationFrame(resize);

      const observer = new ResizeObserver(resize);
      observerRef.current = observer;
      if (shellRef.current) observer.observe(shellRef.current);
    })();

    return () => {
      cancelled = true;
      readyRef.current = false;
      observerRef.current?.disconnect();
      observerRef.current = null;
      popupRef.current?.remove();
      hoverPopupRef.current?.remove();
      mapRef.current?.remove();
      mapRef.current = null;
      popupRef.current = null;
    };
  }, []);

  // Update markers without touching the basemap.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    map.getSource("events")?.setData(geojson);
    map.getSource("hotspots")?.setData(hotspotsGeojson);
  }, [geojson, hotspotsGeojson]);

  // Pan map when search/area changes — stay at cluster-friendly zoom.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current || mapTarget.key === lastMapTargetRef.current) return;

    lastMapTargetRef.current = mapTarget.key;
    lastFlownRef.current = null;

    const currentZoom = map.getZoom();
    const targetZoom =
      currentZoom >= EVENTS_MIN_ZOOM ? mapTarget.zoom : Math.max(currentZoom, mapTarget.zoom);

    map.flyTo({
      center: mapTarget.center,
      zoom: targetZoom,
      duration: 650,
      essential: true,
    });
  }, [mapTarget]);

  // Fly to selected event only when user picks from list or map.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current || !selectedId || selectedId === lastFlownRef.current) {
      return;
    }

    const feature = geojson.features.find((f) => f.properties?.id === selectedId);
    if (!feature || feature.geometry.type !== "Point") return;

    lastFlownRef.current = selectedId;
    map.flyTo({
      center: feature.geometry.coordinates as [number, number],
      zoom: 16,
      duration: 700,
      essential: true,
    });
  }, [selectedId, geojson]);

  return (
    <div
      ref={shellRef}
      className="blr-map-shell relative h-full min-h-[320px] w-full overflow-hidden rounded-2xl"
    >
      <div ref={containerRef} className="h-full w-full" />
      <p className="pointer-events-none absolute bottom-3 right-3 rounded-lg bg-black/50 px-2.5 py-1 text-[11px] text-slate-400 backdrop-blur-sm">
        Cluster counts while zooming · hover dots for name
      </p>
    </div>
  );
}

export const EventMap = memo(EventMapInner);
