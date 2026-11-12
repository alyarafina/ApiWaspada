/**
 * Modul Integrasi GIS dan Peta Interaktif menggunakan Leaflet.js & OpenStreetMap.
 * Mendukung:
 * - Peta pemilih koordinat laporan (klik peta, drag marker, atau GPS Geolocation)
 * - Peta persebaran laporan dengan marker berwarna berdasarkan status:
 *   Pending (#F59E0B), Verified (#2563EB), Rejected (#64748B), Completed (#16A34A)
 * - Layer Control (OpenStreetMap Standar & Peta Topografi/Humanitarian)
 * - Auto-fit bounds dan popup detail laporan
 */

const STATUS_MARKER_COLORS = {
  pending: "#F59E0B",
  verified: "#2563EB",
  rejected: "#64748B",
  completed: "#16A34A",
};

function createColoredPinIcon(colorHex) {
  const svgHtml = `
    <svg xmlns="http://www.w3.org/2000/svg" width="30" height="40" viewBox="0 0 30 40">
      <path d="M15 1C7.8 1 2 6.8 2 14C2 23.5 15 38 15 38C15 38 28 23.5 28 14C28 6.8 22.2 1 15 1Z"
            fill="${colorHex}" stroke="#FFFFFF" stroke-width="2.5"/>
      <circle cx="15" cy="14" r="5.5" fill="#FFFFFF"/>
    </svg>`;
  return L.divIcon({
    className: "custom-leaflet-pin",
    html: svgHtml,
    iconSize: [30, 40],
    iconAnchor: [15, 38],
    popupAnchor: [0, -34],
  });
}

function initBaseTileLayers(mapInstance) {
  const osmStandard = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }
  );
  const osmHot = L.tileLayer(
    "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
    {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors, Tiles style by Humanitarian OSM Team',
    }
  );
  osmStandard.addTo(mapInstance);
  L.control
    .layers(
      {
        "OpenStreetMap Standar": osmStandard,
        "OSM Humanitarian (Kontras Tinggi)": osmHot,
      },
      null,
      { position: "topright" }
    )
    .addTo(mapInstance);
}

function initReportPickerMap(containerId, onLocationSelected) {
  const cfg = window.APIWASPADA_CONFIG;
  const map = L.map(containerId).setView(
    [cfg.DEFAULT_LAT, cfg.DEFAULT_LNG],
    cfg.DEFAULT_ZOOM
  );
  initBaseTileLayers(map);

  let activeMarker = null;

  function setPickerCoordinate(lat, lng, panMap = true) {
    const cleanLat = Number(parseFloat(lat).toFixed(6));
    const cleanLng = Number(parseFloat(lng).toFixed(6));
    if (isNaN(cleanLat) || isNaN(cleanLng)) return;

    if (!activeMarker) {
      activeMarker = L.marker([cleanLat, cleanLng], {
        draggable: true,
        icon: createColoredPinIcon("#DC2626"),
      }).addTo(map);

      activeMarker.on("dragend", function (ev) {
        const pos = ev.target.getLatLng();
        if (typeof onLocationSelected === "function") {
          onLocationSelected(
            Number(pos.lat.toFixed(6)),
            Number(pos.lng.toFixed(6))
          );
        }
      });
    } else {
      activeMarker.setLatLng([cleanLat, cleanLng]);
    }

    activeMarker
      .bindPopup(
        `<strong>Lokasi Kejadian</strong><br>Lat: ${cleanLat}<br>Lng: ${cleanLng}`
      )
      .openPopup();

    if (panMap) {
      map.setView([cleanLat, cleanLng], Math.max(map.getZoom(), 15));
    }
    if (typeof onLocationSelected === "function") {
      onLocationSelected(cleanLat, cleanLng);
    }
  }

  map.on("click", function (e) {
    setPickerCoordinate(e.latlng.lat, e.latlng.lng, false);
  });

  return {
    map,
    setPickerCoordinate,
  };
}

function renderReportsDistributionMap(mapInstance, markersGroup, markersData, isOfficerView = false) {
  markersGroup.clearLayers();
  const bounds = [];

  (markersData || []).forEach((item) => {
    const statusKey = String(item.status || "pending").toLowerCase();
    const color = STATUS_MARKER_COLORS[statusKey] || "#DC2626";
    const marker = L.marker([item.latitude, item.longitude], {
      icon: createColoredPinIcon(color),
    });

    const detailUrl = isOfficerView
      ? `/report-detail.html?id=${encodeURIComponent(item.id)}`
      : `/tracking.html?code=${encodeURIComponent(item.tracking_code)}`;

    const popupContent = `
      <div style="min-width:220px; font-family:Inter, sans-serif; font-size:13px; line-height:1.45;">
        <div style="font-weight:800; color:#0F172A; margin-bottom:4px;">
          #${item.id} &bull; ${window.ApiWaspadaUtils.escapeHtml(item.tracking_code)}
        </div>
        <div style="color:#64748B; font-size:11.5px; margin-bottom:6px;">
          ${window.ApiWaspadaUtils.formatDateTimeWIB(item.created_at)}
        </div>
        <div style="margin-bottom:6px;">
          <strong>Indikasi AI:</strong><br/>
          ${window.ApiWaspadaUtils.escapeHtml(item.detection_result)}
          (${(Number(item.detection_confidence || 0) * 100).toFixed(1)}%)
        </div>
        <div style="margin-bottom:8px;">
          ${window.ApiWaspadaUtils.getStatusBadgeHtml(item.status)}
        </div>
        <a href="${detailUrl}" style="display:inline-block; font-weight:700; color:#DC2626; text-decoration:underline;">
          Lihat Detail Laporan &rarr;
        </a>
      </div>
    `;

    marker.bindPopup(popupContent);
    markersGroup.addLayer(marker);
    bounds.push([item.latitude, item.longitude]);
  });

  if (bounds.length > 0) {
    mapInstance.fitBounds(bounds, { padding: [36, 36], maxZoom: 15 });
  }
}

window.ApiWaspadaMap = {
  STATUS_MARKER_COLORS,
  createColoredPinIcon,
  initBaseTileLayers,
  initReportPickerMap,
  renderReportsDistributionMap,
};
