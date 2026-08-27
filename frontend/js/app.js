// nginx가 method 기준(map $request_method)으로 /api/books를
// command-service/query-service에 나눠 프록시하므로 같은 origin의 상대경로만 쓰면 된다.
const QUERY_API_BASE = "";
const COMMAND_API_BASE = "";

const CATEGORIES = [
  "IT",
  "경제경영",
  "과학",
  "소설",
  "에세이",
  "여행",
  "역사",
  "예술",
  "인문",
  "자기계발",
];

const PAGE_SIZE = 10;

const state = {
  page: 0,
  totalPages: 0,
  filters: { title: "", category: "", author: "", publisher: "" },
  editingId: null,
};

const el = {
  searchForm: document.getElementById("search-form"),
  searchCategory: document.getElementById("search-category"),
  resetSearch: document.getElementById("reset-search"),
  searchError: document.getElementById("search-error"),

  createButton: document.getElementById("create-button"),
  formSection: document.getElementById("form-section"),
  formTitle: document.getElementById("form-title"),
  bookForm: document.getElementById("book-form"),
  formCategory: document.getElementById("form-category"),
  formSubmit: document.getElementById("form-submit"),
  formCancel: document.getElementById("form-cancel"),
  formError: document.getElementById("form-error"),

  resultsTable: document.getElementById("results-table"),
  resultsBody: document.getElementById("results-body"),
  emptyState: document.getElementById("empty-state"),

  prevPage: document.getElementById("prev-page"),
  nextPage: document.getElementById("next-page"),
  pageInfo: document.getElementById("page-info"),
};

function populateCategoryOptions() {
  for (const select of [el.searchCategory, el.formCategory]) {
    for (const category of CATEGORIES) {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      select.appendChild(option);
    }
  }
}

function showError(target, message) {
  target.textContent = message;
  target.hidden = false;
}

function hideError(target) {
  target.hidden = true;
}

async function parseErrorMessage(response) {
  try {
    const body = await response.json();
    return body.message || `요청이 실패했습니다 (${response.status})`;
  } catch {
    return `요청이 실패했습니다 (${response.status})`;
  }
}

async function fetchBooks() {
  hideError(el.searchError);

  const params = new URLSearchParams({ page: String(state.page), size: String(PAGE_SIZE) });
  if (state.filters.title) params.set("title", state.filters.title);
  if (state.filters.category) params.set("category", state.filters.category);
  if (state.filters.author) params.set("author", state.filters.author);
  if (state.filters.publisher) params.set("publisher", state.filters.publisher);

  let response;
  try {
    response = await fetch(`${QUERY_API_BASE}/api/books/search?${params}`);
  } catch {
    showError(el.searchError, "검색 서비스에 연결할 수 없습니다. query-service가 실행 중인지 확인해주세요.");
    return;
  }

  if (!response.ok) {
    showError(el.searchError, await parseErrorMessage(response));
    return;
  }

  const data = await response.json();
  state.totalPages = data.total_pages;
  renderResults(data);
}

function renderResults(data) {
  el.resultsBody.replaceChildren();
  const hasResults = data.content.length > 0;
  el.emptyState.hidden = hasResults;
  el.resultsTable.hidden = !hasResults;

  for (const book of data.content) {
    el.resultsBody.appendChild(buildRow(book));
  }

  updatePaginationUI(data);
}

function buildRow(book) {
  const tr = document.createElement("tr");
  const values = [
    book.title,
    book.author,
    book.publisher,
    book.category,
    book.published_date,
    book.isbn,
    `${book.price.toLocaleString()}원`,
    String(book.stock),
  ];
  for (const value of values) {
    const td = document.createElement("td");
    td.textContent = value;
    tr.appendChild(td);
  }

  const actionsTd = document.createElement("td");

  const editBtn = document.createElement("button");
  editBtn.textContent = "수정";
  editBtn.addEventListener("click", () => startEdit(book));

  const deleteBtn = document.createElement("button");
  deleteBtn.textContent = "삭제";
  deleteBtn.className = "danger";
  deleteBtn.addEventListener("click", () => deleteBook(book.id, book.title));

  actionsTd.append(editBtn, deleteBtn);
  tr.appendChild(actionsTd);

  return tr;
}

