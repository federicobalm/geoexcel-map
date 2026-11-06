"""Exercise manual data entry and real exports on both classroom pages."""
import argparse
from tempfile import TemporaryDirectory

from playwright.sync_api import expect, sync_playwright
from verify_flows import assert_classic_heat, fill_metadata, verify_exports


def enter_events(page, coordinates=None):
    page.locator('#manual-entry summary').click()
    page.fill('#manual-latitud', '91')
    page.fill('#manual-longitud', '-58,40')
    page.click('#manual-save')
    expect(page.locator('#manual-rows tr')).to_have_count(0)
    assert not page.locator('#manual-latitud').evaluate('(input) => input.validity.valid')
    coordinates = coordinates or [(-34.60 - .001 * index, -58.40 - .001 * index) for index in range(6)]
    for index, (lat, lon) in enumerate(coordinates):
        page.fill('#manual-caso', f'Caso {index + 1}')
        page.fill('#manual-latitud', str(lat).replace('.', ','))
        page.fill('#manual-longitud', str(lon).replace('.', ','))
        page.fill('#manual-fecha', '2026-01-01')
        page.fill('#manual-hora', '12:30')
        page.fill('#manual-tipo', 'Tipo A' if index % 2 else 'Tipo B')
        page.fill('#manual-zona', 'Centro')
        page.fill('#manual-barrio', 'Barrio ficticio')
        page.fill('#manual-descripcion', 'Ejercicio <sin investigación>')
        page.click('#manual-save')
    expect(page.locator('#manual-rows tr')).to_have_count(6)
    page.get_by_role('button', name='Editar evento 1', exact=True).click()
    expect(page.locator('#manual-descripcion')).to_have_value('Ejercicio <sin investigación>')
    page.fill('#manual-caso', 'Evento corregido')
    page.click('#manual-save')
    expect(page.locator('#manual-rows tr').first).to_contain_text('Evento corregido')
    page.get_by_role('button', name='Quitar evento 6', exact=True).click()
    expect(page.locator('#manual-rows tr')).to_have_count(5)
    page.fill('#manual-caso', 'Borrador pendiente')
    page.click('#manual-continue')
    expect(page.locator('#manual-feedback')).to_contain_text('sin guardar')
    page.click('#manual-cancel')
    with page.expect_response('**/api/manual-data') as response:
        page.click('#manual-continue')
    assert response.value.status == 200, response.value.text()
    upload = response.value.json()
    assert upload['row_count'] == 5
    assert upload['suggested_lat_column'] == 'latitud'
    assert upload['suggested_lon_column'] == 'longitud'
    assert upload['preview_rows'][0]['caso'] == 'Evento corregido'
    assert upload['preview_rows'][0]['descripcion'] == 'Ejercicio <sin investigación>'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8767')
    url = parser.parse_args().url
    with TemporaryDirectory(prefix='manual-entry-') as directory, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(url, wait_until='networkidle')
        enter_events(page)
        expect(page.locator('#map-stage-2')).to_be_visible()
        fill_metadata(page, 'map')
        page.check('input[name=map_choice][value=hotmap]')
        page.click('#map-config-form button[type=submit]')
        expect(page.locator('#map-stage-3')).to_be_visible()
        expect(page.locator('#map-systematic-analysis li')).to_have_count(3)
        page.fill('#map-personal-analysis', 'Interpretación académica de los eventos ingresados manualmente.')
        verify_exports(context, page, '', directory, 'hotmap', pdf=True)
        page.set_viewport_size({'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert len(page.locator('.common-analysis').evaluate('(element) => getComputedStyle(element).gridTemplateColumns').split()) == 1
        page.set_viewport_size({'width': 1280, 'height': 900})
        page.get_by_role('button', name='Cambiar mapa', exact=True).click()
        page.locator('#map-stage-2 [data-go-step="1"]').first.click()
        expect(page.locator('#manual-rows tr')).to_have_count(5)

        page.goto(url + '/rossmo', wait_until='networkidle')
        enter_events(page, [
            (-34.43, -57.86), (-34.54, -58.55), (-34.66, -58.70),
            (-34.72, -58.43), (-34.91, -58.85), (-34.80, -58.20),
        ])
        expect(page.locator('#step-verify')).to_be_visible()
        fill_metadata(page, 'rossmo')
        page.click('#rossmo-verify-form button[type=submit]')
        page.click('#rossmo-next-from-verify')
        with page.expect_response('**/api/map-preview') as response:
            page.click('#rossmo-compute-form button[type=submit]')
        assert response.value.status == 200, response.value.text()
        assert response.value.json()['profile']['crimes_used'] == 5
        assert len(response.value.json()['profile']['jeopardy_points']) >= 10000
        page.click('#rossmo-next-from-compute')
        expect(page.locator('#rossmo-map canvas')).to_be_visible()
        assert_classic_heat(page)
        page.click('#rossmo-continue-analysis')
        page.fill('#rossmo-personal-analysis', 'Interpretación académica de la serie ficticia.')
        page.click('#rossmo-confirm-analysis')
        verify_exports(context, page, 'rossmo-', directory, 'profile', pdf=True)
        bad = context.request.post(url + '/api/manual-data', data={'events': [{'latitud': 95, 'longitud': 0}]})
        assert bad.status == 422 and 'Evento 1' in bad.json()['detail']
        assert not errors, errors
        browser.close()
    print('PASS manual maps/Rossmo, validation, editing, removal, unsaved drafts, mobile layout and HTML/PDF.')


if __name__ == '__main__':
    main()
