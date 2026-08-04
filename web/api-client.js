const RVI_API_BASE = `${window.location.protocol}//${window.location.hostname}:8484`;

async function rviFetch(path) {
  const url = `${RVI_API_BASE}${path}`;
  const start = performance.now();
  try {
    const response = await fetch(url);
    const elapsedMs = performance.now() - start;
    let body = null;
    try {
      body = await response.json();
    } catch (parseErr) {
      body = null;
    }
    return { ok: response.ok, status: response.status, body, elapsedMs, url };
  } catch (err) {
    const elapsedMs = performance.now() - start;
    return { ok: false, status: 0, body: null, error: err.message, elapsedMs, url };
  }
}
