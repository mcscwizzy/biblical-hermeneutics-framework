function usableCoordinate(value, min, max) {
  const number = Number(value);
  return Number.isFinite(number) && number >= min && number <= max;
}

function getMapCoordinates(item = {}) {
  const latitude = Number(item.latitude ?? item.lat);
  const longitude = Number(item.longitude ?? item.lng);
  if (!usableCoordinate(latitude, -90, 90) || !usableCoordinate(longitude, -180, 180)) {
    return null;
  }
  return { latitude, longitude };
}

function hasUsableCoordinates(item = {}) {
  return Boolean(getMapCoordinates(item));
}

function buildGoogleEarthUrl(item = {}) {
  const coordinates = getMapCoordinates(item);
  if (!coordinates) {
    return "";
  }
  const latitude = coordinates.latitude.toFixed(6);
  const longitude = coordinates.longitude.toFixed(6);
  return `https://earth.google.com/web/@${latitude},${longitude},1200a,35y,0h,0t,0r`;
}

export { buildGoogleEarthUrl, getMapCoordinates, hasUsableCoordinates };
