// Simulador do FourPC.
// O JavaScript só mostra as peças e guarda o que foi escolhido. As regras
// de compatibilidade e as contas (total, PIX, energia) vêm todas da API, que
// usa o mesmo código do programa de terminal (pasta core/).

const EXTRA_STORAGE = "extra_storage";

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
  refresh();
}

async function validateBuild() {
  const response = await fetch("/api/montagens/validar", {
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

async function refresh() {
  const request = ++lastRequest;
  try {
    const result = await validateBuild();
    if (request !== lastRequest) {
      return;
    }
    hideError();
    renderSummary(result);
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
  updateExtraStorageAvailability();
  elements.categories.addEventListener("change", onChoice);
  refresh();
}

start();
