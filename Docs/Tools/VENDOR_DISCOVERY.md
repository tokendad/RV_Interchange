# vendor_discovery.py

Builds a review queue of vendor manuals, brochures, service documents, parts lists,
dimensional drawings, wiring diagrams, and retrofit guides.

The tool is intentionally conservative:

- respects `robots.txt` by default;
- rate-limits page requests;
- crawls HTML only on the seed host;
- records external document links such as Google Drive without crawling them;
- does not download documents;
- produces JSON or CSV for human review before capture with `observations.py`.

## Fogatti example

Fogatti's former `fogatti.com` address redirects to `fogattiliving.com`. The current
manual index is:

    https://fogattiliving.com/pages/technical-service-manuals

Run:

    cd Docs/Tools
    python3 vendor_discovery.py \
      --vendor Fogatti \
      --seed https://fogattiliving.com/pages/technical-service-manuals \
      --out fogatti_document_queue.json \
      --max-pages 20 \
      --delay 1.0 \
      --top 20

The current Fogatti page uses generic `Download` anchor text and hosts many manuals on
Google Drive. `vendor_discovery.py` preserves the enclosing table-row text so each link
retains its model context, and canonicalizes common Google Drive URL forms for deduplication.

Observed manual-index families used to validate the parser include:

- InstaShower 7
- InstaShower 8 Plus
- InstaShower 8 Pro
- InstaShower 9 Pro
- InstaShower Ultra
- HybridShower 6 / 6 Pro / 10 / 10 Pro
- InstaCool and FA-series air conditioners
- RV furnaces
- induction cooktop and opening instructions

## Output fields

- `vendor`
- `title`
- `url`
- `source_page`
- `document_type`
- `priority`
- `host`
- `model_hint`
- `notes`
- `fetched`

The queue is not evidence by itself. Review each candidate, then use `observations.py fetch`
or `observations.py add` to capture selected documents deliberately.

## Classification

Current classes include:

- `service_manual`
- `parts_catalog`
- `installation_manual`
- `fitment_guide`
- `dimension_drawing`
- `wiring_diagram`
- `user_manual`
- `spec_sheet`
- `sales_brochure`
- `catalog`
- `guide`

Classification is keyword-based and intended for prioritization, not ground truth.

## Tests

    python3 -m unittest -v test_vendor_discovery.py

The tests use Fogatti-shaped HTML to verify:

- generic Google Drive `Download` links retain their product-row context;
- Google Drive URL variants deduplicate to one canonical file URL;
- opening-instruction documents receive installation-manual priority.

## Limitations

- It does not use a search-engine API, so it only discovers documents reachable from the
  supplied seed pages and their relevant same-host links.
- JavaScript-only links that are absent from the returned HTML will not be seen.
- External dealer libraries should be supplied as additional `--seed` arguments rather
  than automatically spidered across domains.
- Document contents are not fetched or parsed by this tool.
