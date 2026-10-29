// Simulador do FourPC.
// O JavaScript só mostra as peças e guarda o que foi escolhido. As regras
// de compatibilidade e as contas (total, PIX, energia) vêm todas da API, que
// usa o mesmo código do programa de terminal (pasta core/).

const EXTRA_STORAGE = "extra_storage";
// chave onde a montagem fica guardada no navegador
const STORAGE_KEY = "fourpc:montagem";

// texto e cor da etiqueta de cada status que a API devolve
const STATUS_TAGS = {
  fail: { text: "Erro", className: "tag-fail" },
  warning: { text: "Aviso", className: "tag-warning" },
  ok: { text: "OK", className: "tag-ok" },
  pending: { text: "Pendente", className: "tag-pending" },
};

// no painel de compatibilidade os erros aparecem primeiro
const STATUS_ORDER = { fail: 0, warning: 1, ok: 2, pending: 3 };

// o que a pessoa escolheu: { cpu: "cpu-r5-7600", ... } + o segundo disco
const state = {
  components: {},
  extraStorage: null,
};

let catalog = [];
// cada validação ganha um número; se chegar uma resposta antiga depois de
// uma mais nova (clicando rápido), ela é ignorada
let lastRequest = 0;

const elements = {
  categories: document.getElementById("categorias"),
  parts: document.getElementById("resumo-pecas"),
  total: document.getElementById("resumo-total"),
  status: document.getElementById("resumo-status"),
  error: document.getElementById("erro"),
  payment: document.getElementById("painel-pagamento"),
  power: document.getElementById("painel-energia"),
  rules: document.getElementById("painel-regras"),
  presetsSection: document.getElementById("montagens-prontas"),
  presets: document.getElementById("presets"),
  clear: document.getElementById("limpar"),
};

// cria um elemento com classe e texto (textContent evita injetar HTML)
function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (text !== undefined) {
    element.textContent = text;
  }
  return element;
}

function showError(message) {
  elements.error.textContent = message;
  elements.error.hidden = false;
}

function hideError() {
  elements.error.hidden = true;
}

async function loadCatalog() {
  const response = await fetch("/api/catalogo");
  if (!response.ok) {
    throw new Error("Não foi possível carregar o catálogo de peças.");
  }
  const data = await response.json();
  return data.categories;
}

// uma opção da lista: um radio dentro de um label, assim clicar em qualquer
// lugar do cartão escolhe a peça
function renderOption(groupName, component) {
  const label = createElement("label", "option");
  label.dataset.id = component.id;

  const input = document.createElement("input");
  input.type = "radio";
  input.name = groupName;
  input.value = component.id;

  const info = createElement("span", "option-info");
  info.append(
    createElement("span", "option-name", component.name),
    createElement("span", "option-specs", component.specs),
  );

  label.append(input, info, createElement("span", "option-price", component.price_formatted));
  return label;
}

function renderNoneOption(groupName) {
  const label = createElement("label", "option option-none");
  const input = document.createElement("input");
  input.type = "radio";
  input.name = groupName;
  input.value = "";
  input.checked = true;
  label.append(input, createElement("span", "option-name", "Nenhum"));
  return label;
}

function renderCategory(groupName, title, components, isExtra) {
  const fieldset = createElement("fieldset", "category card");
  fieldset.dataset.group = groupName;
  fieldset.append(createElement("legend", "category-title", title));
  if (isExtra) {
    fieldset.append(createElement(
      "p",
      "category-hint muted",
      "Opcional. Escolha primeiro o disco principal.",
    ));
  }

  const list = createElement("div", "options");
  if (isExtra) {
    list.append(renderNoneOption(groupName));
  }
  for (const component of components) {
    list.append(renderOption(groupName, component));
  }
  fieldset.append(list);
  return fieldset;
}

function renderCategories() {
  elements.categories.replaceChildren();
  for (const category of catalog) {
    elements.categories.append(renderCategory(
      category.category, category.label, category.components, false,
    ));
    // o segundo disco usa as mesmas peças do armazenamento
    if (category.category === "storage") {
      elements.categories.append(renderCategory(
        EXTRA_STORAGE, "Segundo disco", category.components, true,
      ));
    }
  }
}

