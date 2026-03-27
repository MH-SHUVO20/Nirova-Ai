
import React, { useEffect, useState } from 'react'
import { getCurrentPosition, fetchNearbyHospitals } from '../utils/location'

const FALLBACK_HOSPITALS = [
  {
    name: 'Dhaka Medical College Hospital',
    address: 'Secretariat Road, Dhaka 1000',
    map: 'https://goo.gl/maps/6Qw6v8v8v8v8v8v8A',
  },
  {
    name: 'BSMMU (PG Hospital)',
    address: 'Shahbag, Dhaka 1000',
    map: 'https://goo.gl/maps/8v8v8v8v8v8v8v8v8',
  },
]

export default function EmergencyHospitals() {
  const [hospitals, setHospitals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [usedFallback, setUsedFallback] = useState(false)

  useEffect(() => {
    getCurrentPosition()
      .then(({ lat, lon }) => fetchNearbyHospitals({ lat, lon }))
      .then((results) => {
        setHospitals(results.map(h => ({
          name: h.display_name.split(',')[0],
          address: h.display_name,
          map: `https://www.google.com/maps/search/?api=1&query=${h.lat},${h.lon}`,
        })))
        setLoading(false)
      })
      .catch(() => {
        setHospitals(FALLBACK_HOSPITALS)
        setUsedFallback(true)
        setLoading(false)
        setError('Could not get your location. Showing default hospitals.')
      })
  }, [])

  return (
    <div className="card mt-6 border border-blue-500/20 bg-blue-500/5">
      <h3 className="text-white font-semibold mb-3">Nearby Emergency Hospitals</h3>
      {loading ? (
        <div className="text-slate-400 text-xs">Loading nearby hospitals...</div>
      ) : (
        <ul className="space-y-3">
          {hospitals.map((h, i) => (
            <li key={i} className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 border-b border-slate-700/30 pb-2 last:border-b-0">
              <div>
                <span className="text-white font-medium">{h.name}</span>
                <span className="block text-slate-400 text-xs">{h.address}</span>
              </div>
              <div className="flex gap-2">
                <a href={h.map} target="_blank" rel="noopener noreferrer" className="btn-outline text-xs">Directions</a>
              </div>
            </li>
          ))}
        </ul>
      )}
      {error && (
        <div className="text-red-400 text-xs mt-2">{error}</div>
      )}
      <p className="text-slate-400 text-xs mt-3">For more, search "hospital" in Google Maps or call 999 for ambulance.</p>
    </div>
  )
}
