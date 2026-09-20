import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useEffect, useRef } from 'react';

const env = import.meta.env as Record<string, string | undefined>;
const CARTO =
  'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';

interface Tiles {
  url: string;
  attrib: string;
}

function resolveTiles(): Tiles | null {
  if (env.VITE_TILE_URL) {
    if (env.VITE_TILE_URL === 'none') return null;
    return { url: env.VITE_TILE_URL, attrib: env.VITE_TILE_ATTRIB ?? '' };
  }
  if (env.VITE_MAP_KEY) {
    const key = env.VITE_MAP_KEY;
    return {
      url: `https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${key}`,
      attrib: '© MapTiler © OpenStreetMap',
    };
  }
  return { url: CARTO, attrib: '© OpenStreetMap · © CARTO' };
}

const TILES = resolveTiles();

function draw(el: HTMLDivElement, points: [number, number][]): () => void {
  const map = L.map(el);
  if (TILES) {
    L.tileLayer(TILES.url, {
      maxZoom: 19,
      subdomains: 'abc',
      attribution: TILES.attrib,
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
