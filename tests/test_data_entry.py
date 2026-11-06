from io import BytesIO
from pathlib import Path
import unittest

import pandas as pd
from openpyxl import load_workbook
from pydantic import ValidationError

from app.errors import AppError
from app.models import ManualDatasetRequest
from app.services.datasets import detect_coordinate_columns, prepare_dataframe, read_uploaded_table, validate_coordinates


class DataEntryTest(unittest.TestCase):
    def test_downloadable_excel_examples_can_be_edited_and_reuploaded(self):
        sample_dir = Path(__file__).resolve().parents[1] / 'sample_data'
        expectations = {
            'plantilla_geoexcel_map.xlsx': (300, 'latitud', 'longitud'),
            'serie_rossmo_demo.xlsx': (6, 'Latitud', 'Longitud'),
        }
        for filename, (rows, lat_column, lon_column) in expectations.items():
            with self.subTest(filename=filename):
                content = (sample_dir / filename).read_bytes()
                frame = prepare_dataframe(read_uploaded_table(filename, content))
                self.assertEqual(len(frame), rows)
                self.assertIn(lat_column, frame.columns)
                self.assertIn(lon_column, frame.columns)

                workbook = load_workbook(BytesIO(content))
                sheet = workbook.active
                extra = ['2026-01-01', '12:00', 'Prueba'] if rows == 6 else ['Prueba', 'Centro', 'Barrio ficticio', 'Fila agregada']
                sheet.append([f'Editado {rows + 1}', -34.61, -58.41, *extra])
                modified = BytesIO()
                workbook.save(modified)
                edited = prepare_dataframe(read_uploaded_table(filename, modified.getvalue()))
                self.assertEqual(len(edited), rows + 1)

    def test_manual_decimal_comma_and_optional_fields(self):
        request = ManualDatasetRequest(events=[{'latitud': '-34,6037', 'longitud': '-58.3816'}])
        self.assertEqual(request.events[0].latitud, -34.6037)
        self.assertEqual(request.events[0].descripcion, '')

    def test_manual_rejects_empty_invalid_or_oversized_dataset(self):
        for events in ([], [{'latitud': '', 'longitud': 0}], [{'latitud': 91, 'longitud': 0}],
                       [{'latitud': 0, 'longitud': 'nan'}], [{'latitud': 0, 'longitud': 0, 'fecha': '2026-02-30'}],
                       [{'latitud': 0, 'longitud': 0}] * 501):
            with self.subTest(events_count=len(events)), self.assertRaises(ValidationError):
                ManualDatasetRequest(events=events)

    def test_excel_csv_separator_directive_and_comma_decimals(self):
        content = 'sep=;\r\ncaso;latitud;longitud\r\nUno;-34,6037;-58,3816\r\n'.encode('utf-8-sig')
        frame = prepare_dataframe(read_uploaded_table('ejemplo.csv', content))
        self.assertEqual(list(frame.columns), ['caso', 'latitud', 'longitud'])
        cleaned, summary = validate_coordinates(frame, 'latitud', 'longitud')
        self.assertEqual(summary['valid_rows'], 1)
        self.assertEqual(cleaned.iloc[0]['lat'], -34.6037)

    def test_duplicate_headers_after_trimming_do_not_break_detection(self):
        original = pd.DataFrame([[-34.6, -34.61, -58.4]], columns=[' latitud ', 'latitud', 'longitud'])
        buffer = BytesIO()
        original.to_excel(buffer, index=False)
        frame = prepare_dataframe(read_uploaded_table('ejemplo.xlsx', buffer.getvalue()))
        self.assertTrue(frame.columns.is_unique)
        self.assertEqual(detect_coordinate_columns(frame)[:2], ('latitud', 'longitud'))

    def test_header_only_file_reports_no_events(self):
        with self.assertRaises(AppError):
            prepare_dataframe(read_uploaded_table('vacio.csv', b'latitud,longitud\n'))


if __name__ == '__main__':
    unittest.main()
