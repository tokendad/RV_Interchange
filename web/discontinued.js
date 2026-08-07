async function walkSupersessionChain(ns, value, initialSupersessions) {
  const visited = new Set([`${ns}:${value}`]);

  async function buildNode(nodeValue, children, unverified) {
    if (!children || children.length === 0) {
      return { value: nodeValue, current: !unverified, unverified: !!unverified, children: [] };
    }

    const showAttributes = children.length > 1;
    const childNodes = [];

    for (const child of children) {
      const key = `${ns}:${child.part}`;
      if (visited.has(key)) {
        childNodes.push({ value: child.part, current: true, children: [], cycle: true });
        continue;
      }
      visited.add(key);

      const replacementsResult = await rviFetch(
        `/public/v1/replacements?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(child.part)}`);
      const replacementsFetchFailed = !replacementsResult.ok;
      const nextSupersessions =
        replacementsResult.ok && replacementsResult.body ? replacementsResult.body.supersessions : [];

      let attributes = [];
      if (showAttributes) {
        const resolveResult = await rviFetch(
          `/public/v1/resolve?ns=${encodeURIComponent(ns)}&identifier=${encodeURIComponent(child.part)}`);
        if (resolveResult.ok && resolveResult.body) {
          attributes = resolveResult.body.attributes.slice(0, 2);
        }
      }

      const childNode = await buildNode(child.part, nextSupersessions, replacementsFetchFailed);
      childNode.attributes = attributes;
      childNodes.push(childNode);
    }

    return { value: nodeValue, current: false, children: childNodes };
  }

  return buildNode(value, initialSupersessions);
}

function formatAttribute(attr) {
  const name = attr.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const value = attr.qualifier ? `${attr.qualifier} ${attr.value}` : attr.value;
  return attr.unit ? `${name}: ${value} ${attr.unit}` : `${name}: ${value}`;
}

function renderDiscontinuedSection(rootNode, { onNodeClick }) {
  const section = document.createElement("section");
  section.className = "discontinued-section";

  const heading = document.createElement("h2");
  heading.className = "section-heading";
  heading.textContent = "Discontinued";
  section.appendChild(heading);

  const card = document.createElement("div");
  card.className = "discontinued-card";
  card.appendChild(renderChainNode(rootNode, true, onNodeClick));
  section.appendChild(card);

  return section;
}

function renderChainNode(node, isRoot, onNodeClick) {
  const wrapper = document.createElement("div");
  wrapper.className = "chain-branch";

  const nodeButton = document.createElement("button");
  nodeButton.type = "button";
  nodeButton.className = "chain-node" +
    (node.unverified ? " chain-node-unverified" : node.current ? " chain-node-current" : "");
  nodeButton.addEventListener("click", () => onNodeClick(node.value));

  const numberSpan = document.createElement("span");
  numberSpan.className = "chain-node-number";
  numberSpan.textContent = node.value;
  nodeButton.appendChild(numberSpan);

  const tagSpan = document.createElement("span");
  tagSpan.className = "chain-node-tag";
  tagSpan.textContent = isRoot
    ? "(this part)"
    : node.unverified ? "— couldn't verify" : node.current ? "— current" : "(also discontinued)";
  nodeButton.appendChild(tagSpan);

  if (node.attributes && node.attributes.length > 0) {
    const attrLine = document.createElement("div");
    attrLine.className = "chain-node-attributes";
    attrLine.textContent = node.attributes.map(formatAttribute).join(" · ");
    nodeButton.appendChild(attrLine);
  }

  wrapper.appendChild(nodeButton);

  if (node.children.length > 0) {
    const arrow = document.createElement("div");
    arrow.className = "chain-arrow";
    arrow.textContent = node.children.length > 1
      ? "↓ replaced by two current options"
      : "↓ replaced by";
    wrapper.appendChild(arrow);

    const childrenRow = document.createElement("div");
    childrenRow.className = "chain-children";
    for (const child of node.children) {
      childrenRow.appendChild(renderChainNode(child, false, onNodeClick));
    }
    wrapper.appendChild(childrenRow);
  }

  return wrapper;
}