function updatePaginationUI(data) {
  const totalPages = Math.max(data.total_pages, 1);
  el.pageInfo.textContent = `${data.total_elements}건 중 ${data.page + 1} / ${totalPages} 페이지`;
  el.prevPage.disabled = data.page <= 0;
  el.nextPage.disabled = data.page + 1 >= data.total_pages;
}

function showForm() {
  el.formSection.hidden = false;
  hideError(el.formError);
}

function closeForm() {
  el.formSection.hidden = true;
  el.bookForm.reset();
  state.editingId = null;
}

function startCreate() {
  state.editingId = null;
  el.formTitle.textContent = "새 도서 등록";
  el.formSubmit.textContent = "등록";
  el.bookForm.reset();
  showForm();
}

function startEdit(book) {
  state.editingId = book.id;
  el.formTitle.textContent = "도서 수정";
  el.formSubmit.textContent = "수정";

  const form = el.bookForm;
  form.title.value = book.title;
  form.author.value = book.author;
  form.publisher.value = book.publisher;
  form.category.value = book.category;
  form.published_date.value = book.published_date;
  form.isbn.value = book.isbn;
  form.price.value = book.price;
  form.stock.value = book.stock;

  showForm();
}

async function handleFormSubmit(event) {
  event.preventDefault();
  hideError(el.formError);

  const formData = new FormData(el.bookForm);
  const payload = {
    title: formData.get("title").trim(),
    author: formData.get("author").trim(),
    publisher: formData.get("publisher").trim(),
    category: formData.get("category"),
    published_date: formData.get("published_date"),
    isbn: formData.get("isbn").trim(),
    price: Number(formData.get("price")),
    stock: Number(formData.get("stock")),
  };

  const isEdit = state.editingId !== null;
  const url = isEdit
    ? `${COMMAND_API_BASE}/api/books/${state.editingId}`
    : `${COMMAND_API_BASE}/api/books`;

  let response;
  try {
    response = await fetch(url, {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    showError(el.formError, "등록 서비스에 연결할 수 없습니다. command-service가 실행 중인지 확인해주세요.");
    return;
  }

  if (!response.ok) {
    showError(el.formError, await parseErrorMessage(response));
    return;
  }

  closeForm();
  state.page = 0;
  await fetchBooks();
}

async function deleteBook(id, title) {
  if (!confirm(`"${title}"을(를) 삭제하시겠습니까?`)) return;

  let response;
  try {
    response = await fetch(`${COMMAND_API_BASE}/api/books/${id}`, { method: "DELETE" });
  } catch {
    alert("삭제 서비스에 연결할 수 없습니다. command-service가 실행 중인지 확인해주세요.");
    return;
  }

  if (!response.ok) {
    alert(await parseErrorMessage(response));
    return;
  }

  await fetchBooks();
}

function init() {
  populateCategoryOptions();

  el.searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(el.searchForm);
    state.filters = {
      title: formData.get("title").trim(),
      category: formData.get("category"),
      author: formData.get("author").trim(),
      publisher: formData.get("publisher").trim(),
    };
    state.page = 0;
    fetchBooks();
  });

  el.resetSearch.addEventListener("click", () => {
    el.searchForm.reset();
    state.filters = { title: "", category: "", author: "", publisher: "" };
    state.page = 0;
    fetchBooks();
  });

  el.createButton.addEventListener("click", startCreate);
  el.formCancel.addEventListener("click", closeForm);
  el.bookForm.addEventListener("submit", handleFormSubmit);

  el.prevPage.addEventListener("click", () => {
    if (state.page > 0) {
      state.page -= 1;
      fetchBooks();
    }
  });
  el.nextPage.addEventListener("click", () => {
    if (state.page + 1 < state.totalPages) {
      state.page += 1;
      fetchBooks();
    }
  });

  fetchBooks();
}

init();
