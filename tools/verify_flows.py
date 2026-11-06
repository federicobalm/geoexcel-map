"""Browser regression: run against a local server with installed Chromium.

    python tools/verify_flows.py --url http://127.0.0.1:8765
"""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import expect, sync_playwright


def fill_metadata(page, prefix):
    for suffix, value in {
        'event': 'Ejercicio de clase', 'unit': 'Buenos Aires',
        'start': '2026-01-01', 'end': '2026-12-31', 'author': 'Docente',
    }.items():
        page.locator(f'#{prefix}-{suffix}').fill(value)
    page.locator(f'#{prefix}-synthetic').check()
    page.locator(f'#{prefix}-period-confirmed').check()
    for removed in ('source', 'coordinates-source', 'variable', 'point-days'):
        assert page.locator(f'#{prefix}-{removed}').count() == 0


def assert_map_view(page, expected):
    actual = page.evaluate('({lat: map.getCenter().lat, lon: map.getCenter().lng, zoom: map.getZoom()})')
    for key in ('lat', 'lon', 'zoom'):
        assert abs(actual[key] - expected[key]) < 1e-7, (key, actual, expected)


def assert_classic_heat(page):
    assert page.evaluate("""() => {
        const canvas = document.querySelector('canvas.leaflet-heatmap-layer');
        if (!canvas) return false;
        const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
        let renderedPixels = 0;
        for (let index = 3; index < pixels.length; index += 4) {
            if (pixels[index] > 0) renderedPixels += 1;
        }
        let gradient = null;
        const targetMap = typeof appState !== 'undefined' ? appState.mapInstance : (typeof rossmoState !== 'undefined' ? rossmoState.mapInstance : map);
        targetMap.eachLayer(layer => {
            if (layer._heat && layer.options?.gradient) gradient = Object.values(layer.options.gradient);
        });
        return renderedPixels >= 100 && ['#0000ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000'].every(color => gradient?.includes(color));
    }"""), 'Expected a rendered heat layer with the five classic colors'


