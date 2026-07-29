function usableCoordinate(value, min, max) {
  const number = Number(value);
  return Number.isFinite(number) && number >= min && number <= max;
}

function hasUsableCoordinates(item = {}) {
  return usableCoordinate(item.latitude, -90, 90) && usableCoordinate(item.longitude, -180, 180);
}

function buildGoogleEarthUrl(item = {}) {
  if (!hasUsableCoordinates(item)) {
    return "";
  }
  const latitude = Number(item.latitude).toFixed(6);
  const longitude = Number(item.longitude).toFixed(6);
  return `https://earth.google.com/web/@${latitude},${longitude},1200a,35y,0h,0t,0r`;
}

export { buildGoogleEarthUrl, hasUsableCoordinates };
