const API_BASE = "http://localhost:8484";

document.getElementById("lookup").addEventListener("click", async () => {
  const ns = document.getElementById("ns").value;
  const identifier = document.getElementById("identifier").value.trim();
  const resultEl = document.getElementById("result");
  resultEl.className = "";
  resultEl.textContent = "Loading...";

  const url = `${API_BASE}/public/v1/replacements?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(identifier)}`;

  try {
    const response = await fetch(url);
    const body = await response.json();
    if (!response.ok) {
      resultEl.className = "error";
      resultEl.textContent = `HTTP ${response.status}\n${JSON.stringify(body, null, 2)}`;
      return;
    }
    resultEl.textContent = JSON.stringify(body, null, 2);
  } catch (err) {
    resultEl.className = "error";
    resultEl.textContent = `Request failed: ${err.message}\n(Is the API reachable at ${API_BASE}? Check the api container's logs.)`;
  }
});
