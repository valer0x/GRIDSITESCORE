import { MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet";
import L from "leaflet";
import FeaturesLayer from "./FeaturesLayer";
import HeatmapControl from "./HeatmapControl";

// Fix the broken default icon paths under bundlers.
const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});
L.Marker.prototype.options.icon = defaultIcon;

interface Props {
  point: { lat: number; lng: number } | null;
  onPick: (lat: number, lng: number) => void;
}

function ClickCapture({ onPick }: { onPick: Props["onPick"] }) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export default function MapView({ point, onPick }: Props) {
  return (
    <MapContainer
      center={[42.5, 12.5]}
      zoom={6}
      style={{ height: "100%", width: "100%" }}
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <HeatmapControl />
      <FeaturesLayer />
      <ClickCapture onPick={onPick} />
      {point && <Marker position={[point.lat, point.lng]} />}
    </MapContainer>
  );
}
