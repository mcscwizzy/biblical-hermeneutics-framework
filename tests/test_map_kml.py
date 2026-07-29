import unittest

from bhf_web.services.map_kml import journey_kml, place_kml, route_kml


class MapKmlTests(unittest.TestCase):
    def test_place_kml_escapes_names_and_includes_coordinates(self):
        document = place_kml(
            {
                "id": "test-place",
                "name": "A <place> & place",
                "description": "A curated place",
                "modern_location": "Modern town",
                "latitude": 31.778,
                "longitude": 35.235,
                "related_references": [{"reference": "John 19:20"}],
            }
        )

        self.assertIn('<?xml version="1.0" encoding="UTF-8"?>', document)
        self.assertIn("A &lt;place&gt; &amp; place", document)
        self.assertIn("35.235000,31.778000,0", document)
        self.assertIn("John 19:20", document)

    def test_route_kml_serializes_line_geometry_and_escapes_description(self):
        document = route_kml(
            {
                "name": "Paul & Barnabas",
                "description": "A <simplified> route",
                "geojson": {
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[35.2, 31.7], [36.1, 32.2]],
                    }
                },
                "scripture_links": [],
            }
        )

        self.assertIn("Paul &amp; Barnabas", document)
        self.assertIn("35.2,31.7,0 36.1,32.2,0", document)
        self.assertIn("A &lt;simplified&gt; route", document)

    def test_journey_kml_orders_stops_and_marks_route_approximate(self):
        document = journey_kml(
            {
                "title": "A teaching journey",
                "caution": "The route is approximate.",
                "stops": [
                    {"id": "second", "name": "Second", "order": 2, "lat": 32.0, "lng": 36.0, "passages": ["Acts 2"]},
                    {"id": "first", "name": "First", "order": 1, "lat": 31.0, "lng": 35.0, "passages": ["Acts 1"]},
                    {"id": "missing", "name": "No coordinates", "order": 3},
                ],
            }
        )

        self.assertLess(document.index("1. First"), document.index("2. Second"))
        self.assertIn("approximate route", document)
        self.assertNotIn("No coordinates", document)


if __name__ == "__main__":
    unittest.main()
