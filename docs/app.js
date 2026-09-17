import {
    loadPyodide
} from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";


const PYODIDE_INDEX =
    "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";


let pyodide = null;
let experimentData = null;
let playerReady = false;


const statusEl =
    document.getElementById(
        "pythonStatus"
    );


function setStatus(
    text,
    type
) {

    statusEl.textContent = text;

    statusEl.className =
        "status " + type;
}


function log(
    message
) {

    const container =
        document.getElementById(
            "log"
        );


    const item =
        document.createElement(
            "div"
        );


    item.className =
        "log-item";


    item.innerHTML = `
        <span>●</span>
        <p>${escapeHtml(message)}</p>
    `;


    container.prepend(
        item
    );
}


function escapeHtml(
    value
) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


async function loadExperimentData() {

    const response =
        await fetch(
            "./data.json?ts="
            + Date.now()
        );


    if (!response.ok) {

        throw new Error(
            "data.json yüklenemedi."
        );
    }


    return await response.json();
}


async function loadSariSource() {

    const response =
        await fetch(
            "./sari_sistem.py?ts="
            + Date.now()
        );


    if (!response.ok) {

        throw new Error(
            "sari_sistem.py yüklenemedi."
        );
    }


    return await response.text();
}


async function initPython(
    source
) {

    setStatus(
        "Python motoru yükleniyor...",
        "loading"
    );


    pyodide =
        await loadPyodide({
            indexURL:
                PYODIDE_INDEX
        });


    pyodide.setStdout({
        batched: text => {

            if (text.trim()) {
                log(text.trim());
            }

        }
    });


    pyodide.globals.set(
        "oyuncu_source",
        source
    );


    pyodide.runPython(`
import json

module_space = {
    "__name__": "sari_sistem"
}

exec(
    oyuncu_source,
    module_space
)

Oyuncu = module_space["Oyuncu"]

oyuncu = Oyuncu()

del oyuncu_source
del module_space
`);


    playerReady = true;


    setStatus(
        "Python motoru aktif",
        "ready"
    );


    log(
        "Sarı Sistem başarıyla tarayıcıda çalıştırıldı."
    );
}


function getState() {

    const raw =
        pyodide.runPython(`
import json

json.dumps(
    {
        "name": oyuncu.isim,
        "level": oyuncu.seviye,
        "xp": oyuncu.xp,
        "inventory": oyuncu.envanter
    },
    ensure_ascii=False,
    default=str
)
        `);


    return JSON.parse(
        raw
    );
}


function updateState() {

    if (!playerReady) {
        return;
    }


    const state =
        getState();


    document.getElementById(
        "level"
    ).textContent =
        state.level;


    document.getElementById(
        "xp"
    ).textContent =
        state.xp;


    document.getElementById(
        "inventory"
    ).textContent =
        state.inventory.length;


    document.getElementById(
        "methodCount"
    ).textContent =
        experimentData.methods.length;


    document.getElementById(
        "generation"
    ).textContent =
        experimentData.generation;


    document.getElementById(
        "generationMax"
    ).textContent =
        "/ "
        + experimentData.max_generations;
}


function actionReady(
    ready
) {

    document.getElementById(
        "trainButton"
    ).disabled =
        !ready;


    document.getElementById(
        "exploreButton"
    ).disabled =
        !ready;


    document
        .querySelectorAll(
            ".method-button"
        )
        .forEach(
            button => {
                button.disabled =
                    !ready;
            }
        );
}


function methodLabel(
    name
) {

    if (name === "xp_kazan") {

        return {
            title: "Antrenman",
            hint: "+25 XP"
        };
    }


    if (name === "durum_raporu") {

        return {
            title: "Durum Raporu",
            hint: "Oyuncu durumunu gör"
        };
    }


    if (
        name.includes("arena")
        || name.includes("duello")
    ) {

        return {
            title: "Arena Düellosu",
            hint: "Özel savaş yeteneği"
        };
    }


    if (
        name.includes("birles")
        || name.includes("birlest")
    ) {

        return {
            title: "Eşya Birleştir",
            hint: "İki eşyayı birleştir"
        };
    }


    if (
        name.includes("envanter")
        && name.includes("kullan")
    ) {

        return {
            title: "Eşya Kullan",
            hint: "Envanterdeki eşyayı kullan"
        };
    }


    return {
        title: "Yetenek",
        hint: "Evrilen Python yeteneği"
    };
}


