/*
  admin-panel.js — обновлённый
  - показывает кнопку удаления возле каждой категории
  - при клике — окно подтверждения (window.confirm)
  - при подтверждении — отправка запроса на бекенд с именем категории
  - при успехе — удаление из UI (ul + select)
*/

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
  let imagesFiles = []; // массив File для дополнительных изображений

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

    // добавляем новые файлы в массив (не перезаписываем)
    imagesFiles = imagesFiles.concat(newFiles);

    // очищаем input, чтобы пользователь мог открывать диалог снова
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

  // ---- Вспомогательные функции для категорий ----

  // Создаёт <li> с текстом и кнопкой удаления
  function createCategoryListItem(name) {
    const li = document.createElement("li");
    li.classList.add("category-item");

    const textSpan = document.createElement("span");
    textSpan.classList.add("category-name");
    textSpan.textContent = name;

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.classList.add("delete-category-btn");
    delBtn.textContent = "Удалить";
    delBtn.dataset.categoryName = name;

    // при нажатии — подтверждение и запрос на бэкенд
    delBtn.addEventListener("click", async (e) => {
      const catName = e.currentTarget.dataset.categoryName;

      try {
        // Первая попытка — без cascade
        const resp = await fetch(window.URLS.delete_category, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ name: catName }),
        });

        const data = await resp.json().catch(() => null);

        if (!resp.ok) {
          // Если есть товары — предложить каскадное удаление
          if (data && data.products_count > 0) {
            const ok = window.confirm(
              `В категории "${catName}" есть ${data.products_count} товар(ов).\n\n` +
                `Удалить категорию вместе со ВСЕМИ товарами?\n` +
                `Это действие НЕЛЬЗЯ отменить!`
            );

            if (!ok) return;

            // Повторный запрос с cascade=true
            const resp2 = await fetch(window.URLS.delete_category, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              body: JSON.stringify({ name: catName, cascade: true }),
            });

            const data2 = await resp2.json().catch(() => null);

            if (!resp2.ok) {
              const msg =
                (data2 && (data2.error || data2.detail)) ||
                `Ошибка при удалении (status ${resp2.status})`;
              alert(msg);
              return;
            }

            // Успешное каскадное удаление
            if (li && li.parentNode) li.parentNode.removeChild(li);
            for (let i = productCategory.options.length - 1; i >= 0; i--) {
              if (productCategory.options[i].value === catName) {
                productCategory.remove(i);
                break;
              }
            }
            alert(
              `Категория "${catName}" и ${data2.deleted_products} товар(ов) удалены.`
            );
            return;
          }

          // Другая ошибка
          const msg =
            (data && (data.error || data.detail)) ||
            `Ошибка при удалении (status ${resp.status})`;
          alert(msg);
          return;
        }

        // Успешное удаление (категория была пустая)
        if (li && li.parentNode) li.parentNode.removeChild(li);
        for (let i = productCategory.options.length - 1; i >= 0; i--) {
          if (productCategory.options[i].value === catName) {
            productCategory.remove(i);
            break;
          }
        }
        alert(`Категория "${catName}" удалена.`);
      } catch (err) {
        console.error("Network/JS error while deleting category:", err);
        alert("Сетевая ошибка при удалении категории");
      }
    });

    li.appendChild(textSpan);
    li.appendChild(delBtn);
    return li;
  }

  // Добавляет опцию в select (если её ещё нет)
  function addCategoryOptionIfMissing(name) {
    if (![...productCategory.options].some((opt) => opt.value === name)) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      productCategory.appendChild(option);
    }
  }

  // ---- Добавление категории на сервер и обновление UI ----
  categoryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const nameInput = document.getElementById("category-name");
    const name = ((nameInput && nameInput.value) || "").trim();
    if (!name) return;

    try {
      const resp = await fetch(window.URLS.add_category, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ name }),
      });

      console.log("add-category status", resp.status);
      const data = await resp.json().catch(() => null);
      console.log("add-category body", data);

      if (!resp.ok) {
        const msg =
          (data && (data.error || data.detail)) ||
          "Ошибка при добавлении категории";
        alert(msg);
        return;
      }

      const addedName = data.name || name;

      // добавляем в список категорий (ul)
      // предотвращаем дубли по точному совпадению value/text
      if (
        ![...categoryList.children].some(
          (li) =>
            li.querySelector(".category-name") &&
            li.querySelector(".category-name").textContent === addedName
        )
      ) {
        const li = createCategoryListItem(addedName);
        categoryList.appendChild(li);
      }

      // добавляем в select, если нет
      addCategoryOptionIfMissing(addedName);

      categoryForm.reset();
    } catch (err) {
      console.error("Network/JS error while adding category:", err);
      alert("Network error while adding category");
    }
  });

  // ---- Инициализация UI при загрузке страницы: наполняем списки из Jinja-переменной ----
  document.addEventListener("DOMContentLoaded", () => {
    try {
      const initialCategories = window.INITIAL_CATEGORIES || [];
      categoryList.innerHTML = "";

      // Оставляем первый option (Select category) и удаляем остальные
      while (productCategory.options.length > 1) productCategory.remove(1);

      initialCategories.forEach((name) => {
        const li = createCategoryListItem(name);
        categoryList.appendChild(li);

        addCategoryOptionIfMissing(name);
      });
    } catch (e) {
      console.warn("Could not populate initial categories:", e);
    }
  });
})();