// o segundo disco só pode ser escolhido depois do disco principal
function updateExtraStorageAvailability() {
  const fieldset = elements.categories.querySelector(
    `[data-group="${EXTRA_STORAGE}"]`,
  );
  if (fieldset) {
    fieldset.disabled = !state.components.storage;
  }
}

function onChoice(event) {
  const input = event.target;
  if (input.type !== "radio") {
    return;
  }
  if (input.name === EXTRA_STORAGE) {
    state.extraStorage = input.value || null;
  } else {
    state.components[input.name] = input.value;
  }
  updateExtraStorageAvailability();
  saveState();
  refresh();
}

function hasChoices() {
  return Object.keys(state.components).length > 0 || state.extraStorage !== null;
}

// deixa os radios marcados de acordo com o state (usado quando a montagem
// muda sem a pessoa clicar: montagem pronta, limpar ou montagem salva)
function syncInputs() {
  for (const input of elements.categories.querySelectorAll('input[type="radio"]')) {
    if (input.name === EXTRA_STORAGE) {
      input.checked = input.value === (state.extraStorage || "");
    } else {
      input.checked = input.value === state.components[input.name];
    }
  }
}

function applyBuild(components, extraStorage) {
  state.components = { ...components };
  state.extraStorage = extraStorage || null;
  syncInputs();
  updateExtraStorageAvailability();
  saveState();
  refresh();
}

// Guarda a montagem no navegador. Se o navegador bloquear (em aba anônima,
// por exemplo), o simulador funciona igual, só não lembra da montagem.
function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // sem localStorage, segue sem salvar
  }
}

// IDs de peça que existem no catálogo, por grupo
function catalogIds(group) {
  const key = group === EXTRA_STORAGE ? "storage" : group;
  const category = catalog.find((item) => item.category === key);
  return new Set(category ? category.components.map((c) => c.id) : []);
}

// Lê a montagem salva. Peças que não existem mais no catálogo (ou um
// segundo disco sem disco principal) são deixadas de fora.
function loadSavedState() {
  let saved;
  try {
    saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
  } catch {
    return null;
  }
  if (!saved || typeof saved.components !== "object" || saved.components === null) {
    return null;
  }
  const components = {};
  for (const [group, id] of Object.entries(saved.components)) {
    if (catalogIds(group).has(id)) {
      components[group] = id;
    }
  }
  let extraStorage = saved.extraStorage;
  if (!components.storage || !catalogIds(EXTRA_STORAGE).has(extraStorage)) {
    extraStorage = null;
  }
  return { components, extraStorage };
}

async function loadPresets() {
  const response = await fetch("/api/presets");
  if (!response.ok) {
    return [];
  }
  return response.json();
}

function choosePreset(preset) {
  if (hasChoices() && !confirm(`Trocar a montagem atual pela montagem ${preset.name}?`)) {
    return;
  }
  applyBuild(preset.components, preset.extra_storage);
}

// sem montagens prontas o simulador funciona igual, a seção só fica escondida
function renderPresets(presets) {
  if (presets.length === 0) {
    return;
  }
  for (const preset of presets) {
    const button = createElement("button", "button button-secondary preset-button");
    button.type = "button";
    button.title = preset.description;
    button.append(
      createElement("span", "preset-name", preset.name),
      createElement("span", "preset-total", preset.total_formatted),
    );
    button.addEventListener("click", () => choosePreset(preset));
    elements.presets.append(button);
  }
  elements.presetsSection.hidden = false;
}

function clearBuild() {
  if (!hasChoices() || !confirm("Limpar todas as peças escolhidas?")) {
    return;
  }
  applyBuild({}, null);
}

// as duas rotas de montagem recebem a mesma coisa
async function postBuild(url) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      components: state.components,
      extra_storage: state.extraStorage,
    }),
  });
  const data = await response.json();
  if (!response.ok) {
    // o 422 da API já vem com a mensagem em português
    throw new Error(typeof data.detail === "string"
      ? data.detail
      : "A API não aceitou a montagem.");
  }
  return data;
}

