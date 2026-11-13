document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-save-product]").forEach((button) => {
        button.addEventListener("click", () => {
            const saved = button.classList.toggle("is-saved");
            button.querySelector("span").textContent = saved ? "♥" : "♡";
            button.setAttribute("aria-label", saved ? "Remove from saved products" : "Save product");
        });
    });

    const filterToggle = document.querySelector("[data-filter-toggle]");
    if (filterToggle) {
        filterToggle.addEventListener("click", () => {
            filterToggle.classList.toggle("is-active");
        });
    }

    document.querySelectorAll(".rating-picker button").forEach((button, index, buttons) => {
        button.addEventListener("click", () => {
            buttons.forEach((item, itemIndex) => {
                item.classList.toggle("is-selected", itemIndex <= index);
            });
        });
    });
});
