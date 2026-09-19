const state = {
  data: null,
  game: null,
  tab: "dev"
};

async function loadData() {
  const response = await fetch("data.json?ts=" + Date.now());
  if (!response.ok) throw new Error("data.json yüklenemedi");
  state.data = await response.json();
  renderDevelopment();
  startNewRun();
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });
}

function switchTab(tab) {
  state.tab = tab;

  document.querySelectorAll(".tab").forEach((button) =>
    button.classList.toggle("active", button.dataset.tab === tab)
  );

  document.querySelectorAll(".tab-panel").forEach((panel) =>
    panel.classList.toggle("active", panel.id === tab)
  );
}

function renderDevelopment() {
  const system = state.data.system;

  document.getElementById("generation").textContent = system.generation;
  document.getElementById("generationPill").textContent =
    `GEN ${system.generation}`;

  document.getElementById("rulesVersion").textContent =
    system.rules_version;

  document.getElementById("systemStatus").textContent =
    system.status;

  document.getElementById("smokeStatus").textContent =
    state.data.smoke_test?.ok ? "OK" : "FAIL";

  const last = system.last_event;
  const eventBox = document.getElementById("lastEvent");

  eventBox.textContent = last
    ? `GEN ${last.generation}
${last.summary || "Değişiklik"}

${last.reason || ""}`
    : "Henüz kabul edilmiş bir nesil yok.";

  const list = document.getElementById("history");
  const history = [...(system.history_tail || [])].reverse();

  list.innerHTML = history.length
    ? history
        .map(
          (item) => `
      <div class="history-item">
        <div class="history-gen">
          GEN ${item.generation ?? "—"}
        </div>

        <div class="history-main">
          <strong>
            ${escapeHtml(item.summary || item.status || "Olay")}
          </strong>

          <span>
            ${escapeHtml(item.reason || "")}
          </span>
        </div>
      </div>
    `
        )
        .join("")
    : '<div class="muted">Geçmiş boş.</div>';
}

function startNewRun() {
  const cfg = state.data.game;
  const firstEnemy = cfg.enemies[0];

  state.game = {
    player: {
      hp: cfg.player.max_hp,
      energy: cfg.player.max_energy,
      gold: cfg.player.starting_gold,
      xp: 0,
      level: 1,
      inventory: []
    },

    battle: {
      enemy: { ...firstEnemy },
      enemyHp: firstEnemy.hp,
      shield: 0,
      turn: 1,
      log: [`${firstEnemy.name} ortaya çıktı.`],
      ended: false,
      result: null
    },

    enemyIndex: 0
  };

  renderGame();
}

function act(actionId) {
  const cfg = state.data.game;
  const g = state.game;

  if (!g || g.battle.ended) return;

  const action = cfg.actions.find((a) => a.id === actionId);

  if (!action) return;

  const cost = Number(action.energy || 0);

  if (g.player.energy < cost) {
    g.battle.log.push("Yeterli enerji yok.");
    renderGame();
    return;
  }

  g.player.energy -= cost;

  applyEffects(action.effects || []);

  if (g.battle.enemyHp <= 0) {
    winBattle();
    renderGame();
    return;
  }

  enemyTurn();

  g.battle.turn += 1;

  renderGame();
}

function applyEffects(effects) {
  const cfg = state.data.game;
  const g = state.game;
  const roll = Math.random();

  for (const effect of effects) {
    const amount = Number(effect.amount || 0);

    if (effect.type === "damage") {
      let raw = Number(cfg.player.base_attack) * amount;

      const critical =
        roll < Number(cfg.player.crit_chance || 0);

      if (critical) {
        raw *= Number(cfg.player.crit_multiplier || 1);
      }

      const damage = Math.max(
        1,
        Math.floor(raw) -
          Number(g.battle.enemy.defense || 0)
      );

      g.battle.enemyHp = Math.max(
        0,
        g.battle.enemyHp - damage
      );

      g.battle.log.push(
        `Saldırı: ${damage} hasar.${
          critical ? " KRİTİK!" : ""
        }`
      );
    }

    else if (effect.type === "heal") {
      const amountInt = Math.max(
        0,
        Math.floor(amount)
      );

      const oldHp = g.player.hp;

      g.player.hp = Math.min(
        Number(cfg.player.max_hp),
        g.player.hp + amountInt
      );

      g.battle.log.push(
        `+${g.player.hp - oldHp} can.`
      );
    }

    else if (effect.type === "shield") {
      g.battle.shield += Math.max(
        0,
        Math.floor(amount)
      );

      g.battle.log.push(
        `Kalkan +${Math.floor(amount)}.`
      );
    }

    else if (effect.type === "energy") {
      g.player.energy = Math.min(
        Number(cfg.player.max_energy),
        Math.max(
          0,
          g.player.energy + Math.floor(amount)
        )
      );

      g.battle.log.push(
        `Enerji ${
          amount >= 0 ? "+" : ""
        }${Math.floor(amount)}.`
      );
    }
  }
}
function enemyTurn() {
  const cfg = state.data.game;
  const g = state.game;

  const raw = Math.max(
    0,
    Number(g.battle.enemy.attack) -
      Number(cfg.player.base_defense)
  );

  const blocked = Math.min(
    raw,
    g.battle.shield
  );

  const damage = raw - blocked;

  g.battle.shield -= blocked;

  g.player.hp = Math.max(
    0,
    g.player.hp - damage
  );

  g.player.energy = Math.min(
    Number(cfg.player.max_energy),
    g.player.energy + 1
  );

  g.battle.log.push(
    blocked
      ? `${g.battle.enemy.name} vurdu: ${damage} hasar, ${blocked} engellendi.`
      : `${g.battle.enemy.name} vurdu: ${damage} hasar.`
  );

  if (g.player.hp <= 0) {
    g.battle.ended = true;
    g.battle.result = "loss";

    gainXp(
      Number(cfg.progression.xp_per_loss)
    );

    g.battle.log.push(
      "Koşu sona erdi."
    );
  }
}

