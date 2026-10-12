import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Search, LocateFixed, Check } from 'lucide-react';
import { api } from './api.js';

const validPin = (lat, lng) => lat !== '' && lng !== '' && lat != null && lng != null
  && Number.isFinite(Number(lat)) && Number.isFinite(Number(lng))
  && Math.abs(Number(lat)) <= 90 && Math.abs(Number(lng)) <= 180
  && !(Number(lat) === 0 && Number(lng) === 0);

function addressDetails(place) {
  const address = place.address || {};
  return {
    address: [address.house_number, address.road].filter(Boolean).join(' ') || place.display_name || '',
    area: address.neighbourhood || address.suburb || address.quarter || address.village || '',
    city: address.city || address.town || address.municipality || address.village || address.county || '',
    state: address.state || '', country: address.country || '', pincode: address.postcode || '',
  };
}

export default function MapCoordinatePicker({ latitude, longitude, onChange, onDetails, onConfirmedChange, token, radiusKm = 0 }) {
  const elementRef = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const circleRef = useRef(null);
  const previousRadius = useRef(null);
  const callbacks = useRef({ onChange, onDetails, onConfirmedChange });
  callbacks.current = { onChange, onDetails, onConfirmedChange };
  const coordsRef = useRef({ latitude, longitude });
  coordsRef.current = { latitude, longitude };
  const selectionKey = useRef(null);
  const requestSequence = useRef(0);
  const mounted = useRef(true);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [confirmed, setConfirmed] = useState(validPin(latitude, longitude));

  const selectPin = (lat, lng) => {
    const next = { latitude: Number(Number(lat).toFixed(7)), longitude: Number(Number(lng).toFixed(7)) };
    selectionKey.current = `${next.latitude},${next.longitude}`;
    requestSequence.current += 1;
    setBusy('');
    coordsRef.current = next;
    setConfirmed(false);
    callbacks.current.onConfirmedChange?.(false);
    setMessage('Review the pin, then confirm it to fill the address.');
    callbacks.current.onDetails?.({ address: '', city: '', state: '', area: '', pincode: '' });
    callbacks.current.onChange(next);
    return next;
  };

  useEffect(() => {
    mounted.current = true;
    const initialPin = validPin(latitude, longitude);
    const map = L.map(elementRef.current, { scrollWheelZoom: false }).setView(initialPin ? [Number(latitude), Number(longitude)] : [20.5937, 78.9629], initialPin ? 13 : 5);
    mapRef.current = map;
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(map);
    map.on('click', (event) => selectPin(event.latlng.lat, event.latlng.lng));
    const resizeObserver = new ResizeObserver(() => map.invalidateSize());
    resizeObserver.observe(elementRef.current);
    return () => {
      mounted.current = false;
      requestSequence.current += 1;
      resizeObserver.disconnect();
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
      circleRef.current = null;
      previousRadius.current = null;
    };
  }, []);

  useEffect(() => {
    const hasPin = validPin(latitude, longitude);
    const key = `${Number(latitude)},${Number(longitude)}`;
    if (selectionKey.current !== key) setConfirmed(hasPin);
    const map = mapRef.current;
    if (!map) return;
    if (!hasPin) {
      markerRef.current?.remove(); markerRef.current = null;
      circleRef.current?.remove(); circleRef.current = null;
      return;
    }
    const position = L.latLng(Number(latitude), Number(longitude));
    if (!markerRef.current) {
      const icon = L.divIcon({ className: 'location-pin', html: '<span aria-hidden="true">●</span>', iconSize: [28, 28], iconAnchor: [14, 14] });
      const marker = L.marker(position, { draggable: true, icon, title: 'Drag to set your exact location', alt: 'Selected location pin' }).addTo(map);
      marker.on('dragend', () => { const point = marker.getLatLng(); selectPin(point.lat, point.lng); });
      markerRef.current = marker;
      map.setView(position, 13);
    } else {
      markerRef.current.setLatLng(position);
      if (!map.getBounds().contains(position)) map.panTo(position);
    }
    if (Number(radiusKm) > 0) {
      if (!circleRef.current) circleRef.current = L.circle(position, { color: '#2563eb', fillOpacity: 0.12, interactive: false }).addTo(map);
      circleRef.current.setLatLng(position).setRadius(Number(radiusKm) * 1000);
      if (previousRadius.current !== Number(radiusKm)) map.fitBounds(circleRef.current.getBounds(), { padding: [20, 20], maxZoom: 14 });
      previousRadius.current = Number(radiusKm);
    } else {
      circleRef.current?.remove(); circleRef.current = null;
      previousRadius.current = null;
    }
  }, [latitude, longitude, radiusKm]);

  useEffect(() => { callbacks.current.onConfirmedChange?.(confirmed); }, [confirmed]);

  const searchLocation = async () => {
    if (query.trim().length < 3) { setMessage('Enter at least 3 characters: a city, area, address or pincode.'); return; }
    const sequence = ++requestSequence.current;
    setBusy('Searching'); setMessage(''); setResults([]);
    try {
      const places = await api.searchLocations(token, query.trim());
      if (!mounted.current || sequence !== requestSequence.current) return;
      setResults(places);
      if (!places.length) setMessage('No places found. Try a nearby city, area or pincode.');
    } catch { if (mounted.current && sequence === requestSequence.current) setMessage('Search is unavailable. Use your current location or drop a pin and enter the address.'); }
    finally { if (mounted.current && sequence === requestSequence.current) setBusy(''); }
  };

  const confirmPin = async (point = coordsRef.current) => {
    if (!validPin(point.latitude, point.longitude)) { setMessage('Choose a location on the map first.'); return; }
    const sequence = ++requestSequence.current;
    setBusy('Finding address');
    try {
      const place = await api.reverseLocation(token, point.latitude, point.longitude);
      if (!mounted.current || sequence !== requestSequence.current) return;
      callbacks.current.onDetails?.(addressDetails(place));
      setConfirmed(true); setMessage('Pin confirmed. Check the address before saving.');
    } catch {
      if (mounted.current && sequence === requestSequence.current) {
        setConfirmed(true); setMessage('Pin confirmed. Address lookup is unavailable; enter your city, state and street address manually.');
      }
    } finally { if (mounted.current && sequence === requestSequence.current) setBusy(''); }
  };

  const useCurrentLocation = () => {
    if (!window.isSecureContext || !navigator.geolocation) { setMessage('Browser location needs HTTPS or localhost. You can also search or drop a pin.'); return; }
    const sequence = ++requestSequence.current;
    setBusy('Locating'); setMessage('Allow location access in your browser when prompted.');
    navigator.geolocation.getCurrentPosition((position) => {
      if (!mounted.current || sequence !== requestSequence.current) return;
      const point = selectPin(position.coords.latitude, position.coords.longitude);
      mapRef.current?.setView([point.latitude, point.longitude], 16);
      confirmPin(point);
    }, (error) => {
      if (!mounted.current || sequence !== requestSequence.current) return;
      setBusy('');
      setMessage(error.code === 1 ? 'Location permission was denied. Allow it in browser settings, or search for your address.' : 'Could not find your current location. Try again or search for your address.');
    }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
  };

  return <div className="location-picker">
    <div className="location-search-row">
      <label className="location-search-input">Search address, area or pincode<input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); searchLocation(); } }} placeholder="e.g. Indiranagar, Bengaluru or 560038" /></label>
      <button type="button" disabled={Boolean(busy)} onClick={searchLocation}><Search size={16} /> Search</button>
      <button type="button" disabled={Boolean(busy)} onClick={useCurrentLocation}><LocateFixed size={16} /> Use my location</button>
    </div>
    {results.length > 0 && <div className="location-results" aria-label="Location search results">{results.map((place, index) => <button type="button" key={place.place_id || index} onClick={() => {
      const point = selectPin(place.lat, place.lon);
      callbacks.current.onDetails?.(addressDetails(place));
      mapRef.current?.setView([point.latitude, point.longitude], 16);
      setResults([]); setQuery(place.display_name || query);
    }}><MapPin size={18} /><span>{place.display_name}</span></button>)}</div>}
    <p className="location-help">Search or use your location, then drag the pin or tap the map to adjust it. {radiusKm > 0 ? `The blue circle covers ${radiusKm} km from your shop.` : ''}</p>
    <div ref={elementRef} className="location-map" aria-label="Location map" />
    <div className="location-confirm-row">
      <span role="status" aria-live="polite">{busy ? `${busy}…` : message || (confirmed ? 'Your saved location is pinned.' : 'Choose and confirm your exact pin.')}</span>
      <button type="button" className="primary" disabled={Boolean(busy) || !validPin(latitude, longitude)} onClick={() => confirmPin()}><Check size={16} /> Confirm Pin</button>
    </div>
    <details className="coordinate-details"><summary>Enter coordinates manually</summary><div className="split-inputs">
      <label>Latitude<input type="number" step="0.0000001" value={latitude ?? ''} onChange={(event) => { selectPin(event.target.value, longitude); if (event.target.value === '') onChange({ latitude: '', longitude }); }} /></label>
      <label>Longitude<input type="number" step="0.0000001" value={longitude ?? ''} onChange={(event) => { selectPin(latitude, event.target.value); if (event.target.value === '') onChange({ latitude, longitude: '' }); }} /></label>
    </div></details>
  </div>;
}
