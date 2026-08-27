const apiBase = "/api/v1/work-certificates";
const state = {
  headers: {},
  lastCreatedRequestId: null,
};

const qs = (selector, root = document) => root.querySelector(selector);
const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function setAlert(message, type = "success") {
  const alert = qs("#app-alert");
  alert.textContent = message;
  alert.className = `alert is-${type}`;
  alert.hidden = false;
}

function clearAlert() {
  const alert = qs("#app-alert");
  alert.hidden = true;
  alert.textContent = "";
}

function setFieldErrors(errors) {
  qsa("[data-field-error]").forEach((item) => {
    item.textContent = "";
  });
  errors.forEach((error) => {
    if (!error.field) return;
    const target = qs(`[data-field-error="${CSS.escape(error.field)}"]`);
    if (target) target.textContent = error.message;
  });
}

function readIdentity() {
  const role = qs("#identity-role").value;
  const userId = qs("#identity-user-id").value.trim() || "anonymous";
  const employeeId = qs("#identity-employee-id").value.trim();
  state.headers = {
    "Content-Type": "application/json",
    "X-User-Role": role,
    "X-User-Id": userId,
  };
  if (employeeId) state.headers["X-Employee-Id"] = employeeId;
  if (role === "approver") {
    state.headers["X-User-Name"] = "Budi Approver";
    state.headers["X-User-Position"] = "Head of Human Capital";
  }
}

async function api(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: {
      ...state.headers,
      ...(options.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok) {
    const errors = payload.errors || [{ message: "Request gagal.", field: null }];
    const error = new Error(errors[0]?.message || "Request gagal.");
    error.errors = errors;
    throw error;
  }
  return payload.data;
}

function switchView(viewId) {
  qsa(".tab-button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === viewId);
  });
  qsa(".view-panel").forEach((panel) => {
    panel.classList.toggle("is-active", panel.id === viewId);
  });
}

function itemButton(label, meta, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "list-item";
  button.innerHTML = `<strong>${label}</strong><span class="meta-row">${meta}</span>`;
  button.addEventListener("click", onClick);
  return button;
}

function empty(target, message) {
  target.innerHTML = `<div class="empty-state">${message}</div>`;
}

function loading(target) {
  target.innerHTML = '<div class="loading-state">Memuat data...</div>';
}

async function loadTemplates() {
  const select = qs("#template-id");
  select.innerHTML = '<option value="">Memuat...</option>';
  try {
    const templates = await api("/templates?active=true&language=id", { method: "GET" });
    if (!templates.length) {
      select.innerHTML = '<option value="">Template aktif belum tersedia</option>';
      return;
    }
    select.innerHTML = templates
      .map((template) => `<option value="${template.id}">${template.name} (${template.language})</option>`)
      .join("");
  } catch (error) {
    select.innerHTML = '<option value="">Gagal memuat template</option>';
    setAlert(error.message, "error");
  }
}

async function loadRequests(targetSelector = "#request-list", status = null) {
  const target = qs(targetSelector);
  loading(target);
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  try {
    const requests = await api(`/requests${query}`, { method: "GET" });
    target.innerHTML = "";
    if (!requests.length) {
      empty(target, "Belum ada permohonan.");
      return;
    }
    requests.forEach((requestItem) => {
      target.appendChild(
        itemButton(
          requestItem.tracking_number,
          `<span class="status-pill">${requestItem.status}</span><span>${requestItem.purpose}</span>`,
          () => loadRequestDetail(requestItem.id),
        ),
      );
    });
  } catch (error) {
    empty(target, error.message);
  }
}

async function loadQueue() {
  const role = qs("#identity-role").value;
  const status = role === "approver" ? "verified" : null;
  await loadRequests("#queue-list", status);
}

function renderDetail(data) {
  const documentActions = data.issued_document
    ? `<div class="action-row">
        <button type="button" data-download-format="pdf" data-request-id="${data.id}">Unduh PDF</button>
        <button type="button" data-download-format="docx" data-request-id="${data.id}">Unduh DOCX</button>
      </div>`
    : "";
  const actionButtons = data.allowed_actions
    .map((action) => `<button type="button" data-action="${action}" data-request-id="${data.id}">${labelForAction(action)}</button>`)
    .join("");
  const timeline = data.timeline.length
    ? data.timeline
        .map(
          (event) => `<li><strong>${event.action}</strong><div class="meta-row">${event.to_status} - ${event.created_at || ""}</div>${event.note || ""}</li>`,
        )
        .join("")
    : "<li>Belum ada timeline yang dapat ditampilkan.</li>";

  return `
    <article class="detail-card">
      <div>
        <span class="status-pill">${data.status}</span>
        <h3>${data.tracking_number}</h3>
      </div>
      <dl class="data-grid">
        <div><dt>Pegawai</dt><dd>${data.employee.full_name}</dd></div>
        <div><dt>Unit</dt><dd>${data.employee.unit}</dd></div>
        <div><dt>Jabatan</dt><dd>${data.employee.position_title}</dd></div>
        <div><dt>Template</dt><dd>${data.template.name}</dd></div>
        <div><dt>Tujuan</dt><dd>${data.purpose}</dd></div>
        <div><dt>SLA</dt><dd>${data.sla_due_at || "-"}</dd></div>
      </dl>
      ${data.issued_document ? `<p><strong>Nomor surat:</strong> ${data.issued_document.letter_number}</p>` : ""}
      ${documentActions}
      <div class="action-row">${actionButtons}</div>
      <section aria-label="Timeline">
        <h3>Timeline</h3>
        <ul class="timeline">${timeline}</ul>
      </section>
    </article>
  `;
}

