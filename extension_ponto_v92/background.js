const API_BASE = "http://127.0.0.1:17892";
const API_HEADER = "X-ALIYVO-Ponto";
const API_SECRET = "aliyvo-ponto-02292";

async function apiFetch(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 1400);
  try {
    const headers = Object.assign({}, options.headers || {}, {
      [API_HEADER]: API_SECRET,
      "Content-Type": "application/json"
    });
    const response = await fetch(API_BASE + path, {
      method: options.method || "GET",
      headers,
      body: options.body,
      cache: "no-store",
      signal: controller.signal
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || !message.type) return false;

  if (message.type === "ponto-status") {
    apiFetch("/status")
      .then(data => sendResponse({available:true, data}))
      .catch(() => sendResponse({available:false}));
    return true;
  }

  if (message.type === "ponto-confirm" || message.type === "ponto-missed") {
    const endpoint = message.type === "ponto-confirm" ? "/confirm" : "/missed";
    apiFetch(endpoint, {
      method:"POST",
      body:JSON.stringify({slot_id:String(message.slot_id || "")})
    })
      .then(data => sendResponse({available:true, data}))
      .catch(() => sendResponse({available:false}));
    return true;
  }

  return false;
});
