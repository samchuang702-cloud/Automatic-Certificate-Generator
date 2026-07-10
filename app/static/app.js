const state = {
  certificates: [],
  token: localStorage.getItem("accessToken"),
  currentUser: JSON.parse(localStorage.getItem("currentUser") || "null"),
  queryIdentity: JSON.parse(localStorage.getItem("queryIdentity") || "null"),
};

function $(id) {
  return document.getElementById(id);
}

function setStatus(element, message, type = "") {
  element.textContent = message;
  element.className = `result-bar ${type}`.trim();
}

function cleanLoginValue(value) {
  return value.replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
}

function getExcelFile() {
  const file = $("excelFileInput").files[0];
  if (!file) {
    throw new Error("請先選擇 Excel 檔案。");
  }
  return file;
}

function buildFileForm(file) {
  const formData = new FormData();
  formData.append("file", file);
  return formData;
}

async function parseJsonResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "API 請求失敗。");
  }
  return payload;
}

function authHeaders(extraHeaders = {}) {
  if (!state.token) {
    throw new Error("請先登入。");
  }
  return {
    ...extraHeaders,
    Authorization: `Bearer ${state.token}`,
  };
}

async function apiFetch(url, options = {}) {
  const headers = options.headers || {};
  return fetch(url, {
    ...options,
    headers: authHeaders(headers),
  });
}

function canUseAdmin() {
  return state.currentUser?.role === "admin";
}

function replaceHash(hash) {
  if (window.location.hash !== hash) {
    window.history.replaceState(null, "", hash);
  }
}

function applyRoleView() {
  const loginPanel = $("loginPanel");
  const adminPanel = $("admin");
  const userPanel = $("user");
  const logoutButton = $("logoutButton");
  const loginButton = $("loginButton");

  if (!state.currentUser) {
    loginPanel.classList.remove("hidden");
    adminPanel.classList.add("hidden");
    userPanel.classList.add("hidden");
    logoutButton.classList.add("hidden");
    loginButton.disabled = false;
    setStatus($("authStatus"), "請先登入後再操作系統。");
    setStatus($("userStatus"), "請先登入。");
    return;
  }

  loginPanel.classList.add("hidden");
  logoutButton.classList.remove("hidden");
  loginButton.disabled = true;

  if (canUseAdmin()) {
    adminPanel.classList.remove("hidden");
    userPanel.classList.add("hidden");
    replaceHash("#admin");
    loadLogs().catch(() => {});
  } else {
    adminPanel.classList.add("hidden");
    userPanel.classList.remove("hidden");
    replaceHash("#user");
    setStatus($("userStatus"), state.queryIdentity ? "正在查詢證書清單..." : "請重新登入並輸入名字與 ID。");
    if (state.queryIdentity) {
      loadCertificates().catch(() => {});
    }
  }
}

async function loginWithAccount(username, password) {
  const response = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  return parseJsonResponse(response);
}

async function loginWithIdentity(name, idNumber) {
  const response = await fetch("/auth/login/identity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, id_number: idNumber }),
  });
  return parseJsonResponse(response);
}

function finishLogin(payload, queryIdentity = null) {
  state.token = payload.access_token;
  state.currentUser = {
    username: payload.username,
    display_name: payload.display_name,
    role: payload.role,
  };
  state.queryIdentity = queryIdentity;
  localStorage.setItem("accessToken", state.token);
  localStorage.setItem("currentUser", JSON.stringify(state.currentUser));
  if (queryIdentity) {
    localStorage.setItem("queryIdentity", JSON.stringify(queryIdentity));
  } else {
    localStorage.removeItem("queryIdentity");
  }
  applyRoleView();
}

async function login() {
  const status = $("authStatus");
  const nameOrUsername = cleanLoginValue($("usernameInput").value);
  const idOrPassword = cleanLoginValue($("passwordInput").value);
  if (!nameOrUsername || !idOrPassword) {
    setStatus(status, "請輸入名字與 ID。", "error");
    return;
  }

  try {
    setStatus(status, "正在登入...");
    try {
      const payload = await loginWithAccount(nameOrUsername, idOrPassword);
      finishLogin(payload);
    } catch {
      const queryIdentity = { name: nameOrUsername, id_number: idOrPassword.toUpperCase() };
      const payload = await loginWithIdentity(queryIdentity.name, queryIdentity.id_number);
      finishLogin(payload, queryIdentity);
    }
  } catch (error) {
    setStatus(status, error.message, "error");
  }
}

function logout() {
  state.token = null;
  state.currentUser = null;
  state.queryIdentity = null;
  state.certificates = [];
  localStorage.removeItem("accessToken");
  localStorage.removeItem("currentUser");
  localStorage.removeItem("queryIdentity");
  $("usernameInput").value = "";
  $("passwordInput").value = "";
  renderCertificates([]);
  applyRoleView();
}

