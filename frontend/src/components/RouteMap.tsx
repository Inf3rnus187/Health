import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useEffect, useRef } from 'react';

const TILES = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

export function RouteMap({ points }: { points: [number, number][] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || points.length === 0) return undefined;
    const map = L.map(el);
    L.tileLayer(TILES, { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(
      map,
    );
    const line = L.polyline(points as L.LatLngExpression[], {
      color: '#2563eb',
      weight: 3,
    }).addTo(map);
    map.fitBounds(line.getBounds(), { padding: [20, 20] });
    return () => {
      map.remove();
    };
  }, [points]);
  return <div ref={ref} className="route-map" />;
}
