/**
 * Flight alerts list — tail number only (?aircraft_id=CALLSIGN).
 */
(function () {
  function qs(name) {
    return new URLSearchParams(window.location.search).get(name);
  }

  function esc(s) {
    if (s == null || s === "") return "";
    const d = document.createElement("div");
    d.textContent = String(s);
    return d.innerHTML;
  }

  function aircraftId() {
    return (qs("aircraft_id") || qs("aircraft") || "").trim().toUpperCase();
  }

  function setBanners(aid, err) {
    const bA = document.getElementById("banner-aircraft");
    const bE = document.getElementById("banner-error");
    bE.classList.add("d-none");
    bE.textContent = "";
    if (err) {
      bE.textContent = err;
      bE.classList.remove("d-none");
      bA.classList.add("d-none");
      return;
    }
    if (!aid) {
      bA.innerHTML =
        '<strong>No aircraft selected.</strong> Open this page from search or use <span class="mono">?aircraft_id=N12345</span> in the URL.';
      bA.classList.remove("d-none");
      return;
    }
    bA.innerHTML = `Showing alerts for <strong class="mono">${esc(aid)}</strong> (internal GUFI shown for reference only).`;
    bA.classList.remove("d-none");
  }

  function detailHref(aid) {
    return `/flight-detail.html?aircraft_id=${encodeURIComponent(aid)}`;
  }

  async function loadAlerts() {
    const aid = aircraftId();
    const ack = document.getElementById("filter-ack").value;
    const linkDetail = document.getElementById("link-detail");
    linkDetail.href = aid ? detailHref(aid) : "/";

    setBanners(aid, null);
    const tbody = document.getElementById("alerts-body");
    if (!aid) {
      tbody.innerHTML =
        '<tr><td colspan="5" class="text-secondary">Provide aircraft_id in the URL.</td></tr>';
      return;
    }

    tbody.innerHTML =
      '<tr><td colspan="5" class="text-secondary">Loading…</td></tr>';
    const params = new URLSearchParams({ limit: "100", offset: "0" });
    if (ack !== "") params.set("acknowledged", ack);
    const url = `/api/flights/${encodeURIComponent(aid)}/alerts?${params}`;
    try {
      const res = await fetch(url);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.error || data.details || `HTTP ${res.status}`);
      }
      const rows = data.alerts || [];
      if (!rows.length) {
        tbody.innerHTML =
          '<tr><td colspan="5" class="text-secondary">No alerts for this aircraft with the current filter.</td></tr>';
        return;
      }
      tbody.innerHTML = rows
        .map(function (r) {
          const acked = r.acknowledged ? "Yes" : "No";
          return `<tr>
            <td class="text-nowrap">${esc(r.created_at || "")}</td>
            <td><span class="mono">${esc(r.alert_type || "")}</span></td>
            <td>${esc(r.message || "")}</td>
            <td class="mono">${esc(r.gufi || "")}</td>
            <td>${esc(acked)}</td>
          </tr>`;
        })
        .join("");
    } catch (e) {
      console.error(e);
      tbody.innerHTML = "";
      setBanners(aid, e.message || String(e));
    }
  }

  document.getElementById("btn-reload").addEventListener("click", loadAlerts);
  document.getElementById("filter-ack").addEventListener("change", loadAlerts);
  loadAlerts();
})();
