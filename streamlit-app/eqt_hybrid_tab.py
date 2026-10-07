"""EQT Hybrid Strategy dashboard as a Streamlit tab or page.

Drop this file next to your app.py, put eqt_hybrid_dashboard.html and
eqt_dashboard_summary.md beside it (or one level up), then call render():

    import eqt_hybrid_tab
    with tab:
        eqt_hybrid_tab.render_eqt_hybrid()

Both deliverables are regenerated together by run_backtest.py, so the HTML
and the Markdown always describe the same panel.
"""
from pathlib import Path
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).resolve().parent


def _find(name: str) -> Path:
    """Look beside this module first, then one level up (repo root)."""
    here = HERE / name
    return here if here.exists() else HERE.parent / name


HTML = _find("eqt_hybrid_dashboard.html")
MD   = _find("eqt_dashboard_summary.md")

# The rendered dashboard measures roughly 2,600px tall.
# Give it a generous height and let the page scroll normally.
DEFAULT_HEIGHT = 2800


@st.cache_data(show_spinner=False)
def _read(path_str: str, mtime: float) -> str:
    """mtime is part of the cache key — redeploying new data busts the cache."""
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


def render_eqt_hybrid(height: int = DEFAULT_HEIGHT,
                      default_view: str = "Interactive") -> None:
    md   = _load(MD)
    html = _load(HTML)

    st.subheader("EQT — Henry Hub mean-reversion hybrid")
    asof = _as_of(md)
    if asof:
        st.caption(
            f"Data through {asof} · seasonal Dec→May + Z-score off-season "
            f"(entry Z < −0.25 & momentum < −$0.20, exit 10 signal-free bars) · "
            f"0.20%/side TC"
        )

    if html is None and md is None:
        st.error(
            "Neither `eqt_hybrid_dashboard.html` nor `eqt_dashboard_summary.md` was found "
            f"next to `eqt_hybrid_tab.py` (looked in `{HERE}`). "
            "Run `python run_backtest.py` locally to generate both files, "
            "then commit them alongside this module."
        )
        return

    views = [v for v, ok in (("Interactive", html is not None),
                              ("Summary",     md   is not None)) if ok]
    view = default_view if default_view in views else views[0]
    if len(views) > 1:
        view = st.radio("View", views, index=views.index(view),
                        horizontal=True, label_visibility="collapsed")

    if view == "Interactive":
        components.html(html, height=height, scrolling=True)
        st.caption(
            "Self-contained dashboard — all charts run client-side. "
            "If the CSV button does nothing, your browser is blocking downloads "
            "from the embedded frame — use the Summary view instead."
        )
    else:
        st.markdown(md)

    if html is not None:
        st.download_button(
            "Download the interactive dashboard (.html)",
            html,
            file_name="eqt_hybrid_dashboard.html",
            mime="text/html",
        )


if __name__ == "__main__":
    st.set_page_config(page_title="EQT Hybrid Strategy", layout="wide", page_icon="⛽")
    render_eqt_hybrid()
