import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useEffect, useRef } from 'react';

const env = import.meta.env as Record<string, string | undefined>;
const TILE_URL =
  env.VITE_TILE_URL ??
  'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
const TILE_ATTRIB = env.VITE_TILE_ATTRIB ?? '© OpenStreetMap · © CARTO';

function draw(el: HTMLDivElement, points: [number, number][]): () => void {
  const map = L.map(el);
  if (TILE_URL && TILE_URL !== 'none') {
    L.tileLayer(TILE_URL, {
      maxZoom: 19,
      subdomains: 'abc',
      attribution: TILE_ATTRIB,
    }).addTo(map);
  }
  const line = L.polyline(points as L.LatLngExpression[], {
    color: '#2563eb',
    weight: 3,
  }).addTo(map);
  map.fitBounds(line.getBounds(), { padding: [20, 20] });
  return () => map.remove();
}

export function RouteMap({ points }: { points: [number, number][] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || points.length === 0) return undefined;
    return draw(ref.current, points);
  }, [points]);
  return <div ref={ref} className="route-map" />;
}
