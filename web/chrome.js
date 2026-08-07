const NAV_LINKS = [
  { id: "lookup", label: "Parts Lookup", href: "/" },
  { id: "coverage", label: "Data Coverage", href: "/coverage.html" },
  { id: "how-it-works", label: "How It Works", href: "/how-it-works.html" },
  { id: "contribute", label: "Contribute", href: "https://github.com/tokendad/RV_Interchange" },
];

function renderHeader(activeId) {
  const header = document.createElement("header");
  header.className = "site-header";

  const nav = document.createElement("nav");
  nav.className = "site-nav";
  nav.setAttribute("aria-label", "Primary");

  for (const link of NAV_LINKS) {
    const a = document.createElement("a");
    a.href = link.href;
    a.textContent = link.label;
    a.className = link.id === activeId ? "nav-link nav-link-active" : "nav-link";
    nav.appendChild(a);
  }

  header.appendChild(nav);
  return header;
}

function renderFooter() {
  const footer = document.createElement("footer");
  footer.className = "site-footer";

  const brand = document.createElement("div");
  brand.className = "footer-brand";
  brand.textContent = "RV Interchange";
  footer.appendChild(brand);

  const coverage = document.createElement("div");
  coverage.className = "footer-coverage";
  coverage.textContent = "Currently covering Suburban, Coleman-Mach, Atwood, and Norcold";
  footer.appendChild(coverage);

  const links = document.createElement("div");
  links.className = "footer-links";

  const githubLink = document.createElement("a");
  githubLink.href = "https://github.com/tokendad/RV_Interchange";
  githubLink.textContent = "GitHub";
  links.appendChild(githubLink);

  const reportLink = document.createElement("a");
  reportLink.href = "https://github.com/tokendad/RV_Interchange/issues/new";
  reportLink.textContent = "Report missing or incorrect data";
  links.appendChild(reportLink);

  const contactLink = document.createElement("a");
  contactLink.href = "/contact.html";
  contactLink.textContent = "Contact";
  links.appendChild(contactLink);

  footer.appendChild(links);

  const disclaimer = document.createElement("p");
  disclaimer.className = "footer-disclaimer";
  disclaimer.textContent =
    "Compatibility information is provided as a research aid. Verify dimensions, " +
    "connections, electrical requirements, fuel type, and installation instructions " +
    "before purchasing or installing a replacement part.";
  footer.appendChild(disclaimer);

  return footer;
}