function winBattle() {
  const cfg = state.data.game;
  const g = state.game;

  const xp = Number(
    g.battle.enemy.xp ??
      cfg.progression.xp_per_win
  );

  const gold = Number(
    g.battle.enemy.gold ??
      cfg.progression.gold_per_win
  );

  gainXp(xp);

  g.player.gold += gold;

  g.player.hp = Math.min(
    Number(cfg.player.max_hp),
    g.player.hp +
      Number(cfg.progression.heal_after_battle)
  );

  g.battle.ended = true;
  g.battle.result = "win";

  g.battle.log.push(
    `Kazandın: +${xp} XP, +${gold} altın.`
  );
}

function gainXp(amount) {
  const threshold = Math.max(
    1,
    Number(
      state.data.game.progression.xp_to_level
    )
  );

  state.game.player.xp += Math.max(
    0,
    Math.floor(amount)
  );

  while (
    state.game.player.xp >= threshold
  ) {
    state.game.player.xp -= threshold;
    state.game.player.level += 1;
  }
}

function buyPotion() {
  const cfg = state.data.game;
  const g = state.game;

  const cost = Number(
    cfg.shop.potion_cost
  );

  const heal = Number(
    cfg.shop.potion_heal
  );

  if (
    g.player.gold < cost ||
    g.player.hp >= Number(cfg.player.max_hp)
  ) {
    return;
  }

  g.player.gold -= cost;

  g.player.hp = Math.min(
    Number(cfg.player.max_hp),
    g.player.hp + heal
  );

  g.player.inventory.push("potion");

  g.battle.log.push(
    `Potion kullanıldı: +${heal} can.`
  );

  renderGame();
}

function renderGame() {
  const cfg = state.data.game;
  const g = state.game;

  if (!g) return;

  document.getElementById("gameTitle").textContent =
    cfg.title;

  document.getElementById("level").textContent =
    g.player.level;

  document.getElementById("xp").textContent =
    g.player.xp;

  document.getElementById("gold").textContent =
    g.player.gold;

  document.getElementById("playerHpText").textContent =
    `${g.player.hp} / ${cfg.player.max_hp} HP`;

  document.getElementById("playerHpBar").style.width =
    `${
      Math.max(
        0,
        Math.min(
          100,
          (g.player.hp / cfg.player.max_hp) * 100
        )
      )
    }%`;

  document.getElementById("playerMeta").textContent =
    `${g.player.energy} enerji • ${g.player.gold} altın`;

  const e = g.battle.enemy;

  document.getElementById("enemyHpText").textContent =
    `${g.battle.enemyHp} / ${e.hp} HP`;

  document.getElementById("enemyHpBar").style.width =
    `${
      Math.max(
        0,
        Math.min(
          100,
          (g.battle.enemyHp / e.hp) * 100
        )
      )
    }%`;

  document.getElementById("enemyMeta").textContent =
    `${e.name} • ${e.attack} saldırı`;

  document.getElementById("log").innerHTML =
    g.battle.log
      .slice(-8)
      .map(
        (line) =>
          `<div class="log-line">${escapeHtml(
            line
          )}</div>`
      )
      .join("");

  const actions =
    document.getElementById("actions");

  actions.innerHTML = cfg.actions
    .map(
      (action) => `
    <button
      class="action-btn"
      ${g.battle.ended ? "disabled" : ""}
      data-action="${escapeAttr(action.id)}"
    >
      <strong>
        ${escapeHtml(action.name)}
      </strong>

      <span>
        ${escapeHtml(action.description)}
      </span>

      <br>

      <span class="action-cost">
        ${Number(action.energy || 0)} enerji
      </span>
    </button>
  `
    )
    .join("");
      actions
    .querySelectorAll("[data-action]")
    .forEach((btn) =>
      btn.addEventListener(
        "click",
        () => act(btn.dataset.action)
      )
    );

  document.getElementById("potionInfo").textContent =
    `${cfg.shop.potion_cost} altın → +${cfg.shop.potion_heal} HP`;
}

function escapeHtml(value) {
  return String(value).replace(
    /[&<>"]/g,
    (ch) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;"
      }[ch])
  );
}

function escapeAttr(value) {
  return escapeHtml(value).replace(
    /'/g,
    "&#39;"
  );
}

document.addEventListener(
  "DOMContentLoaded",
  async () => {
    setupTabs();

    document
      .getElementById("restartBtn")
      .addEventListener(
        "click",
        startNewRun
      );

    document
      .getElementById("potionBtn")
      .addEventListener(
        "click",
        buyPotion
      );

    try {
      await loadData();
    } catch (error) {
      document.getElementById(
        "lastEvent"
      ).textContent =
        "Veri yüklenemedi: " +
        error.message;
    }
  }
);
