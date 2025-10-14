/*
  Полностью обновлённый JavaScript для admin-panel.html
  - Управление категориями (загрузка, добавление на сервер)
  - Превью preview + дополнительные изображения (накопление)
  - Динамические атрибуты
  - Отправка формы товара через FormData (fetch)
*/
(() => {
  // ---- Элементы DOM ----
  const categoryForm = document.getElementById("category-form");
  const categoryList = document.getElementById("category-list");
  const productForm = document.getElementById("product-form");
  const productList = document.getElementById("product-list"); // не обязательно, но оставлено
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

    // валидация минимальная
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

    // атрибуты
    const attributeInputs = attributesContainer.querySelectorAll(
      'input[name="attribute"]'
    );
    attributeInputs.forEach((inp) => {
      const v = (inp.value || "").trim();
      if (v) fd.append("attribute", v);
    });

    // preview
    if (previewFile) {
      fd.append("product-preview", previewFile, previewFile.name);
    }

    // дополнительные изображения (всё из imagesFiles)
    imagesFiles.forEach((file) => {
      fd.append("product-images", file, file.name);
    });

    try {
      const resp = await fetch(productForm.action, {
        method: "POST",
        body: fd,
        credentials: "same-origin", // важно для сессии
      });

      // если сервер сделал редирект и вернул redirect URL
      if (resp.redirected) {
        window.location = resp.url;
        return;
      }

      const text = await resp.text(); // либо JSON, если сервер вернёт JSON
      console.log("add-product server response:", resp.status, text);

      // очистка состояния UI после успешной отправки
      productForm.reset();
      previewContainer.innerHTML = "";
      imagesContainer.innerHTML = "";
      imagesFiles = [];
      previewFile = null;
      // заново добавляем одно пустое поле атрибута
      attributesContainer.innerHTML = "";
      attributesContainer.appendChild(createAttributeInput());

      alert("Product uploaded (check server console/log for details).");
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Ошибка при загрузке. Посмотрите консоль.");
    }
  });

  // ---- Добавление категории на сервер и обновление UI ----
  categoryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const nameInput = document.getElementById("category-name");
    const name = ((nameInput && nameInput.value) || "").trim();
    if (!name) return;

    try {
      const resp = await fetch("{{ url_for('add_category') }}", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin", // обязательно, чтобы передать сессионную cookie
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

      // добавляем в список категорий (ul), если нет
      if (
        ![...categoryList.children].some((li) => li.textContent === addedName)
      ) {
        const li = document.createElement("li");
        li.textContent = addedName;
        categoryList.appendChild(li);
      }

      // добавляем в select, если нет
      if (
        ![...productCategory.options].some((opt) => opt.value === addedName)
      ) {
        const option = document.createElement("option");
        option.value = addedName;
        option.textContent = addedName;
        productCategory.appendChild(option);
      }

      categoryForm.reset();
    } catch (err) {
      console.error("Network/JS error while adding category:", err);
      alert("Network error while adding category");
    }
  });

  // ---- Инициализация UI при загрузке страницы: наполняем списки из Jinja-переменной ----
  document.addEventListener("DOMContentLoaded", () => {
    try {
      // categories передаётся из Flask: в шаблоне должно быть {{ categories|tojson }}
      const initialCategories = window.INITIAL_CATEGORIES || [];
      categoryList.innerHTML = "";

      // Оставляем первый option (Select category) и удаляем остальные
      while (productCategory.options.length > 1) productCategory.remove(1);

      initialCategories.forEach((name) => {
        const li = document.createElement("li");
        li.textContent = name;
        categoryList.appendChild(li);

        if (![...productCategory.options].some((opt) => opt.value === name)) {
          const option = document.createElement("option");
          option.value = name;
          option.textContent = name;
          productCategory.appendChild(option);
        }
      });
    } catch (e) {
      console.warn("Could not populate initial categories:", e);
    }
  });
})();
