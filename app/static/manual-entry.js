// Shared event-by-event editor for both classroom workflows.
function initManualEntry(onLoaded) {
  const form = document.getElementById('manual-event-form');
  const rows = document.getElementById('manual-rows');
  const feedback = document.getElementById('manual-feedback');
  const proceed = document.getElementById('manual-continue');
  const save = document.getElementById('manual-save');
  const cancel = document.getElementById('manual-cancel');
  const fields = ['caso', 'latitud', 'longitud', 'fecha', 'hora', 'tipo', 'zona', 'barrio', 'descripcion'];
  const events = [];
  let editing = null;
  let dirty = false;
  let busy = false;

  function message(text, error = false) {
    feedback.textContent = text;
    feedback.classList.toggle('is-error', error);
  }
  function resetEditor() {
    form.reset();
    fields.forEach(field => form.elements[field].setCustomValidity(''));
    editing = null;
    dirty = false;
    save.textContent = 'Agregar evento';
    cancel.hidden = true;
  }
  function render() {
    rows.replaceChildren();
    events.forEach((event, index) => {
      const row = document.createElement('tr');
      [event.caso, event.latitud, event.longitud, [event.fecha, event.hora].filter(Boolean).join(' '), event.tipo].forEach(value => {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.appendChild(cell);
      });
      const actions = document.createElement('td');
      const edit = document.createElement('button');
      edit.type = 'button'; edit.className = 'text-button'; edit.textContent = 'Editar';
      edit.setAttribute('aria-label', `Editar evento ${index + 1}`);
      edit.disabled = busy;
      edit.addEventListener('click', () => {
        if (dirty && !window.confirm('Hay cambios sin agregar. ¿Querés descartarlos y editar este evento?')) return;
        resetEditor(); editing = index;
        fields.forEach(field => form.elements[field].value = event[field]);
        save.textContent = 'Guardar cambios'; cancel.hidden = false;
        form.elements.caso.focus();
      });
      const remove = document.createElement('button');
      remove.type = 'button'; remove.className = 'text-button'; remove.textContent = 'Quitar';
      remove.setAttribute('aria-label', `Quitar evento ${index + 1}`);
      remove.disabled = busy;
      remove.addEventListener('click', () => {
        events.splice(index, 1);
        if (editing === index) resetEditor();
        else if (editing !== null && editing > index) editing--;
        render(); message('Evento quitado.');
      });
      actions.append(edit, remove); row.appendChild(actions); rows.appendChild(row);
    });
    document.getElementById('manual-table-wrap').hidden = !events.length;
    document.getElementById('manual-count').textContent = `${events.length} eventos cargados`;
    proceed.disabled = busy || !events.length;
  }
  form.addEventListener('input', event => {
    dirty = true;
    cancel.hidden = false;
    event.target.setCustomValidity('');
    message('Recordá agregar el evento o guardar los cambios antes de continuar.');
  });
  cancel.addEventListener('click', () => { resetEditor(); message('Edición cancelada.'); });
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (busy) return;
    const record = Object.fromEntries(fields.map(field => [field, form.elements[field].value.trim()]));
    for (const [field, limit] of [['latitud', 90], ['longitud', 180]]) {
      const input = form.elements[field];
      const value = Number(record[field].replace(',', '.'));
      if (!record[field] || !Number.isFinite(value) || Math.abs(value) > limit) {
        input.setCustomValidity(`Ingresá un número entre ${-limit} y ${limit}. Podés usar punto o coma decimal.`);
        input.reportValidity(); return;
      }
      record[field] = value;
    }
    if (editing === null && events.length >= 500) { message('Llegaste al límite de 500 eventos manuales.', true); return; }
    record.caso ||= `Evento ${editing === null ? events.length + 1 : editing + 1}`;
    if (editing === null) events.push(record);
    else events[editing] = record;
    resetEditor(); render(); message('Evento guardado. Podés agregar otro o continuar.');
    form.elements.caso.focus();
  });
  proceed.addEventListener('click', async () => {
    if (busy || !events.length) return;
    if (dirty || editing !== null) {
      message('Tenés un evento sin guardar. Presioná Agregar evento o Guardar cambios; también podés cancelar la edición.', true);
      save.focus(); return;
    }
    busy = true;
    document.getElementById('manual-entry').setAttribute('aria-busy', 'true');
    [...form.elements].forEach(input => input.disabled = true);
    render(); message('Preparando los eventos...');
    try {
      const response = await fetch('/api/manual-data', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({events}),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(body));
      await onLoaded(body);
      message('Eventos listos para configurar el mapa.');
    } catch (error) {
      message(error.message || 'No se pudo completar la carga manual. Volvé a intentarlo.', true);
    } finally {
      busy = false;
      [...form.elements].forEach(input => input.disabled = false);
      document.getElementById('manual-entry').setAttribute('aria-busy', 'false');
      render();
    }
  });
}
