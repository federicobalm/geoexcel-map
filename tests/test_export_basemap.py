import unittest
from unittest.mock import patch

import pandas as pd

from app.main import _build_export_payload
from app.models import MapRequest
from test_cartography import request_data


class ExportBasemapTest(unittest.TestCase):
    def test_local_export_replaces_osm_and_describes_actual_provider(self):
        view = {'lat': -34.595, 'lon': -58.405, 'zoom': 15}
        request = MapRequest(**request_data(map_type='hotmap', map_view=view))
        frame = pd.DataFrame({'lat': [-34.60, -34.61], 'lon': [-58.40, -58.41]})
        with patch('app.main.session_store.load_dataframe', return_value=frame):
            result = _build_export_payload(request)
        self.assertEqual(request.tile_layer, 'OpenStreetMap')
        self.assertEqual(result.map_config.tile_layer, 'Esri Light Gray')
        self.assertEqual(result.cartography['basemap'], 'Esri Light Gray')
        self.assertTrue(any('OpenStreetMap' in item for item in result.cartography['warnings']))
        self.assertEqual(len(result.points), 2)
        self.assertEqual(result.map_config.map_view.model_dump(), view)

    def test_export_preserves_other_selected_basemaps(self):
        frame = pd.DataFrame({'lat': [-34.60], 'lon': [-58.40]})
        for basemap in ('Esri Light Gray', 'Esri Dark Gray', 'Esri World Imagery'):
            with self.subTest(basemap=basemap):
                request = MapRequest(**request_data(tile_layer=basemap))
                with patch('app.main.session_store.load_dataframe', return_value=frame):
                    result = _build_export_payload(request)
                self.assertEqual(result.map_config.tile_layer, basemap)
                self.assertEqual(result.cartography['basemap'], basemap)


if __name__ == '__main__':
    unittest.main()