function renderMethods() {

    const container =
        document.getElementById(
            "methods"
        );


    container.innerHTML = "";


    const methods =
        experimentData.methods
            .filter(
                item =>
                    item.name !== "__init__"
            );


    if (!methods.length) {

        container.innerHTML =
            "<div class='empty'>Henüz yetenek yok.</div>";

        return;
    }


    for (
        const method
        of methods
    ) {

        const info =
            methodLabel(
                method.name
            );


        const button =
            document.createElement(
                "button"
            );


        button.className =
            "method-button";


        button.innerHTML = `
            <span class="method-name">
                ${escapeHtml(method.name)}
            </span>

            <span class="method-hint">
                ${escapeHtml(info.title)}
                ·
                ${escapeHtml(info.hint)}
            </span>
        `;


        button.addEventListener(
            "click",
            () => {
                runMethod(
                    method.name
                );
            }
        );


        container.appendChild(
            button
        );
    }


    actionReady(
        playerReady
    );
}


function renderEvolution() {

    const latest =
        experimentData.latest_method;


    document.getElementById(
        "latestMethod"
    ).textContent =
        latest || "Henüz yok";


    document.getElementById(
        "scoreChange"
    ).textContent =
        experimentData.score_difference
        !== null
            ? (
                experimentData
                    .score_difference > 0
                    ? "+"
                    : ""
            )
            + experimentData
                .score_difference
            : "-";


    document.getElementById(
        "decision"
    ).textContent =
        experimentData
            .experiment_status
        || "-";


    document.getElementById(
        "latestCode"
    ).textContent =
        experimentData
            .latest_code
        || "Henüz evrim kaydı yok.";
                    }
function runPython(
    code
) {

    if (!playerReady) {

        log(
            "Python motoru henüz hazır değil."
        );

        return null;
    }


    try {

        return pyodide.runPython(
            code
        );

    } catch (error) {

        log(
            "Hata: "
            + error.message
        );

        return null;
    }
}


function train() {

    const result =
        runPython(`
oyuncu.xp_kazan(25)
        `);


    if (result !== null) {

        log(
            "Antrenman yapıldı. +25 XP"
        );

        updateState();
    }
}


function explore() {

    const items = [
        {
            ad: "Gizemli Kristal",
            deger: 25,
            xp: 15
        },

        {
            ad: "Eski Kılıç",
            deger: 35,
            xp: 20
        },

        {
            ad: "Şans Tılsımı",
            deger: 20,
            xp: 10
        },

        {
            ad: "Ejderha Parçası",
            deger: 50,
            xp: 30
        }
    ];


    const item =
        items[
            Math.floor(
                Math.random()
                * items.length
            )
        ];


    pyodide.globals.set(
        "found_item_json",
        JSON.stringify(item)
    );


    const result =
        runPython(`
import json

bulunan = json.loads(
    found_item_json
)

oyuncu.envanter.append(
    bulunan
)

bulunan["ad"]
        `);


    if (result !== null) {

        log(
            "Keşif başarılı: "
            + item.ad
            + " bulundu."
        );

        updateState();
    }


    pyodide.globals.delete(
        "found_item_json"
    );
}


function runMethod(
    name
) {

    if (!playerReady) {
        return;
    }


    try {

        let result;


        if (name === "xp_kazan") {

            result =
                pyodide.runPython(
                    "oyuncu.xp_kazan(25)"
                );

        } else {

            pyodide.globals.set(
                "selected_method",
                name
            );


            result =
                pyodide.runPython(`
method_name = selected_method
method = getattr(
    oyuncu,
    method_name
)

method_result = method()

method_result
                `);


            pyodide.globals.delete(
                "selected_method"
            );
        }


        let output = "";


        if (
            result !== null
            && result !== undefined
        ) {

            try {

                output =
                    JSON.stringify(
                        result.toJs
                            ? result.toJs({
                                dict_converter:
                                    Object.fromEntries
                            })
                            : result
                    );

            } catch {

                output =
                    String(result);
            }
        }


        log(
            "Yetenek çalıştırıldı: "
            + name
            + (
                output
                    ? " → " + output
                    : ""
            )
        );


        updateState();


    } catch (error) {

        log(
            name
            + " çalıştırılamadı: "
            + error.message
        );
    }
}


function connectButtons() {

    document.getElementById(
        "trainButton"
    ).addEventListener(
        "click",
        train
    );


    document.getElementById(
        "exploreButton"
    ).addEventListener(
        "click",
        explore
    );
}


async function start() {

    connectButtons();


    try {

        experimentData =
            await loadExperimentData();


        renderMethods();

        renderEvolution();

        updateState();


        log(
            "Nesil "
            + experimentData.generation
            + " yüklendi."
        );


        const source =
            await loadSariSource();


        await initPython(
            source
        );


        renderMethods();

        updateState();


        log(
            "🎮 Oyun hazır. Macerana başlayabilirsin."
        );


    } catch (error) {

        console.error(error);


        setStatus(
            "Oyun yüklenemedi",
            "error"
        );


        log(
            error.message
        );
    }
}


start();