function labelForAction(action) {
  const labels = {
    submit: "Kirim",
    cancel: "Batalkan",
    return_to_employee: "Kembalikan ke pegawai",
    reject: "Tolak",
    verify: "Kirim ke approver",
    return_to_hc: "Kembalikan ke HC",
    approve: "Setujui",
  };
  return labels[action] || action;
}

async function loadRequestDetail(requestId) {
  const target = qs("#request-detail");
  loading(target);
  try {
    const data = await api(`/requests/${requestId}`, { method: "GET" });
    target.innerHTML = renderDetail(data);
  } catch (error) {
    empty(target, error.message);
  }
}

async function mutateRequest(action, requestId) {
  const endpoints = {
    submit: { path: `/requests/${requestId}/submit`, body: null },
    cancel: { path: `/requests/${requestId}/cancel`, body: null },
    verify: { path: `/requests/${requestId}/verify`, body: { approver_id: "approver-1" } },
    approve: { path: `/requests/${requestId}/approve`, body: { note: "Disetujui." } },
    return_to_employee: { path: `/requests/${requestId}/return-to-employee`, body: { note: "Mohon lengkapi tujuan penggunaan.", visible_to_employee: true } },
    return_to_hc: { path: `/requests/${requestId}/return-to-hc`, body: { note: "Mohon cek ulang data pegawai." } },
    reject: { path: `/requests/${requestId}/reject`, body: { note: "Permohonan tidak sesuai policy." } },
  };
  const endpoint = endpoints[action];
  if (!endpoint) return;
  try {
    const options = { method: "POST" };
    if (endpoint.body) options.body = JSON.stringify(endpoint.body);
    const data = await api(endpoint.path, options);
    qs("#request-detail").innerHTML = renderDetail(data);
    await loadRequests();
    setAlert("Status permohonan diperbarui.");
  } catch (error) {
    setAlert(error.message, "error");
  }
}

function formPayload(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function bindEvents() {
  qsa(".tab-button").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });

  qs("#identity-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    readIdentity();
    clearAlert();
    await Promise.all([loadTemplates(), loadRequests()]);
  });

  qs("#refresh-templates").addEventListener("click", loadTemplates);
  qs("#refresh-requests").addEventListener("click", () => loadRequests());
  qs("#refresh-queue").addEventListener("click", loadQueue);

  qs("#request-detail").addEventListener("click", (event) => {
    const downloadButton = event.target.closest("[data-download-format]");
    if (downloadButton) {
      downloadDocument(downloadButton.dataset.requestId, downloadButton.dataset.downloadFormat);
      return;
    }
    const button = event.target.closest("[data-action]");
    if (!button) return;
    mutateRequest(button.dataset.action, button.dataset.requestId);
  });

  qs("#create-request-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    clearAlert();
    setFieldErrors([]);
    const payload = {
      template_id: qs("#template-id").value,
      purpose: qs("#request-purpose").value,
      language: qs("#request-language").value,
      additional_fields: { recipient: qs("#additional-recipient").value },
      employee_note: qs("#employee-note").value,
    };
    try {
      const data = await api("/requests", { method: "POST", body: JSON.stringify(payload) });
      state.lastCreatedRequestId = data.id;
      qs("#submit-created-request").disabled = false;
      await loadRequests();
      setAlert(`Draft ${data.tracking_number} tersimpan.`);
    } catch (error) {
      setFieldErrors(error.errors || []);
      setAlert(error.message, "error");
    }
  });

  qs("#submit-created-request").addEventListener("click", async () => {
    if (!state.lastCreatedRequestId) return;
    await mutateRequest("submit", state.lastCreatedRequestId);
    qs("#submit-created-request").disabled = true;
  });

  qs("#employee-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const data = await api("/employees", { method: "POST", body: JSON.stringify(formPayload(event.currentTarget)) });
      qs("#identity-employee-id").value = data.id;
      readIdentity();
      setAlert(`Pegawai ${data.employee_number} tersimpan.`);
    } catch (error) {
      setAlert(error.message, "error");
    }
  });

  qs("#template-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const raw = formPayload(event.currentTarget);
    const required = raw.required_additional_fields
      ? raw.required_additional_fields.split(",").map((item) => item.trim()).filter(Boolean)
      : [];
    const payload = {
      code: raw.code,
      name: raw.name,
      language: raw.language,
      body_template: raw.body_template,
      is_active: event.currentTarget.elements.is_active.checked,
      required_placeholders: ["employee.full_name"],
      additional_field_schema: { required },
    };
    try {
      await api("/admin/templates", { method: "POST", body: JSON.stringify(payload) });
      await loadTemplates();
      setAlert(`Template ${payload.code} tersimpan.`);
    } catch (error) {
      setAlert(error.message, "error");
    }
  });
}

async function downloadDocument(requestId, format) {
  try {
    const response = await fetch(`${apiBase}/requests/${requestId}/documents/${format}`, { headers: state.headers });
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.errors?.[0]?.message || "Dokumen gagal diunduh.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `surat-keterangan-kerja.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    setAlert(error.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  readIdentity();
  bindEvents();
  await Promise.all([loadTemplates(), loadRequests()]);
});
