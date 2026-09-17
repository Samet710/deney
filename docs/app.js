async function loadData() {

    const response = await fetch(
        "data.json?ts=" + Date.now()
    );

    if (!response.ok) {
        throw new Error(
            "data.json yüklenemedi."
        );
    }

    return await response.json();
}


function text(id, value) {

    const element =
        document.getElementById(id);

    if (element) {
        element.textContent =
            value ?? "-";
    }
}


function renderMethods(methods) {

    const container =
        document.getElementById("methods");

    container.innerHTML = "";


    if (!methods || methods.length === 0) {

        container.innerHTML =
            "<div class='method'>Henüz gelişim yok.</div>";

        return;
    }


    for (const method of methods) {

        const card =
            document.createElement("div");

        card.className =
            "method";


        card.innerHTML = `
            <div class="method-name">
                ✓ ${method.name}
            </div>

            <div class="method-meta">
                Oyuncu yeteneği
            </div>
        `;


        container.appendChild(card);
    }
}


async function render() {

    try {

        const data =
            await loadData();


        text(
            "generation",
            `${data.generation}/${data.max_generations}`
        );


        text(
            "methodCount",
            data.methods.length
        );


        text(
            "latestMethod",
            data.latest_method || "-"
        );


        text(
            "level",
            data.player.level
        );


        text(
            "xp",
            data.player.xp
        );


        text(
            "inventory",
            data.player.inventory
        );


        text(
            "latestName",
            data.latest_method || "Henüz yok"
        );


        text(
            "latestGeneration",
            data.latest_generation
                ? `Nesil ${data.latest_generation}`
                : "Başlangıç sürümü"
        );


        text(
            "latestCode",
            data.latest_code || "-"
        );


        text(
            "updated",
            data.updated_at || "-"
        );


        text(
            "lineCount",
            data.line_count
        );


        text(
            "experimentStatus",
            data.experiment_status || "-"
        );


        renderMethods(
            data.methods
        );


        text(
            "status",
            "● AKTİF"
        );

    } catch (error) {

        console.error(error);

        text(
            "status",
            "● VERİ BEKLENİYOR"
        );

    }

}


render();
