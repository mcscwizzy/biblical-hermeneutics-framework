(function () {
  async function requestJson(url, options = {}, fallbackMessage = "Request failed.") {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || fallbackMessage);
    }
    return data;
  }

  async function requestText(url, options = {}, fallbackMessage = "Request failed.") {
    const response = await fetch(url, options);
    const data = await response.text();
    if (!response.ok) {
      throw new Error(data || fallbackMessage);
    }
    return data;
  }

  window.BHFApi = {
    requestJson,
    requestText,
  };
})();