// admin-panel.js
document.addEventListener("DOMContentLoaded", () => {
  const categories = window.INITIAL_CATEGORIES || [];
  const list = document.getElementById("category-list");
  const productCategorySelect = document.getElementById("product-category");

  function buildImageNode(cat) {
    if (cat.image_path) {
      const img = document.createElement("img");
      img.className = "category-thumb";
      // если путь в БД уже относительный к static — используем url_for-like
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

    const imgNode = buildImageNode(cat);
    const name = document.createElement("div");
    name.className = "category-name";
    name.textContent = cat.name;

    const actions = document.createElement("div");
    actions.className = "category-actions";

    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.className = "upload-input";

    const label = document.createElement("label");
    label.className = "upload-label";
    label.textContent = "Upload";
    label.title = "Загрузить новое изображение";
    label.style.cursor = "pointer";
    label.appendChild(input);

    const status = document.createElement("div");
    status.className = "upload-status";
    status.textContent = "";

    // кнопка удалить категорию
    const delBtn = document.createElement("button");
    delBtn.className = "delete-btn";
    delBtn.textContent = "Delete";
    delBtn.title = "Удалить категорию";

    input.addEventListener("change", async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      status.textContent = "Uploading...";
      label.disabled = true;
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
          // заменяем картинку или блок "Нет фото"
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
            // fallback
            row.insertBefore(newImg, name);
          }
          // обновим ссылку/данные
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
      if (
        !confirm(
          `Удалить категорию "${cat.name}"? Это действие нельзя будет отменить.`
        )
      )
        return;
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
          // удалить из локального массива
          const idx = categories.findIndex((c) => c.name === cat.name);
          if (idx !== -1) categories.splice(idx, 1);
          // удалить DOM
          row.remove();
          // удалить опцию из select
          const opt = Array.from(productCategorySelect.options).find(
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

    row.appendChild(imgNode);
    row.appendChild(name);
    row.appendChild(actions);

    return row;
  }

  function renderCategories() {
    list.innerHTML = "";
    // очистим select (кроме первой опции)
    while (productCategorySelect.options.length > 1)
      productCategorySelect.remove(1);

    categories.forEach((cat) => {
      const row = makeCategoryRow(cat);
      list.appendChild(row);

      const opt = document.createElement("option");
      opt.value = cat.name;
      opt.textContent = cat.name;
      productCategorySelect.appendChild(opt);
    });
  }

  // Добавление категории (через add_category)
  const catForm = document.getElementById("category-form");
  catForm.addEventListener("submit", async (e) => {
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
      const newCat = await resp.json(); // ожидаем { name, image_path? }
      categories.push(newCat);
      renderCategories();
      input.value = "";
    } catch (err) {
      console.error(err);
      alert("Не удалось добавить категорию: " + err.message);
    }
  });

  renderCategories();
});