def verify_exports(context, page, prefix, directory, kind, pdf=False):
    state = 'rossmoState' if prefix else 'appState'
    analysis_id = '#rossmo-personal-analysis' if prefix else '#map-personal-analysis'
    expected_analysis = page.locator(analysis_id).input_value()
    expected_view = page.evaluate(f'readMapView({state}.mapInstance)')
    with page.expect_download(timeout=90000) as download:
        page.locator(f'#{prefix}export-html').click()
    html = Path(directory) / f'{kind}.html'
    download.value.save_as(html)
    exported = context.new_page()
    errors = []
    osm_requests = []
    exported.on('pageerror', lambda error: errors.append(str(error)))
    exported.on('request', lambda request: osm_requests.append(request.url) if 'tile.openstreetmap.org/' in request.url else None)
    exported.goto(html.as_uri(), wait_until='networkidle')
    expect(exported.locator('.cartographic-legend')).to_be_visible()
    expect(exported.get_by_role('heading', name='Análisis sistematizado', exact=True)).to_be_visible()
    expect(exported.get_by_role('heading', name='Interpretación del estudiante', exact=True)).to_be_visible()
    exported.wait_for_function("""() => {
        const tiles = [...document.querySelectorAll('#map img.leaflet-tile')];
        return tiles.length > 0 && tiles.every(tile => tile.complete && tile.naturalWidth > 0);
    }""")
    assert not osm_requests, 'Local exports must not request OpenStreetMap tiles'
    assert exported.evaluate('window.GEOEXCEL_EXPORT_PAYLOAD.map_config.tile_layer') == 'Esri Light Gray'
    expect(exported.locator('.cartographic-legend')).to_contain_text('Esri Light Gray sustituye a OpenStreetMap')
    payload = exported.evaluate('window.GEOEXCEL_EXPORT_PAYLOAD')
    assert payload['map_config']['map_view'] == expected_view
    assert payload['map_config']['personal_analysis'] == expected_analysis
    expect(exported.locator('#personal-analysis')).to_have_text(expected_analysis)
    if not prefix:
        assert exported.locator('#systematic-list li').count() == 3
        assert exported.locator('#systematic-list').evaluate("(element) => Boolean(element.compareDocumentPosition(document.querySelector('#map')) & Node.DOCUMENT_POSITION_FOLLOWING)")
    assert_map_view(exported, expected_view)
    if kind in ('hotmap', 'profile'):
        expect(exported.locator('canvas.leaflet-heatmap-layer')).to_be_visible()
        assert_classic_heat(exported)
    if kind == 'choropleth':
        assert exported.locator('.leaflet-overlay-pane path').count() > 0
    if kind == 'heatmap':
        expect(exported.locator('img.leaflet-image-layer')).to_be_visible()
    assert not errors, errors
    exported.close()
    if pdf:
        # Exercise the actual PDF template at the renderer's viewport size.
        env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1] / 'app/templates'), autoescape=select_autoescape())
        pdf_source = Path(directory) / f'{kind}-pdf.html'
        pdf_source.write_text(env.get_template('export_pdf.html').render(
            title='Prueba de encuadre', title_json=json.dumps('Prueba de encuadre'),
            map_payload_json=json.dumps(payload), summary_json=json.dumps(payload['summary']),
        ), encoding='utf-8')
        pdf_page = context.new_page()
        pdf_page.set_viewport_size({'width': 1440, 'height': 1080})
        pdf_page.goto(pdf_source.as_uri(), wait_until='networkidle')
        pdf_page.wait_for_function('window.__EXPORT_READY === true')
        pdf_page.emulate_media(media='print')
        assert_map_view(pdf_page, expected_view)
        pdf_page.close()
        with page.expect_download(timeout=120000) as download:
            page.locator(f'#{prefix}export-pdf').click()
        target = Path(directory) / f'{kind}.pdf'
        download.value.save_as(target)
        content = target.read_bytes()
        assert content.startswith(b'%PDF-') and len(content) > 10000
    print(f'PASS {kind}: preview + HTML' + (' + PDF' if pdf else ''), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    with TemporaryDirectory(prefix='geoexcel-flows-') as directory, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(accept_downloads=True, viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='networkidle')
        page.locator('#load-demo').click()
        expect(page.locator('#map-stage-2')).to_be_visible()
        fill_metadata(page, 'map')
        for kind in ('hotmap', 'heatmap', 'choropleth', 'points', 'proportional', 'cluster', 'category'):
            page.locator(f'input[name=map_choice][value={kind}]').check()
            if kind == 'category':
                page.locator('#category-column').select_option(index=1)
            with page.expect_response('**/api/map-preview') as response:
                page.locator('#map-config-form button[type=submit]').click()
            assert response.value.status == 200, response.value.text()
            expect(page.locator('#map-stage-3')).to_be_visible()
            if kind == 'hotmap':
                assert response.value.json()['map_config']['heat_palette'] == 'classic'
                expect(page.locator('canvas.leaflet-heatmap-layer')).to_be_visible()
                assert_classic_heat(page)
            if kind == 'heatmap':
                assert response.value.json()['points'] == []
                assert response.value.json()['map_config']['heat_palette'] == 'blues'
            page.evaluate('appState.mapInstance.setView([-34.595, -58.405], 15, {animate: false})')
            expect(page.locator('#map-systematic-analysis li')).to_have_count(3)
            page.locator('#map-personal-analysis').fill(f'Interpretación académica para {kind}.')
            verify_exports(context, page, '', directory, kind, pdf=kind in ('hotmap', 'heatmap', 'choropleth'))
            page.get_by_role('button', name='Cambiar mapa', exact=True).click()

        # Invalid metadata must have a readable error even for a raw API caller.
        invalid = page.evaluate('currentMapRequest()')
        invalid['cartographic_metadata']['period_end'] = '2025-01-01'
        response = context.request.post(args.url + '/api/map-preview', data=invalid)
        assert response.status == 422
        assert isinstance(response.json()['detail'], str)
        assert 'fecha inicial' in response.json()['detail']
        assert page.evaluate("apiErrorMessage({detail:[{loc:['body','field'],msg:'Revisar valor'}]})") == 'field: Revisar valor'
        assert page.evaluate("apiErrorMessage({detail:{message:'Revisar datos'}})") == 'Revisar datos'

        page.goto(args.url + '/rossmo', wait_until='networkidle')
        page.locator('#rossmo-load-dataset').click()
        expect(page.locator('#rossmo-next-from-upload')).to_be_enabled()
        page.locator('#rossmo-next-from-upload').click()
        fill_metadata(page, 'rossmo')
        page.locator('#rossmo-verify-form button[type=submit]').click()
        page.locator('#rossmo-next-from-verify').click()
        with page.expect_response('**/api/map-preview') as response:
            page.locator('#rossmo-compute-form button[type=submit]').click()
        assert response.value.status == 200, response.value.text()
        assert response.value.json()['profile']['crimes_used'] == 6
        page.locator('#rossmo-next-from-compute').click()
        expect(page.locator('#rossmo-map canvas.leaflet-heatmap-layer')).to_be_visible()
        assert_classic_heat(page)
        page.evaluate('rossmoState.mapInstance.setView([-34.595, -58.405], 15, {animate: false})')
        page.locator('#rossmo-continue-analysis').click()
        page.locator('#rossmo-back-to-preview').click()
        page.wait_for_function('rossmoState.mapInstance.getZoom() === 15')
        page.locator('#rossmo-continue-analysis').click()
        page.locator('#rossmo-personal-analysis').fill('Hipotesis de clase: contrastar el anclaje con evidencia independiente.')
        page.locator('#rossmo-confirm-analysis').click()
        verify_exports(context, page, 'rossmo-', directory, 'profile', pdf=True)

        page.locator('#rossmo-back-to-analysis').click()
        page.locator('#rossmo-back-to-preview').click()
        page.locator('#rossmo-back-to-compute').click()
        page.locator('#rossmo-buffer-radius-m').fill('500')
        expect(page.locator('#rossmo-next-from-compute')).to_be_disabled()
        expect(page.locator('#rossmo-export-html')).to_be_disabled()
        with page.expect_response('**/api/map-preview') as response:
            page.locator('#rossmo-compute-form button[type=submit]').click()
        assert response.value.status == 200
        expect(page.locator('#rossmo-next-from-compute')).to_be_enabled()
        assert not errors, errors
        browser.close()
    print('PASS validation errors and Rossmo recalculation; no JavaScript exceptions.', flush=True)


if __name__ == '__main__':
    main()