function renderPreviewTable(rows) {
  const table = $("previewTable");
  const thead = table.querySelector("thead");
  const tbody = table.querySelector("tbody");
  thead.innerHTML = "";
  tbody.innerHTML = "";

  if (!rows.length) {
    tbody.innerHTML = '<tr><td>沒有可預覽資料</td></tr>';
    return;
  }

  const columns = Object.keys(rows[0]);
  const columnLabels = {
    user_id: "查詢 ID",
    national_id: "完整 ID",
    name: "姓名",
    certificate_name: "活動",
    issue_date: "日期",
    certificate_id: "證書字號",
    course_name: "種類",
    completion_date: "完成日期",
    note: "備註 / 時數",
    source_sheet: "來源工作表",
  };
  const headerRow = document.createElement("tr");
  columns.forEach((column) => {
    const th = document.createElement("th");
    th.textContent = columnLabels[column] || column;
    th.title = column;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((column) => {
      const td = document.createElement("td");
      td.textContent = row[column] ?? "";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

function renderLogs(logs) {
  const list = $("logsList");
  list.innerHTML = "";

  if (!logs.length) {
    list.textContent = "目前沒有操作紀錄。";
    return;
  }

  logs.forEach((log) => {
    const item = document.createElement("div");
    item.className = "log-item";
    item.innerHTML = `
      <strong>${log.action} - ${log.status}</strong>
      <span>${log.filename || "無檔案"} · ${new Date(log.created_at).toLocaleString()}</span>
      <span>${log.detail || ""}</span>
    `;
    list.appendChild(item);
  });
}

function renderCertificates(certificates) {
  const list = $("certificateList");
  list.innerHTML = "";
  state.certificates = certificates;

  if (!certificates.length) {
    list.textContent = "目前沒有可產生的證書。";
    return;
  }

  certificates.forEach((certificate) => {
    const item = document.createElement("label");
    item.className = "certificate-item";
    item.innerHTML = `
      <input type="checkbox" value="${certificate.record_id}" />
      <div>
        <strong>${certificate.certificate_name}</strong>
        <div class="certificate-meta">
          發證日期：${certificate.issue_date}
          ${certificate.course_name ? ` · 課程：${certificate.course_name}` : ""}
          ${certificate.note ? ` · 備註：${certificate.note}` : ""}
        </div>
      </div>
    `;
    list.appendChild(item);
  });
}

async function previewExcel() {
  const status = $("adminStatus");
  try {
    setStatus(status, "正在讀取 Excel 預覽...");
    const response = await apiFetch("/admin/excel/preview?limit=10", {
      method: "POST",
      body: buildFileForm(getExcelFile()),
    });
    const payload = await parseJsonResponse(response);
    renderPreviewTable(payload.rows);
    const type = payload.validation.is_valid ? "success" : "error";
    setStatus(status, `預覽完成，共 ${payload.validation.row_count} 筆，錯誤 ${payload.validation.errors.length} 筆。`, type);
  } catch (error) {
    setStatus(status, error.message, "error");
  }
}

async function uploadExcel() {
  const status = $("adminStatus");
  try {
    setStatus(status, "正在上傳 Excel...");
    const response = await apiFetch("/admin/excel/upload", {
      method: "POST",
      body: buildFileForm(getExcelFile()),
    });
    const payload = await parseJsonResponse(response);
    if (payload.saved_filename) {
      $("savedFilenameInput").value = payload.saved_filename;
    }
    const type = payload.uploaded ? "success" : "error";
    setStatus(status, payload.uploaded ? `上傳成功：${payload.saved_filename}` : "上傳失敗，請查看驗證錯誤。", type);
    await loadLogs();
  } catch (error) {
    setStatus(status, error.message, "error");
  }
}

async function importExcel() {
  const status = $("adminStatus");
  try {
    setStatus(status, "正在匯入 Excel...");
    const response = await apiFetch("/admin/excel/import", {
      method: "POST",
      body: buildFileForm(getExcelFile()),
    });
    const payload = await parseJsonResponse(response);
    const type = payload.imported ? "success" : "error";
    setStatus(status, payload.imported ? `匯入成功：新增 ${payload.inserted_count} 筆，更新 ${payload.updated_count} 筆。` : "匯入失敗。", type);
    await loadLogs();
  } catch (error) {
    setStatus(status, error.message, "error");
  }
}

async function previewSavedExcel() {
  const status = $("adminStatus");
  const filename = $("savedFilenameInput").value.trim();
  if (!filename) {
    setStatus(status, "請先輸入保存檔名。", "error");
    return;
  }

  try {
    setStatus(status, "正在讀取已上傳檔案...");
    const response = await apiFetch(`/admin/excel/uploads/${encodeURIComponent(filename)}/preview?limit=10`);
    const payload = await parseJsonResponse(response);
    renderPreviewTable(payload.rows);
    setStatus(status, `已上傳檔案預覽完成：${payload.preview_count} 筆。`, payload.validation.is_valid ? "success" : "error");
  } catch (error) {
    setStatus(status, error.message, "error");
  }
}

async function importSavedExcel() {
  const status = $("adminStatus");
  const filename = $("savedFilenameInput").value.trim();
  if (!filename) {
    setStatus(status, "請先輸入保存檔名。", "error");
    return;
  }

  try {
    setStatus(status, "正在匯入已上傳檔案...");
    const response = await apiFetch(`/admin/excel/uploads/${encodeURIComponent(filename)}/import`, {
      method: "POST",
    });
    const payload = await parseJsonResponse(response);
    setStatus(status, payload.imported ? `匯入成功：處理 ${payload.processed_count} 筆。` : "匯入失敗。", payload.imported ? "success" : "error");
    await loadLogs();
  } catch (error) {
    setStatus(status, error.message, "error");
  }
}

async function loadLogs() {
  if (!canUseAdmin()) {
    renderLogs([]);
    return;
  }
  const response = await apiFetch("/admin/logs?limit=10");
  const payload = await parseJsonResponse(response);
  renderLogs(payload.logs);
}

function userPayload() {
  const name = state.queryIdentity?.name?.trim();
  const idNumber = state.queryIdentity?.id_number?.trim();
  if (!name || !idNumber) {
    throw new Error("請重新登入並輸入名字與 ID。");
  }
  return { name, id_number: idNumber };
}

async function loadCertificates() {
  const status = $("userStatus");
  try {
    setStatus(status, "正在查詢證書清單...");
    const response = await apiFetch("/certificates/available", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(userPayload()),
    });
    const payload = await parseJsonResponse(response);
    renderCertificates(payload.certificates);
    setStatus(status, payload.message, payload.verified ? "success" : "error");
  } catch (error) {
    setStatus(status, error.message, "error");
  }
}

function selectedRecordIds() {
  return Array.from($("certificateList").querySelectorAll("input[type='checkbox']:checked")).map((input) => Number(input.value));
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function filenameFromDisposition(disposition) {
  const match = /filename="?([^"]+)"?/i.exec(disposition || "");
  return match ? match[1] : "certificates";
}

function setButtonLoading(button, isLoading, loadingText) {
  if (isLoading) {
    button.dataset.originalText = button.textContent;
    button.disabled = true;
    button.innerHTML = `<span class="button-spinner" aria-hidden="true"></span>${loadingText}`;
    return;
  }

  button.disabled = false;
  button.textContent = button.dataset.originalText || button.textContent;
  delete button.dataset.originalText;
}

async function generateCertificates() {
  const status = $("userStatus");
  const generateButton = $("generateButton");
  try {
    const recordIds = selectedRecordIds();
    if (!recordIds.length) {
      throw new Error("請至少勾選一份證書。");
    }

    setButtonLoading(generateButton, true, "產生中...");
    setStatus(status, "正在產生 PDF...");
    const response = await apiFetch("/certificates/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...userPayload(), record_ids: recordIds }),
    });

    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "產生 PDF 失敗。");
    }

    const blob = await response.blob();
    const filename = filenameFromDisposition(response.headers.get("content-disposition"));
    downloadBlob(blob, filename);
    setStatus(status, `已產生並下載 PDF：${filename}`, "success");
    await loadLogs();
  } catch (error) {
    setStatus(status, error.message, "error");
  } finally {
    setButtonLoading(generateButton, false);
  }
}

function bindEvents() {
  $("loginButton").addEventListener("click", login);
  $("usernameInput").addEventListener("input", () => setStatus($("authStatus"), "請輸入名字與 ID。"));
  $("passwordInput").addEventListener("input", () => setStatus($("authStatus"), "請輸入名字與 ID。"));
  $("logoutButton").addEventListener("click", logout);
  $("previewExcelButton").addEventListener("click", previewExcel);
  $("uploadExcelButton").addEventListener("click", uploadExcel);
  $("importExcelButton").addEventListener("click", importExcel);
  $("previewSavedButton").addEventListener("click", previewSavedExcel);
  $("importSavedButton").addEventListener("click", importSavedExcel);
  $("refreshLogsButton").addEventListener("click", loadLogs);
  $("loadCertificatesButton").addEventListener("click", loadCertificates);
  $("generateButton").addEventListener("click", generateCertificates);
}

bindEvents();
applyRoleView();
