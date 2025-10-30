(() => {
  // ---- Элементы DOM ----
  const categoryForm = document.getElementById("category-form");
  const categoryList = document.getElementById("category-list");
  const productForm = document.getElementById("product-form");
  const productList = document.getElementById("product-list");
  const productCategory = document.getElementById("product-category");

  const previewInput = document.getElementById("product-preview");
  const imagesInput = document.getElementById("product-images");
  const previewContainer = document.getElementById("preview-container");
  const imagesContainer = document.getElementById("images-container");

  const attributesContainer = document.getElementById("attributes-container");
  const addAttributeBtn = document.getElementById("add-attribute-btn");

  // ---- Состояние файлов ----
  let previewFile = null;
  let imagesFiles = [];
  let categories = window.INITIAL_CATEGORIES || [];

  // ---- Drag & Drop переменные ----
  let draggedElement = null;

  // ---- Утилиты ----
  function createAttributeInput(value = "") {
    const wrapper = document.createElement("div");
    wrapper.classList.add("attribute-wrapper");

    const input = document.createElement("input");
    input.type = "text";
    input.name = "attribute";
    input.placeholder = "Attribute (e.g., color: red)";
    input.value = value;

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.textContent = "×";
    delBtn.classList.add("delete-btn");
    delBtn.onclick = () => wrapper.remove();

    wrapper.appendChild(input);
    wrapper.appendChild(delBtn);
    return wrapper;
  }

  function clearAndAddInitialAttribute() {
    if (!attributesContainer.querySelector('input[name="attribute"]')) {
      attributesContainer.appendChild(createAttributeInput());
    }
  }

  // ---- Превью preview ----
  previewInput.addEventListener("change", (e) => {
    previewFile = e.target.files[0] || null;
    previewContainer.innerHTML = "";
    if (!previewFile) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
      const img = document.createElement("img");
      img.src = ev.target.result;
      img.classList.add("preview-img");

      const delBtn = document.createElement("button");
      delBtn.textContent = "×";
      delBtn.classList.add("delete-btn");
      delBtn.onclick = () => {
        previewFile = null;
        previewInput.value = "";
        previewContainer.innerHTML = "";
      };

      const wrapper = document.createElement("div");
      wrapper.classList.add("img-wrapper");
      wrapper.appendChild(img);
      wrapper.appendChild(delBtn);
      previewContainer.appendChild(wrapper);
    };
    reader.readAsDataURL(previewFile);
  });

  // ---- Дополнительные изображения (накопление и превью) ----
  imagesInput.addEventListener("change", (e) => {
    const newFiles = Array.from(e.target.files || []);
    if (newFiles.length === 0) return;

    imagesFiles = imagesFiles.concat(newFiles);
    imagesInput.value = "";
    renderImagesPreviews();
  });

  function renderImagesPreviews() {
    imagesContainer.innerHTML = "";
    imagesFiles.forEach((file, index) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const img = document.createElement("img");
        img.src = ev.target.result;
        img.classList.add("preview-img");

        const delBtn = document.createElement("button");
        delBtn.textContent = "×";
        delBtn.classList.add("delete-btn");
        delBtn.onclick = () => {
          imagesFiles.splice(index, 1);
          renderImagesPreviews();
        };

        const wrapper = document.createElement("div");
        wrapper.classList.add("img-wrapper");
        wrapper.appendChild(img);
        wrapper.appendChild(delBtn);
        imagesContainer.appendChild(wrapper);
      };
      reader.readAsDataURL(file);
    });
  }

  // ---- Динамические атрибуты ----
  addAttributeBtn.addEventListener("click", () => {
    attributesContainer.appendChild(createAttributeInput());
  });
  clearAndAddInitialAttribute();

  // ---- Отправка формы товара через JS (FormData) ----
  productForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = (document.getElementById("product-name") || {}).value || "";
    const category = (productCategory || {}).value || "";
    const description =
      (document.getElementById("product-description") || {}).value || "";
    if (!name.trim() || !category.trim()) {
      alert("Введите название и категорию");
      return;
    }

    const fd = new FormData();
    fd.append("product-name", name.trim());
    fd.append("product-category", category.trim());
    fd.append("product-description", description.trim());

    const attributeInputs = attributesContainer.querySelectorAll(
      'input[name="attribute"]'
    );
    attributeInputs.forEach((inp) => {
      const v = (inp.value || "").trim();
      if (v) fd.append("attribute", v);
    });

    if (previewFile) {
      fd.append("product-preview", previewFile, previewFile.name);
    }

    imagesFiles.forEach((file) => {
      fd.append("product-images", file, file.name);
    });

    try {
      const resp = await fetch(productForm.action, {
        method: "POST",
        body: fd,
        credentials: "same-origin",
      });

      if (resp.redirected) {
        window.location = resp.url;
        return;
      }

      const text = await resp.text();
      console.log("add-product server response:", resp.status, text);

      productForm.reset();
      previewContainer.innerHTML = "";
      imagesContainer.innerHTML = "";
      imagesFiles = [];
      previewFile = null;
      attributesContainer.innerHTML = "";
      attributesContainer.appendChild(createAttributeInput());

      alert("Product uploaded (check server console/log for details).");
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Ошибка при загрузке. Посмотрите консоль.");
    }
  });

  // ---- Функции для категорий ----
  function buildImageNode(cat) {
    if (cat.image_path) {
      const img = document.createElement("img");
      img.className = "category-thumb";
      img.src =
        cat.image_url ||
        (cat.image_path.startsWith("/")
          ? cat.image_path
          : `/static/${cat.image_path}`);
      img.alt = cat.name;
      img.onerror = () => {
        img.replaceWith(makeNoThumb());
      };
      return img;
    } else {
      return makeNoThumb();
    }
  }

  function makeNoThumb() {
    const div = document.createElement("div");
    div.className = "no-thumb";
    div.textContent = "Нет фото";
    return div;
  }

  function makeCategoryRow(cat) {
    const row = document.createElement("div");
    row.className = "category-row";
    row.dataset.name = cat.name;
    row.draggable = true;

    // Drag & Drop обработчики
    row.addEventListener("dragstart", handleDragStart);
    row.addEventListener("dragover", handleDragOver);
    row.addEventListener("drop", handleDrop);
    row.addEventListener("dragend", handleDragEnd);
    row.addEventListener("dragenter", handleDragEnter);
    row.addEventListener("dragleave", handleDragLeave);

    const imgNode = buildImageNode(cat);
    const name = document.createElement("div");
    name.className = "category-name";
    name.textContent = cat.name;

    // Добавим индикатор для перетаскивания
    const dragHandle = document.createElement("div");
    dragHandle.className = "drag-handle";
    dragHandle.innerHTML = "☰";
    dragHandle.style.cssText =
      "cursor: grab; padding: 0 8px; color: #666; font-size: 18px;";

    const actions = document.createElement("div");
    actions.className = "category-actions";

    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.className = "upload-input";

    const label = document.createElement("label");
    label.className = "upload-label";
    label.textContent = "Завантажити зображення";
    label.title = "Загрузить новое изображение";
    label.style.cursor = "pointer";
    label.appendChild(input);

    const status = document.createElement("div");
    status.className = "upload-status";
    status.textContent = "";

    const delBtn = document.createElement("button");
    delBtn.className = "delete-btn";
    delBtn.textContent = "Видалити категорію";
    delBtn.title = "Удалить категорию";

    input.addEventListener("change", async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      status.textContent = "Uploading...";
      try {
        const fd = new FormData();
        fd.append("category_name", cat.name);
        fd.append("image", file);

        const resp = await fetch(window.URLS.upload_category_image, {
          method: "POST",
          body: fd,
          credentials: "same-origin",
        });

        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(`Server error: ${resp.status} ${text}`);
        }

        const data = await resp.json();
        const newUrl =
          data.image_url ||
          (data.image_path ? `/static/${data.image_path}` : null);
        if (newUrl) {
          const newImg = document.createElement("img");
          newImg.className = "category-thumb";
          newImg.src = newUrl + `?v=${Date.now()}`;
          newImg.alt = cat.name;
          newImg.onerror = () => {
            newImg.replaceWith(makeNoThumb());
          };

          if (imgNode.parentElement) {
            imgNode.replaceWith(newImg);
          } else {
            row.insertBefore(newImg, name);
          }
          cat.image_path = data.image_path || cat.image_path;
          cat.image_url = newUrl;
          status.textContent = "Updated";
        } else {
          status.textContent = "Uploaded (no URL)";
        }
      } catch (err) {
        console.error(err);
        status.textContent = "Upload failed";
        alert("Не удалось загрузить изображение: " + err.message);
      } finally {
        input.value = "";
        setTimeout(() => {
          status.textContent = "";
        }, 2500);
      }
    });

    delBtn.addEventListener("click", async () => {
      if (!confirm(`Удалить категорию "${cat.name}"?`)) return;
      try {
        const resp = await fetch(window.URLS.delete_category, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: cat.name }),
          credentials: "same-origin",
        });
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(`Server error: ${resp.status} ${text}`);
        }
        const data = await resp.json();
        if (data.success) {
          const idx = categories.findIndex((c) => c.name === cat.name);
          if (idx !== -1) categories.splice(idx, 1);
          row.remove();
          const opt = Array.from(productCategory.options).find(
            (o) => o.value === cat.name
          );
          if (opt) opt.remove();
        } else {
          throw new Error(data.error || "Unknown");
        }
      } catch (err) {
        console.error(err);
        alert("Ошибка при удалении: " + err.message);
      }
    });

    actions.appendChild(label);
    actions.appendChild(status);
    actions.appendChild(delBtn);

    row.appendChild(dragHandle);
    row.appendChild(imgNode);
    row.appendChild(name);
    row.appendChild(actions);

    return row;
  }

  // ---- Drag & Drop обработчики ----
  function handleDragStart(e) {
    draggedElement = this;
    this.style.opacity = "0.4";
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/html", this.innerHTML);
  }

  function handleDragOver(e) {
    if (e.preventDefault) {
      e.preventDefault();
    }
    e.dataTransfer.dropEffect = "move";
    return false;
  }

  function handleDragEnter(e) {
    if (this !== draggedElement) {
      this.classList.add("drag-over");
    }
  }

  function handleDragLeave(e) {
    this.classList.remove("drag-over");
  }

  function handleDrop(e) {
    if (e.stopPropagation) {
      e.stopPropagation();
    }

    if (draggedElement !== this) {
      // Получаем все строки категорий
      const allRows = Array.from(
        categoryList.querySelectorAll(".category-row")
      );
      const draggedIndex = allRows.indexOf(draggedElement);
      const targetIndex = allRows.indexOf(this);

      // Переставляем в DOM
      if (draggedIndex < targetIndex) {
        this.parentNode.insertBefore(draggedElement, this.nextSibling);
      } else {
        this.parentNode.insertBefore(draggedElement, this);
      }

      // Обновляем порядок на сервере
      saveNewOrder();
    }

    this.classList.remove("drag-over");
    return false;
  }

  function handleDragEnd(e) {
    this.style.opacity = "1";
    const allRows = categoryList.querySelectorAll(".category-row");
    allRows.forEach((row) => {
      row.classList.remove("drag-over");
    });
  }

  // Сохранение нового порядка на сервере
  async function saveNewOrder() {
    const allRows = Array.from(categoryList.querySelectorAll(".category-row"));
    const order = allRows.map((row) => row.dataset.name);

    try {
      const resp = await fetch(window.URLS.reorder_categories, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ order }),
        credentials: "same-origin",
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`Server error: ${resp.status} ${text}`);
      }

      const data = await resp.json();
      console.log("Order updated:", data);
    } catch (err) {
      console.error("Failed to save order:", err);
      alert("Не удалось сохранить порядок категорий");
    }
  }

  function renderCategories() {
    categoryList.innerHTML = "";
    while (productCategory.options.length > 1) productCategory.remove(1);

    // Сортируем по tier
    const sortedCategories = [...categories].sort(
      (a, b) => (a.tier || 0) - (b.tier || 0)
    );

    sortedCategories.forEach((cat) => {
      const row = makeCategoryRow(cat);
      categoryList.appendChild(row);

      const opt = document.createElement("option");
      opt.value = cat.name;
      opt.textContent = cat.name;
      productCategory.appendChild(opt);
    });
  }

  // Добавление категории
  categoryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("category-name");
    const name = input.value.trim();
    if (!name) return;
    try {
      const resp = await fetch(window.URLS.add_category, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
        credentials: "same-origin",
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || "Add failed");
      }
      const newCat = await resp.json();
      categories.push(newCat);
      renderCategories();
      input.value = "";
    } catch (err) {
      console.error(err);
      alert("Не удалось добавить категорию: " + err.message);
    }
  });

  // Инициализация
  document.addEventListener("DOMContentLoaded", () => {
    categories = window.INITIAL_CATEGORIES || [];
    renderCategories();
  });
})();
