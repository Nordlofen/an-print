"""Scoped styles for the ipywidgets input panel (calculation output is separate)."""

PANEL_CSS = """
<style>
.anp-root { width: 100%; min-width: 0; }
.anp-root > .anp-style { display: none; }
.anp-panel {
    --anp-bg: #fff;
    --anp-fg: #202327;
    --anp-muted: #5a626b;
    --anp-line: #d7dce1;
    --anp-field: #fff;
    --anp-soft: #f4f6f8;
    --anp-action: #293c4c;
    --anp-on-action: #fff;
    --anp-focus: var(--jp-brand-color1, #2675bf);
    box-sizing: border-box;
    container-type: inline-size;
    width: 100%; max-width: 710px;
    padding: 22px; margin: 6px 0 18px;
    border: 1px solid var(--anp-line); border-radius: 8px;
    background: var(--anp-bg); color: var(--anp-fg);
    font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --jp-widgets-font-size: 14px;
    --jp-widgets-label-color: var(--anp-fg);
    --jp-widgets-color: var(--anp-fg);
}
[data-jp-theme-light="false"] .anp-panel { --anp-bg: #202226; --anp-fg: #ededee; --anp-muted: #b3bac2; --anp-line: #50565e; --anp-field: #292d32; --anp-soft: #292d32; --anp-action: #d1dce5; --anp-on-action: #202327; }
.anp-panel *, .anp-panel *::before, .anp-panel *::after { box-sizing: border-box; }
.anp-panel .widget-box, .anp-panel .widget-html, .anp-panel .widget-label { min-width: 0; }
.anp-panel .widget-html, .anp-panel .widget-label { margin: 0; padding: 0; }
.anp-panel .widget-html-content { width: 100%; padding: 0; font: inherit; color: inherit; }
.anp-panel .anp-title h3 { margin: 0 0 16px; font: 500 19px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--anp-fg); }
.anp-panel .anp-grid { display: grid; gap: 12px 14px; align-items: end; width: 100%; min-width: 0; }
.anp-panel .anp-cols-1 { grid-template-columns: minmax(0, 1fr); }
.anp-panel .anp-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.anp-panel .anp-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.anp-panel .anp-span-2 { grid-column: span 2; }
.anp-panel .anp-span-3 { grid-column: 1 / -1; }
.anp-panel .anp-field { width: 100%; min-width: 0; gap: 4px; }
.anp-panel .anp-field-label { font-size: 12px; line-height: 1.5; white-space: normal; overflow-wrap: anywhere; }
.anp-panel .anp-field-meta { min-height: 18px; font-size: 12px; line-height: 1.5; color: var(--anp-muted); }
.anp-panel .anp-field-meta:empty { display: none; }
.anp-panel .anp-field-meta i { font-style: italic; }
.anp-panel .anp-input { width: 100%; min-width: 0; height: auto; margin: 0; padding: 0; }
/* Keep native labels available to assistive technology, beside the visible HTML label. */
.anp-panel .anp-input > .widget-label { position: absolute; width: 1px !important; height: 1px; padding: 0; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.anp-panel .anp-input input, .anp-panel .anp-input select {
    width: 100%; min-width: 0; flex: 1 1 0; height: 36px;
    margin: 0; padding: 5px 8px;
    border: 1px solid var(--anp-line); border-radius: 4px;
    background-color: var(--anp-field); color: var(--anp-fg);
    box-shadow: none; font: inherit; font-variant-numeric: tabular-nums;
}
.anp-panel .anp-input select { padding-right: 24px; text-overflow: ellipsis; }
.anp-panel .anp-input input:disabled, .anp-panel .anp-input select:disabled { background-color: var(--anp-soft); color: var(--anp-muted); opacity: 1; }
.anp-panel .anp-input input:focus-visible, .anp-panel .anp-input select:focus-visible,
.anp-panel button:focus-visible, .anp-panel .p-Collapse-header:focus-visible,
.anp-panel .jupyter-widget-Collapse-header:focus-visible { outline: 2px solid var(--anp-focus); outline-offset: 2px; }
.anp-panel .anp-check { width: 100%; min-width: 0; height: auto; min-height: 36px; margin: 0; }
.anp-panel .anp-check label { width: auto; margin: 0; font: inherit; font-size: 13px; white-space: normal; display: flex; align-items: center; gap: 7px; color: var(--anp-fg); }
.anp-panel .anp-check input[type="checkbox"] { width: 16px; height: 16px; flex-shrink: 0; margin: 0; accent-color: var(--anp-action); }
.anp-panel .anp-check .widget-label { width: auto; padding: 0; text-align: left; white-space: normal; }
.anp-panel .anp-section { position: relative; width: 100%; min-width: 0; padding: 13px 0; border-top: 1px solid var(--anp-line); }
.anp-panel .anp-section-static { width: 100%; min-width: 0; padding: 14px 0; }
.anp-panel .anp-ungrouped { padding: 0; }
.anp-panel .anp-section-heading h4 { margin: 0 0 10px; font: inherit; font-weight: 500; color: var(--anp-fg); }
.anp-panel .anp-subsections { align-items: start; gap: 24px; }
.anp-panel .anp-subsections > .anp-section-static { padding: 0; }
.anp-panel .anp-subsections > .anp-section-static + .anp-section-static { padding-left: 24px; border-left: 1px solid var(--anp-line); }
.anp-panel .anp-subsections .anp-section-heading h4 { font-size: 12px; margin-bottom: 8px; }
.anp-panel .widget-accordion { width: 100%; margin: 0; padding: 0; overflow: visible; }
.anp-panel .p-Collapse, .anp-panel .jupyter-widget-Collapse { margin: 0; border: 0; box-shadow: none; background: transparent; }
.anp-panel .p-Collapse-header, .anp-panel .jupyter-widget-Collapse-header { margin: 0; padding: 0; border: 0; background: transparent; color: var(--anp-fg); font: inherit; font-weight: 500; line-height: 24px; min-height: 24px; white-space: normal; }
.anp-panel .p-Collapse-header:hover, .anp-panel .jupyter-widget-Collapse-header:hover { background: transparent; }
.anp-panel .p-Collapse-contents, .anp-panel .jupyter-widget-Collapse-contents { margin: 0; padding: 12px 0 0; border: 0; background: transparent; overflow: visible; }
.anp-panel .anp-section-summary { position: absolute; right: 0; top: 15px; max-width: 52%; font-size: 12px; color: var(--anp-muted); pointer-events: none; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.anp-panel .anp-section-summary .widget-html-content { overflow: hidden; text-overflow: ellipsis; }
.anp-panel .anp-with-summary:not(.anp-expanded) .p-Collapse-header,
.anp-panel .anp-with-summary:not(.anp-expanded) .jupyter-widget-Collapse-header { padding-right: 54%; }
.anp-panel .anp-cases { padding: 10px 12px; margin-bottom: 14px; border: 0; border-radius: 5px; background: var(--anp-soft); }
.anp-panel .anp-cases > .anp-section-summary { top: 13px; right: 12px; }
.anp-panel .anp-actions { flex-flow: row wrap; gap: 8px; margin-top: 10px; }
.anp-panel .widget-button, .anp-panel .an-print-copy-key-button {
    width: auto; min-width: 0; height: auto; min-height: 32px; margin: 0;
    padding: 6px 10px; border: 1px solid var(--anp-line); border-radius: 4px;
    box-shadow: none; background: var(--anp-soft); color: var(--anp-fg);
    font: inherit; font-size: 12px; white-space: normal; line-height: 1.5;
}
.anp-panel .widget-button:hover:enabled, .anp-panel .an-print-copy-key-button:hover:enabled { filter: brightness(.96); box-shadow: none; }
.anp-panel .widget-button:disabled, .anp-panel .an-print-copy-key-button:disabled { opacity: .5; }
.anp-panel .an-print-copy-key-button:active { transform: translateY(1px); }
.anp-panel .an-print-copy-key-clicked { outline: 2px solid var(--anp-focus); }
.anp-panel .anp-footer { flex-flow: row wrap; align-items: center; gap: 12px; border-top: 1px solid var(--anp-line); padding-top: 18px; }
.anp-panel .anp-calculate { font-size: 14px; min-height: 36px; background: var(--anp-action); color: var(--anp-on-action); border-color: var(--anp-action); }
.anp-panel .anp-case-status { font-size: 12px; color: var(--anp-muted); }
.anp-panel .anp-table { margin: 14px 0; width: 100%; min-width: 0; }
.anp-panel .anp-table-scroll { overflow-x: auto; width: 100%; min-width: 0; }
.anp-panel .anp-table-row { min-width: 380px; gap: 6px; align-items: center; padding: 6px 0; border-top: 1px solid var(--anp-line); }
.anp-panel .anp-table-header { padding: 0 0 8px; border-top: 0; align-items: end; color: var(--anp-muted); font-size: 12px; }
.anp-panel .anp-table-header .widget-html-content { white-space: normal; font-size: 12px; }
.anp-panel .anp-table-row > .widget-label { font: inherit; font-size: 12px; }
.anp-panel .anp-table-add { margin-top: 8px; align-self: flex-start; }
.anp-panel .anp-report-row { display: grid; grid-template-columns: minmax(0,1fr) 48px 56px 62px; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--anp-line); }
.anp-panel .anp-report-row .widget-label { font-size: 12px; white-space: normal; }
.anp-panel .anp-report-header { color: var(--anp-muted); }
.anp-panel .anp-report-row .anp-check { justify-content: center; }
.anp-panel .anp-report-row .anp-check .widget-label,
.anp-panel .anp-report-row .anp-check .widget-label-basic > span { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
.anp-panel .anp-report-row .anp-input input { text-align: center; }
.anp-output { width: 100%; min-width: 0; }
@container (max-width: 560px) {
    .anp-panel .anp-cols-3 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .anp-panel .anp-subsections .anp-cols-2 { grid-template-columns: minmax(0, 1fr); }
    .anp-panel .anp-subsections .anp-span-2 { grid-column: auto; }
    .anp-panel .anp-section-summary { display: none; }
    .anp-panel .anp-with-summary:not(.anp-expanded) .p-Collapse-header,
    .anp-panel .anp-with-summary:not(.anp-expanded) .jupyter-widget-Collapse-header { padding-right: 0; }
}
@container (max-width: 400px) {
    .anp-panel .anp-cols-2, .anp-panel .anp-cols-3 { grid-template-columns: minmax(0, 1fr); }
    .anp-panel .anp-span-2, .anp-panel .anp-span-3 { grid-column: auto; }
    .anp-panel .anp-subsections > .anp-section-static + .anp-section-static { padding-left: 0; padding-top: 14px; border-left: 0; border-top: 1px solid var(--anp-line); }
    .anp-panel .anp-report-row { grid-template-columns: minmax(0,1fr) 32px 42px 48px; gap: 4px; }
}
@media (pointer: coarse) {
    .anp-panel .anp-input input, .anp-panel .anp-input select { font-size: 16px; min-height: 44px; }
    .anp-panel .widget-button, .anp-panel .an-print-copy-key-button,
    .anp-panel .anp-check, .anp-panel .p-Collapse-header, .anp-panel .jupyter-widget-Collapse-header { min-height: 44px; }
}
</style>
"""
