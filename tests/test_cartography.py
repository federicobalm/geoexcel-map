import unittest

import numpy as np
import pandas as pd
from pydantic import ValidationError

from app.models import MapRequest, MapSummary
from app.services.cartography import build_cartography, gaussian_density


def request_data(**overrides):
    data = {
        'session_id': 'test', 'lat_column': 'lat', 'lon_column': 'lon',
        'cartographic_metadata': {
            'event': 'Eventos ficticios', 'geographic_unit': 'CABA',
            'period_start': '2026-01-01', 'period_end': '2026-01-28',
            'author': 'Docente', 'synthetic': True, 'period_confirmed': True,
        },
    }
    data.update(overrides)
    return data


class CartographicRulesTest(unittest.TestCase):
    def test_required_metadata(self):
        data = request_data()
        del data['cartographic_metadata']
        with self.assertRaises(ValidationError): MapRequest(**data)

    def test_points_accept_long_period_without_removed_fields(self):
        data = request_data()
        MapRequest(**data)
        data['cartographic_metadata']['period_end'] = '2026-12-31'
        MapRequest(**data)

    def test_reject_real_data_unconfirmed_or_inverted_dates(self):
        for change in ['real', 'unconfirmed', 'inverted']:
            data = request_data()
            if change == 'real': data['cartographic_metadata']['synthetic'] = False
            elif change == 'unconfirmed': data['cartographic_metadata']['period_confirmed'] = False
            else: data['cartographic_metadata']['period_end'] = '2025-01-01'
            with self.subTest(change=change), self.assertRaises(ValidationError): MapRequest(**data)

    def test_all_map_types_accept_simplified_metadata(self):
        for kind in ['points', 'cluster', 'heatmap', 'hotmap', 'choropleth', 'proportional', 'profile']:
            with self.subTest(kind=kind):
                MapRequest(**request_data(map_type=kind))

    def test_classic_palette_and_ordered_levels(self):
        MapRequest(**request_data(map_type='hotmap', heat_palette='classic'))
        with self.assertRaises(ValidationError): MapRequest(**request_data(heat_levels=[10, 10, 50, 80, 100]))

    def test_rossmo_ignores_removed_variable_from_old_client(self):
        data = request_data(map_type='profile')
        data['cartographic_metadata']['variable'] = 'frequency'
        request = MapRequest(**data)
        self.assertNotIn('variable', request.cartographic_metadata.model_dump())

    def test_export_view_validation_and_legacy_requests(self):
        self.assertIsNone(MapRequest(**request_data()).map_view)
        for change in ({'lat': 91}, {'lon': -181}, {'zoom': 20}, {'zoom': float('nan')}, {'lat': 'invalid'}):
            view = {'lat': -34.6, 'lon': -58.4, 'zoom': 15, **change}
            with self.subTest(change=change), self.assertRaises(ValidationError):
                MapRequest(**request_data(map_view=view))

    def test_kde_gaussian_magnitude_and_bandwidth(self):
        single = pd.DataFrame({'lat': [-34.60], 'lon': [-58.40]})
        one = gaussian_density(single, 500)
        four = gaussian_density(pd.concat([single] * 4), 500)
        broad = gaussian_density(single, 1000)
        self.assertAlmostEqual(four['maximum'] / one['maximum'], 4, places=5)
        self.assertAlmostEqual(one['maximum'], 1e6 / (2 * np.pi * 500**2), delta=.01)
        self.assertAlmostEqual(one['maximum'] / broad['maximum'], 4, delta=.02)
        self.assertEqual(len(one['values']), one['rows'] * one['cols'])
        self.assertTrue(np.isfinite(one['values']).all())
        self.assertGreaterEqual(min(one['values']), 0)
        self.assertNotIn('points', one)

    def test_geopositioning_denominator_and_duplicates(self):
        frame = pd.DataFrame({'lat': [-34.6, -34.6], 'lon': [-58.4, -58.4]})
        summary = MapSummary(total_rows=4, valid_rows=2, invalid_rows=2, invalid_breakdown=[], bounds=None, detected_swap_warning=False)
        report = build_cartography(MapRequest(**request_data()), summary, frame)
        self.assertEqual(report['geocoding_percentage'], 50)
        self.assertTrue(any('comparten coordenadas' in text for text in report['warnings']))
        self.assertIn('2026-01-28', report['title'])


if __name__ == '__main__': unittest.main()