function renderSummary(result) {
  elements.parts.replaceChildren();
  if (result.components.length === 0) {
    elements.parts.append(createElement("li", "muted", "Nenhuma peça escolhida ainda."));
  }
  for (const component of result.components) {
    const item = createElement("li", "summary-item");
    const info = createElement("span", "summary-info");
    info.append(
      createElement("span", "summary-label", component.category_label),
      createElement("span", "summary-name", component.name),
    );
    item.append(info, createElement("span", "summary-price", component.price_formatted));
    elements.parts.append(item);
  }
  elements.total.textContent = result.payment.total_formatted;
  elements.status.textContent = result.status_message;
}

// lista de "nome: valor" usada nos painéis de pagamento e energia
function renderRows(container, rows) {
  const list = createElement("dl", "panel-list");
  for (const [label, value] of rows) {
    const row = createElement("div", "panel-row");
    row.append(createElement("dt", "", label), createElement("dd", "", value));
    list.append(row);
  }
  container.replaceChildren(list);
}

function renderPayment(payment) {
  renderRows(elements.payment, [
    [`À vista no PIX (${payment.pix_discount_percent}% de desconto)`, payment.pix_price_formatted],
    [`Ou em ${payment.installments}x sem juros de`, payment.installment_price_formatted],
  ]);
}

function renderPower(power) {
  if (!power) {
    elements.power.replaceChildren(createElement(
      "p",
      "muted",
      "Escolha o processador e a placa de vídeo para estimar o consumo.",
    ));
    return;
  }
  const hasPsu = power.psu_watts !== null;
  renderRows(elements.power, [
    ["Consumo estimado (CPU + GPU)", `${power.estimated_load_watts} W`],
    ["Fonte mínima recomendada", `${power.required_psu_watts} W`],
    ["Fonte escolhida", hasPsu ? `${power.psu_watts} W` : "-"],
    ["Folga da fonte", hasPsu ? `${power.psu_headroom_percent}%` : "-"],
  ]);
}

function renderRules(rules) {
  const sorted = [...rules].sort(
    (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status],
  );
  elements.rules.replaceChildren();
  for (const rule of sorted) {
    const tag = STATUS_TAGS[rule.status];
    const item = createElement("li", `rule-item rule-${rule.status}`);
    const header = createElement("div", "rule-header");
    header.append(
      createElement("span", `tag ${tag.className}`, tag.text),
      createElement("span", "rule-name", rule.rule),
    );
    item.append(header, createElement("p", "rule-message", rule.message));
    if (rule.hint && (rule.status === "fail" || rule.status === "warning")) {
      item.append(createElement("p", "rule-hint", `Sugestão: ${rule.hint}`));
    }
    elements.rules.append(item);
  }
}

// marca de vermelho as peças que dariam erro se fossem escolhidas agora
function renderConflicts(conflicts) {
  for (const option of elements.categories.querySelectorAll(".option[data-id]")) {
    const group = option.closest("fieldset").dataset.group;
    const rules = (conflicts[group] || {})[option.dataset.id];
    const info = option.querySelector(".option-info");

    info.querySelector(".option-conflict-text")?.remove();
    option.classList.toggle("option-conflict", Boolean(rules));
    if (rules) {
      info.append(createElement(
        "span",
        "option-conflict-text",
        `Incompatível: ${rules.join(", ")}`,
      ));
    }
  }
}

async function refresh() {
  const request = ++lastRequest;
  try {
    // as duas chamadas saem juntas pra não esperar uma pela outra
    const [result, conflicts] = await Promise.all([
      postBuild("/api/montagens/validar"),
      postBuild("/api/montagens/conflitos"),
    ]);
    if (request !== lastRequest) {
      return;
    }
    hideError();
    renderSummary(result);
    renderPayment(result.payment);
    renderPower(result.power);
    renderRules(result.rules);
    renderConflicts(conflicts.conflicts);
  } catch (error) {
    if (request === lastRequest) {
      showError(error.message);
    }
  }
}

async function start() {
  try {
    catalog = await loadCatalog();
  } catch (error) {
    elements.categories.replaceChildren(createElement("p", "error-message", error.message));
    return;
  }
  renderCategories();
  const saved = loadSavedState();
  if (saved) {
    state.components = saved.components;
    state.extraStorage = saved.extraStorage;
    syncInputs();
  }
  updateExtraStorageAvailability();
  elements.categories.addEventListener("change", onChoice);
  elements.clear.addEventListener("click", clearBuild);
  refresh();
  loadPresets().then(renderPresets).catch(() => {});
}

start();
