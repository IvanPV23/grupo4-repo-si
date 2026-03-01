/* ===================================================
   Sistema de Derivación de Tickets — Protecta Seguros
   actions.js
   =================================================== */

'use strict';

const API = 'http://localhost:8000';
const historial = [];

/* ── Lista de informantes ── */
const INFORMANTES = [
    'aalburquer', 'acastro', 'administrisa', 'afung', 'agomez', 'ahernandez',
    'alfonsos', 'amachuca', 'anavelic', 'aboccolini', 'acamacho', 'acarrasco',
    'acassantanec', 'acostell', 'csimaro', 'DQUIÑADO', 'avellar', 'adlatorne',
    'atmontes', 'aalto', 'amora', 'amuro', 'ariverag', 'ariveraj', 'fluentemente',
    'fisaceda', 'fiorenzag', 'fjimenez', 'JJMENF47', 'jollague', 'jsharon',
    'jsaceres', 'jhinostrroza', 'jlandauro', 'jleandre', 'jlopezs', 'jlonique',
    'jmontem', 'jpalcalco', 'jsanchez', 'JVIDAL', 'kcacciano', 'kcusantibar',
    'ktoaback', 'lalvarez', 'lalanda', 'tellegas', 'tellesm', 'limanem',
    'tmalpalacas', 'mnarvaez', 'mrobles', 'mrsanchez', 'mssalor', 'mmiotcto',
    'mmorgan', 'mmorgs', 'mzevillos', 'nhermesn', 'nportugal', 'ocassidio',
    'ohernmesn', 'pmila', 'prianez', 'oriovera', 'orisca', 'rsavia', 'rsagarciac',
    'rsantosdipl', 'soquintero', 'sramirez', 'svalverde', 'syritones',
    'ccortez', 'zolaberru', 'zestros', 'ytirones','mpuray'
].sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' }));

/* ── Searchable Dropdown ── */
let ddOpen = false;
let highlighted = -1;

function initDropdown() {
    const ddSearch = document.getElementById('informador-search');
    const ddList = document.getElementById('dd-list');
    const ddHidden = document.getElementById('informador');
    const ddContainer = document.getElementById('dd-container');

    function renderList(filter) {
        const q = (filter || '').toLowerCase();
        const filtered = INFORMANTES.filter(n => n.toLowerCase().includes(q));
        ddList.innerHTML = filtered.length
            ? filtered.map((n, i) =>
                `<div class="dd-item" data-val="${n}" data-idx="${i}">${n}</div>`
            ).join('')
            : '<div class="dd-empty">Sin resultados</div>';
        highlighted = -1;
    }

    function openDrop() {
        renderList(ddSearch.value);
        ddList.classList.add('open');
        ddOpen = true;
    }

    function closeDrop() {
        ddList.classList.remove('open');
        ddOpen = false;
    }

    function selectItem(val) {
        ddSearch.value = val;
        ddHidden.value = val;
        closeDrop();
    }

    ddSearch.addEventListener('focus', () => openDrop());
    ddSearch.addEventListener('input', () => { openDrop(); ddHidden.value = ''; });
    ddSearch.addEventListener('keydown', (e) => {
        const items = ddList.querySelectorAll('.dd-item');
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            highlighted = Math.min(highlighted + 1, items.length - 1);
            items.forEach((el, i) => el.classList.toggle('highlighted', i === highlighted));
            items[highlighted]?.scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            highlighted = Math.max(highlighted - 1, 0);
            items.forEach((el, i) => el.classList.toggle('highlighted', i === highlighted));
            items[highlighted]?.scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (highlighted >= 0 && items[highlighted]) selectItem(items[highlighted].dataset.val);
        } else if (e.key === 'Escape') {
            closeDrop();
        }
    });

    ddList.addEventListener('mousedown', (e) => {
        const item = e.target.closest('.dd-item');
        if (item) selectItem(item.dataset.val);
    });

    document.addEventListener('click', (e) => {
        if (!ddContainer.contains(e.target)) closeDrop();
    });
}

