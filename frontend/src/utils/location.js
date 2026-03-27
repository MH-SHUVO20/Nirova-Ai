// utils/location.js

export function getCurrentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation is not supported by your browser.'));
    } else {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            lat: position.coords.latitude,
            lon: position.coords.longitude,
          });
        },
        (error) => {
          reject(error);
        }
      );
    }
  });
}

export async function fetchNearbyHospitals({ lat, lon }) {
  // Using OpenStreetMap Nominatim API for demonstration (no API key required)
  const url = `https://nominatim.openstreetmap.org/search?format=json&q=hospital&limit=10&extratags=1&viewbox=${lon-0.1},${lat+0.1},${lon+0.1},${lat-0.1}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to fetch hospitals');
  return response.json();
}
