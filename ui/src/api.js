/** Talk to the FastAPI backend. Vite proxies /api to port 8000 in development. */

export async function fetchSystems() {
  const response = await fetch("/api/systems");
  if (!response.ok) {
    throw new Error(`Could not load systems (${response.status})`);
  }
  return response.json();
}

export async function runDiscovery() {
  const response = await fetch("/api/discover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ focus: "bss_oss_party_and_service" }),
  });
  if (!response.ok) {
    throw new Error(`Discovery failed (${response.status})`);
  }
  return response.json();
}