/* ── Submit ── */
function initForm() {
    document.getElementById('formTicket').addEventListener('submit', async (e) => {
        e.preventDefault();

        const tipoInc = document.getElementById('tipo_incidencia').value;
        const resumen = document.getElementById('resumen').value.trim();
        const tipoSD = document.getElementById('tipo_atencion_sd').value;
        const area = document.getElementById('area').value;
        const informador = document.getElementById('informador').value
            || document.getElementById('informador-search').value.trim();

        if (!tipoInc || !resumen || !tipoSD || !area) {
            mostrarError('Complete todos los campos obligatorios (*).');
            return;
        }

        const btn = document.getElementById('btnEnviar');
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner"></div><span>Procesando...</span>';

        // El payload respeta exactamente el modelo TicketEntrada del backend.
        // descripcion_detallada es Optional en el backend → se omite.
        const payload = {
            tipo_incidencia: tipoInc,
            resumen: resumen,
            tipo_atencion_sd: tipoSD,
            area: area,
            producto: document.getElementById('producto').value || null,
            aplicativo: document.getElementById('aplicativo').value.trim() || null,
            informador: informador || null,
            cantidad_afectados: parseInt(document.getElementById('cantidad_afectados').value) || 1,
            impacta_al_cierre: document.getElementById('impacta_al_cierre').checked,
        };

        try {
            const res = await fetch(`${API}/tickets/nuevo`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            let data;
            try {
                // try parsing JSON; if the response is not valid JSON (e.g. 500 HTML page)
                data = await res.json();
            } catch (parseErr) {
                // fall back to plain text so we can show a meaningful message
                const text = await res.text();
                throw new Error(text || parseErr.message);
            }
            if (!res.ok) throw new Error(data.detail || 'Error del servidor');
            mostrarResultado(data);
        } catch (err) {
            mostrarError(err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="#fff" fill="none"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="22" y1="2" x2="11" y2="13"/>
          <polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
        <span>Derivar Ticket</span>`;
        }
    });
}

/* ── Helpers ── */
function nivelClass(n) {
    return n === 'N1' ? 'nivel-n1' : n === 'N2' ? 'nivel-n2' : 'nivel-n3';
}

function mostrarResultado(d) {
    const box = document.getElementById('resultado');
    const content = document.getElementById('resultado-content');
    box.style.display = 'block';

    const tiempoStr = d.tiempo_estimado_horas != null
        ? `${d.tiempo_estimado_horas}h · ${d.categoria_tiempo || ''}`
        : '—';

    const via = d.via_historico
        ? '<span style="color:#15803d;font-weight:600;">Histórico</span>'
        : '<span style="color:var(--text-muted);">Pipeline completo</span>';

    const estado = d.en_cola
        ? '<span class="status-cola">En cola</span>'
        : '<span class="status-Ok">Asignado</span>';

    content.innerHTML = `
    <div class="resultado-grid">
      <div class="metric">
        <div class="metric-label">Mesa Asignada</div>
        <div class="metric-value" style="font-size:.9rem;">${d.mesa_asignada}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Nivel</div>
        <div class="metric-value ${nivelClass(d.nivel_asignado)}">${d.nivel_asignado}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Complejidad</div>
        <div class="metric-value" style="font-size:1rem;">
          <span class="badge-comp comp-${d.complejidad}">${d.complejidad.toUpperCase()}</span>
          <div style="font-size:.67rem;color:var(--text-muted);margin-top:.35rem;">score ${d.score_complejidad}</div>
        </div>
      </div>
      <div class="metric">
        <div class="metric-label">Tiempo Estimado</div>
        <div class="metric-value" style="font-size:.88rem;color:var(--blue);">${tiempoStr}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Estado</div>
        <div class="metric-value" style="font-size:.85rem;">${estado}</div>
      </div>
    </div>
    <div class="ticket-id-row">
      <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="var(--text-muted)"
           stroke-width="2" stroke-linecap="round">
        <rect x="2" y="7" width="20" height="14" rx="2"/>
        <path d="M16 3l-4 4-4-4"/>
      </svg>
      Ticket ID: <code>${d.ticket_id}</code>
    </div>
    <div class="razonamiento">${d.razonamiento}</div>
  `;

    historial.unshift({ id: d.ticket_id, mesa: d.mesa_asignada, nivel: d.nivel_asignado });
    actualizarHistorial();
    box.scrollIntoView({ behavior: 'smooth' });
}

function mostrarError(msg) {
    const box = document.getElementById('resultado');
    const content = document.getElementById('resultado-content');
    box.style.display = 'block';
    content.innerHTML = `
    <div class="error-box">
      <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>${msg}</span>
    </div>`;
    box.scrollIntoView({ behavior: 'smooth' });
}

function actualizarHistorial() {
    const ul = document.getElementById('historial-list');
    if (!historial.length) {
        ul.innerHTML = '<li style="color:var(--text-muted);font-size:.8rem;padding:.4rem 0;">Sin tickets procesados aún.</li>';
        return;
    }
    ul.innerHTML = historial.slice(0, 8).map(h => `
    <li>
      <span class="hist-id">${h.id}</span>
      <span class="hist-mesa">${h.mesa}</span>
      <span class="hist-nivel ${h.nivel.toLowerCase()}">${h.nivel}</span>
    </li>
  `).join('');
}

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
    initDropdown();
    initForm();
});
