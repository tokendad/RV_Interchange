const TIER_ORDER = ["Exact Match", "Direct Fit", "Fits With Modification"];
const TIER_CLASS = {
  "Exact Match": "tier-exact",
  "Direct Fit": "tier-direct",
  "Fits With Modification": "tier-modification",
};
const TIER_ICON = {
  "Exact Match": "✓",
  "Direct Fit": "↔",
  "Fits With Modification": "⚠",
};

function renderDetailView({ resolveData, replacementsData, ns }, { onBack, onCopyLink, onChainNodeClick }) {
  const container = document.createElement("div");
  container.className = "detail-view";

  const backButton = document.createElement("button");
  backButton.type = "button";
  backButton.className = "back-link";
  backButton.textContent = "← Back to results";
  backButton.addEventListener("click", onBack);
  container.appendChild(backButton);

  if (resolveData.manufacturer || resolveData.part_type) {
    const metaLine = document.createElement("div");
    metaLine.className = "detail-meta";
    metaLine.textContent =
      [resolveData.manufacturer, resolveData.part_type].filter(Boolean).join(" · ");
    container.appendChild(metaLine);
  }

  const heading = document.createElement("h1");
  heading.className = "detail-heading";
  heading.textContent = replacementsData.source;
  container.appendChild(heading);

  const others = resolveData.identifiers
    .map((i) => i.value)
    .filter((v) => v !== replacementsData.source);
  const altLine = document.createElement("div");
  altLine.className = "detail-alt";
  altLine.textContent = others.length > 0
    ? `Also known as: ${others.join(" · ")}`
    : "No alternate identifiers on file";
  container.appendChild(altLine);

  const byTier = {};
  for (const item of replacementsData.replacements) {
    if (!byTier[item.fit]) byTier[item.fit] = [];
    byTier[item.fit].push(item);
  }
  const hasReplacements = TIER_ORDER.some((tier) => byTier[tier] && byTier[tier].length > 0);
  if (hasReplacements) {
    const repHeading = document.createElement("h2");
    repHeading.className = "section-heading";
    repHeading.textContent = "Compatible Replacements";
    container.appendChild(repHeading);

    for (const tier of TIER_ORDER) {
      const items = byTier[tier];
      if (!items || items.length === 0) continue;
      for (const item of items) {
        container.appendChild(renderReplacementCard(tier, item));
      }
    }
  }

  if (replacementsData.supersessions.length > 0) {
    const placeholder = document.createElement("div");
    placeholder.className = "discontinued-loading";
    placeholder.textContent = "Loading discontinued history…";
    container.appendChild(placeholder);

    walkSupersessionChain(ns, replacementsData.source, replacementsData.supersessions)
      .then((tree) => {
        placeholder.replaceWith(renderDiscontinuedSection(tree, { onNodeClick: onChainNodeClick }));
      });
  }

  const copyButton = document.createElement("button");
  copyButton.type = "button";
  copyButton.className = "copy-link-button";
  copyButton.textContent = "Copy link";
  copyButton.addEventListener("click", onCopyLink);
  container.appendChild(copyButton);

  return container;
}

function renderReplacementCard(tier, item) {
  const card = document.createElement("div");
  card.className = `replacement-card ${TIER_CLASS[tier]}`;

  const pill = document.createElement("span");
  pill.className = `tier-pill ${TIER_CLASS[tier]}`;
  pill.textContent = `${TIER_ICON[tier]} ${tier}`;
  card.appendChild(pill);

  const partLine = document.createElement("div");
  partLine.className = "replacement-part";
  partLine.textContent = item.part;
  card.appendChild(partLine);

  if (item.caveats && item.caveats.length > 0) {
    const caveatLine = document.createElement("div");
    caveatLine.className = "replacement-caveats";
    caveatLine.textContent = item.caveats.map((c) => c.text).join("; ");
    card.appendChild(caveatLine);
  }

  return card;
}
