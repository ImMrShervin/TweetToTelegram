import html
import os
import time
from typing import Any, Dict, Optional

from PIL import Image

import config


def _fmt(n: int) -> str:
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1000:
        return f"{n/1000:.1f}K".replace(".0K", "K")
    return str(n)


def build_html(tw: Dict[str, Any], s: Dict[str, Any]) -> str:
    a = tw["author"]
    text = html.escape(tw.get("text", "")).replace("\n", "<br>")
    rtl = any("\u0600" <= ch <= "\u06ff" for ch in tw.get("text", ""))
    direction = "rtl" if rtl else "ltr"

    verified = (
        '<svg class="badge" viewBox="0 0 24 24" aria-hidden="true"><path fill="#1d9bf0" '
        'd="M22.25 12c0-1.43-.88-2.67-2.19-3.34.46-1.39.2-2.9-.81-3.91s-2.52-1.27-3.91-.81'
        'C14.67 2.63 13.43 1.75 12 1.75s-2.67.88-3.34 2.19c-1.39-.46-2.9-.2-3.91.81s-1.26 '
        '2.52-.8 3.91c-1.32.67-2.2 1.91-2.2 3.34s.88 2.67 2.2 3.34c-.46 1.39-.2 2.9.8 3.91'
        's2.52 1.26 3.91.8c.67 1.32 1.91 2.2 3.34 2.2s2.67-.88 3.34-2.2c1.39.46 2.9.2 '
        '3.91-.8s1.27-2.52.81-3.91c1.31-.67 2.19-1.91 2.19-3.34zm-11.71 4.2L6.8 12.46l1.41-1.42 '
        '2.26 2.26 4.8-5.23 1.47 1.36-6.2 6.77z"></path></svg>'
        if (s.get("show_verified") and a.get("verified"))
        else ""
    )

    media_html = ""
    if s.get("show_media"):
        photos = [m for m in tw.get("media", []) if m.get("thumb")]
        if photos:
            cells = "".join(
                f'<div class="m-cell"><img src="{html.escape(m["thumb"])}">'
                + ('<span class="play">▶</span>' if m["type"] == "video" else "")
                + "</div>"
                for m in photos[:4]
            )
            media_html = f'<div class="media grid-{min(len(photos),4)}">{cells}</div>'

    quote_html = ""
    q = tw.get("quote")
    if s.get("show_quote") and q:
        quote_html = (
            '<div class="quote">'
            f'<div class="q-head"><b>{html.escape(q["name"])}</b> '
            f'<span>@{html.escape(q["screen_name"])}</span></div>'
            f'<div class="q-text">{html.escape(q["text"]).replace(chr(10), "<br>")}</div>'
            "</div>"
        )

    stats_html = ""
    if s.get("show_stats"):
        st = tw.get("stats", {})
        stats_html = (
            '<div class="stats">'
            f'<span><b>{_fmt(st.get("retweets"))}</b> retweets</span>'
            f'<span><b>{_fmt(st.get("replies"))}</b> replies</span>'
            f'<span><b>{_fmt(st.get("likes"))}</b> likes</span>'
            "</div>"
        )

    date_html = (
        f'<div class="date">{html.escape(str(tw.get("created_at", "")))}</div>'
        if s.get("show_date") and tw.get("created_at")
        else ""
    )

    page_bg = s.get("page_bg", "#f5f8fa")
    bg_image = (s.get("bg_image") or "").strip()
    body_bg = (
        f"background:{page_bg} url('{html.escape(bg_image)}') center/cover no-repeat;"
        if bg_image
        else f"background:{page_bg};"
    )
    shadow = "box-shadow:0 12px 32px rgba(0,0,0,.18);" if s.get("shadow") else "box-shadow:none;"

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  * {{ box-sizing:border-box; }}
  body {{ margin:0; {body_bg} padding:{int(s['padding'])}px;
         font-family:'Vazirmatn','Noto Sans Arabic','Segoe UI',Arial,sans-serif;
         display:inline-block; }}
  .card {{ width:{int(s['width'])}px; background:{s['card_bg']}; color:{s['font_color']};
           border-radius:20px; padding:22px 24px; {shadow} }}
  .head {{ display:flex; align-items:center; gap:12px; }}
  .avatar {{ width:52px; height:52px; border-radius:50%; object-fit:cover; }}
  .name {{ font-weight:700; font-size:{int(s['font_size'])+1}px; display:flex; align-items:center; gap:5px; }}
  .handle {{ opacity:.6; font-size:{int(s['font_size'])-3}px; }}
  .badge {{ width:19px; height:19px; }}
  .text {{ margin-top:16px; font-size:{int(s['font_size'])}px; line-height:1.85;
           white-space:pre-wrap; direction:{direction}; text-align:{'right' if rtl else 'left'}; }}
  .media {{ margin-top:16px; display:grid; gap:4px; border-radius:16px; overflow:hidden; }}
  .grid-1 {{ grid-template-columns:1fr; }}
  .grid-2 {{ grid-template-columns:1fr 1fr; }}
  .grid-3, .grid-4 {{ grid-template-columns:1fr 1fr; }}
  .m-cell {{ position:relative; }}
  .m-cell img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .play {{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
           font-size:44px; color:#fff; text-shadow:0 2px 10px rgba(0,0,0,.6); }}
  .quote {{ margin-top:14px; border:1px solid rgba(0,0,0,.15); border-radius:14px; padding:12px 14px;
            font-size:{int(s['font_size'])-2}px; direction:{direction}; }}
  .q-head span {{ opacity:.6; }}
  .stats {{ margin-top:16px; display:flex; gap:16px; flex-wrap:wrap;
            font-size:{int(s['font_size'])-4}px; opacity:.85; }}
  .date {{ margin-top:8px; font-size:{int(s['font_size'])-5}px; opacity:.6; }}
</style></head>
<body><div class="card" id="card">
  <div class="head">
    <img class="avatar" src="{html.escape(a.get('avatar',''))}">
    <div>
      <div class="name">{html.escape(a.get('name',''))}{verified}</div>
      <div class="handle">@{html.escape(a.get('screen_name',''))}</div>
    </div>
  </div>
  <div class="text">{text}</div>
  {media_html}
  {quote_html}
  {stats_html}
  {date_html}
</div></body></html>"""


def screenshot(tw: Dict[str, Any], settings: Dict[str, Any], out_path: Optional[str] = None) -> str:

    from playwright.sync_api import sync_playwright

    out_path = out_path or os.path.join(config.TMP_DIR, f"tweet_{tw.get('id','x')}_{int(time.time())}.png")
    html_path = out_path.replace(".png", ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(build_html(tw, settings))

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": int(settings["width"]) + 2 * int(settings["padding"]) + 40,
                                          "height": 1000},
                                device_scale_factor=2)
        page.goto("file://" + html_path)
        page.wait_for_timeout(1200)
        page.locator("body").screenshot(path=out_path)
        browser.close()
    return out_path


def add_watermark(image_path: str, logo_path: str, settings: Dict[str, Any]) -> str:

    if not logo_path or not os.path.exists(logo_path):
        return image_path

    base = Image.open(image_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    target_w = max(40, int(base.width * int(settings.get("watermark_scale", 14)) / 100))
    ratio = target_w / logo.width
    logo = logo.resize((target_w, max(1, int(logo.height * ratio))), Image.LANCZOS)

    opacity = max(5, min(100, int(settings.get("watermark_opacity", 85)))) / 100
    alpha = logo.getchannel("A").point(lambda v: int(v * opacity))
    logo.putalpha(alpha)

    margin = max(12, int(base.width * 0.025))
    pos_key = settings.get("watermark_pos", "bottom-right")
    positions = {
        "top-left": (margin, margin),
        "top-right": (base.width - logo.width - margin, margin),
        "bottom-left": (margin, base.height - logo.height - margin),
        "bottom-right": (base.width - logo.width - margin, base.height - logo.height - margin),
        "center": ((base.width - logo.width) // 2, (base.height - logo.height) // 2),
    }
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(logo, positions.get(pos_key, positions["bottom-right"]), logo)
    result = Image.alpha_composite(base, layer).convert("RGB")

    out = image_path.replace(".png", "_wm.jpg")
    result.save(out, "JPEG", quality=94)
    return out


def build_caption(title: str, body: str, settings: Dict[str, Any], channel: str = "") -> str:

    lines = []
    if title:
        lines.append(f"<b>{html.escape(title)}</b> {settings.get('title_emoji','')}")
        lines.append("")
    if body:
        for para in [p.strip() for p in body.split("\n") if p.strip()]:
            lines.append(f"{settings.get('paragraph_emoji','')} {html.escape(para)}")
            lines.append("")
    if channel:
        lines.append(f"📣 کانال: @{channel.lstrip('@')}")
    return "\n".join(lines).strip()
