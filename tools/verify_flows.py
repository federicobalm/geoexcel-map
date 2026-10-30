"""Browser regression: run against a local server with installed Chromium.

    python tools/verify_flows.py --url http://127.0.0.1:8765
"""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

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


def verify_exports(context, page, prefix, directory, kind, pdf=False):
    with page.expect_download(timeout=90000) as download:
        page.locator(f'#{prefix}export-html').click()
    html = Path(directory) / f'{kind}.html'
    download.value.save_as(html)
    exported = context.new_page()
    errors = []
    exported.on('pageerror', lambda error: errors.append(str(error)))
    exported.goto(html.as_uri(), wait_until='networkidle')
    expect(exported.locator('.cartographic-legend')).to_be_visible()
    if kind in ('hotmap', 'profile'):
        expect(exported.locator('canvas.leaflet-heatmap-layer')).to_be_visible()
    if kind == 'choropleth':
        assert exported.locator('.leaflet-overlay-pane path').count() > 0
    if kind == 'heatmap':
        expect(exported.locator('img.leaflet-image-layer')).to_be_visible()
    assert not errors, errors
    exported.close()
    if pdf:
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
            if kind == 'heatmap':
                assert response.value.json()['points'] == []
                assert response.value.json()['map_config']['heat_palette'] == 'blues'
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
