const setupComposer = () => {
    const textarea = document.getElementById("message-text");
    const fileInput = document.getElementById("data-file");
    const filePill = document.getElementById("selected-file-pill");
    const thread = document.getElementById("chat-thread");

    if (textarea) {
        const resize = () => {
            textarea.style.height = "auto";
            textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
        };

        resize();
        textarea.addEventListener("input", resize);

        document.querySelectorAll("[data-prompt]").forEach((button) => {
            button.addEventListener("click", () => {
                textarea.value = button.dataset.prompt || "";
                textarea.focus();
                resize();
            });
        });

        textarea.addEventListener("keydown", (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                event.preventDefault();
                textarea.closest("form")?.requestSubmit();
            }
        });
    }

    if (fileInput && filePill) {
        const syncFilePill = () => {
            const file = fileInput.files?.[0];
            if (!file) {
                filePill.hidden = true;
                filePill.textContent = "";
                return;
            }

            filePill.hidden = false;
            filePill.textContent = `Выбрано: ${file.name}`;
        };

        fileInput.addEventListener("change", syncFilePill);
        syncFilePill();
    }

    if (thread) {
        thread.scrollTop = thread.scrollHeight;
    }
};

const toggleLoader = (show) => {
    const globalLoader = document.getElementById("global-loader");
    if (!globalLoader) {
        return;
    }
    globalLoader.style.display = show ? "inline-flex" : "none";
};

const setupDropzones = () => {
    document.querySelectorAll(".dropzone").forEach((dropzone) => {
        const input = dropzone.querySelector("input[type=file]");
        const label = document.getElementById("dropzone-file-name");
        if (!input || dropzone.dataset.ready) return;
        dropzone.dataset.ready = "true";
        const update = () => {
            const file = input.files?.[0];
            if (label) label.textContent = file ? `Выбрано: ${file.name}` : "Файл не выбран";
            dropzone.classList.toggle("is-filled", Boolean(file));
        };
        input.addEventListener("change", update);
        ["dragenter", "dragover"].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add("is-dragging");
        }));
        ["dragleave", "drop"].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove("is-dragging");
        }));
        dropzone.addEventListener("drop", (event) => {
            if (event.dataTransfer?.files?.length) {
                input.files = event.dataTransfer.files;
                update();
            }
        });
    });
};

const setupLightbox = () => {
    const lightbox = document.getElementById("media-lightbox");
    const image = lightbox?.querySelector("img");
    if (!lightbox || !image || lightbox.dataset.ready) return;
    lightbox.dataset.ready = "true";
    document.addEventListener("click", (event) => {
        const target = event.target;
        if (target instanceof HTMLImageElement && target.matches(".message-preview-image, .chart-card img, .image-preview img")) {
            image.src = target.currentSrc || target.src;
            image.alt = target.alt;
            lightbox.showModal();
        }
        if (target === lightbox || target.closest(".media-lightbox__close")) lightbox.close();
    });
};

const setupTheme = () => {
    const toggle = document.querySelector("[data-theme-toggle]");
    if (window.localStorage.getItem("data-assistant-theme") === "dark") {
        document.documentElement.dataset.theme = "dark";
    }

    if (!toggle || toggle.dataset.ready) {
        return;
    }

    toggle.dataset.ready = "true";
    toggle.addEventListener("click", () => {
        const isDark = document.documentElement.dataset.theme === "dark";
        document.documentElement.dataset.theme = isDark ? "light" : "dark";
        window.localStorage.setItem("data-assistant-theme", isDark ? "light" : "dark");
    });
};

document.addEventListener("DOMContentLoaded", () => {
    setupComposer();
    setupTheme();
    setupDropzones();
    setupLightbox();

    document.body.addEventListener("htmx:beforeRequest", () => toggleLoader(true));
    document.body.addEventListener("htmx:afterRequest", () => toggleLoader(false));
    document.body.addEventListener("htmx:afterSwap", () => {
        toggleLoader(false);
        setupComposer();
        setupDropzones();
    });
});
