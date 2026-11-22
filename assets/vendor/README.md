Vendored map dependencies (no runtime CDN required):

- Leaflet 1.9.4: https://leafletjs.com/ and https://unpkg.com/leaflet@1.9.4/dist/ (BSD-2-Clause, LICENSE included).
- Leaflet.markercluster 1.5.3: https://github.com/Leaflet/Leaflet.markercluster and https://unpkg.com/leaflet.markercluster@1.5.3/dist/ (MIT, LICENSE included).

Map tiles load only when B-5 opens, directly from https://tile.openstreetmap.org/{z}/{x}/{y}.png with visible OpenStreetMap attribution and ordinary browser caching/referrer behavior. No tile prefetch or offline download is provided.
Customer coordinates are precomputed static records; no public geocoding endpoint is queried as users search or use the website.

Coordinate credits: UK postcode coordinates are from Postcodes.io / ONS Postcode Directory under OS OpenData. Source licences and copyright notices: https://postcodes.io/docs/licences/ . Approximate postcode locations are explicitly labelled and full verified addresses are used for Google Maps directions.
