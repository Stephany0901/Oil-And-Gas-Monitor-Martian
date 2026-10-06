"""VLO crack-spread dashboard as a Streamlit tab or page.

Drop this file next to your app, put `vlo_crack_dashboard.html` and
`vlo_dashboard.md` beside it, then call `render()` from wherever you want it.

    # single-file app using st.tabs
    import vlo_tab
    t1, t2, t3 = st.tabs(["Overview", "Something", "VLO Crack Model"])
    with t3:
        vlo_tab.render()

    # multipage app: save as pages/3_VLO_Crack_Model.py
    import vlo_tab
    vlo_tab.render()

Both deliverables are regenerated together by the model refresh, so the HTML and
the Markdown always describe the same panel.
"""
from pathlib import Path
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).resolve().parent


def _find(name: str) -> Path:
    """Look beside this module, then one level up.

    In this repo `app.py` and friends live in `streamlit-app/` while
    `vlo_dashboard.md` sits at the repository root. Searching the parent too keeps a
    single copy of each file instead of two that drift apart.
    """
    here = HERE / name
    return here if here.exists() else HERE.parent / name


HTML = _find("vlo_crack_dashboard.html")
MD = _find("vlo_dashboard.md")

# Streamlit's component iframe does NOT auto-size to its content. The rendered
# dashboard measures ~5,240px tall, so anything shorter forces a scrollbar inside the
# iframe and the reader ends up scrolling two things at once. Give it the full height
# and let the ordinary Streamlit page scroll. scrolling=True is kept as insurance so a
# longer trade log can never be clipped.
DEFAULT_HEIGHT = 5400


@st.cache_data(show_spinner=False)
def _read(path_str: str, mtime: float) -> str:
    """mtime is part of the cache key, so redeploying new data busts the cache."""
    return Path(path_str).read_text(encoding="utf-8")


def _load(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return _read(str(path), path.stat().st_mtime)


def _as_of(md: Optional[str]) -> Optional[str]:
    if not md:
        return None
    for line in md.splitlines():
        if line.startswith("**Data through "):
            return line.split("**Data through ")[1].split("**")[0].strip()
    return None


def render(height: int = DEFAULT_HEIGHT, default_view: str = "Interactive") -> None:
    md = _load(MD)
    html = _load(HTML)

    st.subheader("Valero — refinery margin mean reversion")
    asof = _as_of(md)
    if asof:
        st.caption(f"Data through {asof} · long-only, locked model (z 30/30, entry z > 1.0 "
                   f"and momentum > 0.5, exit after 3 signal-free bars)")

    if html is None and md is None:
        st.error(
            "Neither `vlo_crack_dashboard.html` nor `vlo_dashboard.md` was found next to "
            f"`vlo_tab.py` (looked in `{HERE}`). Commit both files alongside this module."
        )
        return

    views = [v for v, ok in (("Interactive", html is not None), ("Summary", md is not None)) if ok]
    view = default_view if default_view in views else views[0]
    if len(views) > 1:
        view = st.radio("View", views, index=views.index(view), horizontal=True,
                        label_visibility="collapsed")

    if view == "Interactive":
        # The page is fully self-contained — no external scripts, no browser storage —
        # so it runs inside the component iframe unchanged.
        components.html(html, height=height, scrolling=True)
        st.caption(
            "Every parameter box is live: the backtest re-runs client-side when you change "
            "one. **Reset to locked model** restores the committed specification. If the "
            "CSV button does nothing, your browser is blocking downloads from the embedded "
            "frame — use the Summary view or open the HTML file directly."
        )
    else:
        st.markdown(md)

    if html is not None:
        st.download_button("Download the interactive dashboard (.html)", html,
                           file_name="vlo_crack_dashboard.html", mime="text/html")


if __name__ == "__main__":
    st.set_page_config(page_title="VLO Crack Model", layout="wide")
    render()
