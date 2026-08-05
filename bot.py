import html
import json
import logging
import os
import traceback

import telebot
from telebot import types

import config
import db
import keyboards as kbs
import renderer
import tweet as tw_api

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("tweetshot")

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML")

WM_POSITIONS = ["bottom-right", "bottom-left", "top-right", "top-left", "center"]


def esc(text) -> str:
    return html.escape(str(text), quote=False)


def safe_error(text, limit: int = 500) -> str:
    s = " ".join(str(text).split())
    if len(s) > limit:
        s = s[:limit] + " …"
    return esc(s)


def send_plain(chat_id, text, **kw):
    return bot.send_message(chat_id, text, parse_mode=None, **kw)


def guard(func):

    def wrapper(obj, *a, **kw):
        try:
            return func(obj, *a, **kw)
        except Exception as e:
            log.error("handler %s failed: %s", func.__name__, traceback.format_exc())
            try:
                chat_id = getattr(getattr(obj, "message", obj), "chat", None)
                if chat_id is not None:
                    send_plain(chat_id.id, f"❌ خطای غیرمنتطره: {' '.join(str(e).split())[:400]}")
            except Exception:
                pass

    wrapper.__name__ = func.__name__
    return wrapper


def admin_only(func):
    def wrapper(message, *a, **kw):
        uid = message.from_user.id
        if not db.is_admin(uid):
            bot.send_message(message.chat.id, "⛔️ این ربات مخصوص ادمین‌هاست.")
            return
        return func(message, *a, **kw)

    wrapper.__name__ = func.__name__
    return wrapper


def payload(uid) -> dict:
    _, raw = db.get_state(uid)
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}


def set_payload(uid, state, data: dict) -> None:
    db.set_state(uid, state, json.dumps(data, ensure_ascii=False))


def download_photo(file_id: str, dest: str) -> str:
    info = bot.get_file(file_id)
    content = bot.download_file(info.file_path)
    with open(dest, "wb") as f:
        f.write(content)
    return dest


@bot.message_handler(commands=["start", "menu"])
def cmd_start(m):
    if not db.is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "⛔️ این ربات مخصوص ادمین‌هاست.")
        return
    db.clear_state(m.from_user.id)
    bot.send_message(m.chat.id, "🔽 برای شروع یکی از گزینه های زیر را انتخاب کنید:",
                     reply_markup=kbs.main_menu())


@bot.message_handler(func=lambda m: m.text == kbs.BTN_BACK)
def go_back(m):
    cmd_start(m)



@bot.message_handler(func=lambda m: m.text == kbs.BTN_SEND)
@admin_only
def ask_tweet_link(m):
    db.set_state(m.from_user.id, "await_link")
    bot.send_message(m.chat.id, "🔗 لینک توییت را ارسال کنید:", reply_markup=kbs.back_menu())


@bot.message_handler(func=lambda m: m.text == kbs.BTN_CHANNELS)
@admin_only
def manage_channels(m):
    chans = db.list_channels(m.from_user.id)
    if not chans:
        bot.send_message(m.chat.id, "یچ کانالی ثبت نشده است.".replace("یچ", "هیچ"))
        return
    text = (
        "📋 لیست کانال های موجود:\n\n"
        f"تعداد کل: {len(chans)} کانال\n\n"
        "💡 برای مشاهده جزئیات هر کانال روی ایدی آن کلیک کنید"
    )
    bot.send_message(m.chat.id, text, reply_markup=kbs.channels_manage(chans))


@bot.message_handler(func=lambda m: m.text == kbs.BTN_ADD_CHANNEL)
@admin_only
def add_channel_start(m):
    db.set_state(m.from_user.id, "await_channel")
    bot.send_message(
        m.chat.id,
        "➕ آیدی کانال را ارسال کنید (مانند <code>@mychannel</code> یا <code>-1001234567890</code>)\n\n"
        "⚠️ ربات باید ادمین کانال باشد.",
        reply_markup=kbs.back_menu(),
    )


@bot.message_handler(func=lambda m: m.text == kbs.BTN_SETTINGS)
@admin_only
def settings_cmd(m):
    s = db.get_settings(m.from_user.id)
    bot.send_message(
        m.chat.id,
        "⚙️ تنظیمات ربات\n\n🔧 برای تغییر هر مورد روی مقدار مقابل آن بزنید:",
        reply_markup=kbs.settings_menu(s),
    )


@bot.message_handler(func=lambda m: m.text == kbs.BTN_ACCOUNTS)
@admin_only
def accounts_cmd(m):
    if m.from_user.id not in config.ADMINS:
        bot.send_message(m.chat.id, "⛔️ فقط مالک ربات می‌تواند ادمین‌ها را مدیریت کند.")
        return
    bot.send_message(m.chat.id, "👑 مدیریت اکانت ادمین‌ها:", reply_markup=kbs.accounts_menu(db.list_admins()))


@bot.message_handler(content_types=["text"])
@guard
def on_text(m):
    uid = m.from_user.id
    if not db.is_admin(uid):
        return
    state, _ = db.get_state(uid)
    data = payload(uid)

    if state == "await_link":
        if not tw_api.parse_url(m.text):
            bot.reply_to(m, "❌ لینک توییت معتبر نیست. دوباره تلاش کنید.")
            return
        wait = bot.reply_to(m, "⏳ در حال دریافت توییت و ساخت اسکرین‌شات...")
        try:
            tw = tw_api.fetch(m.text)
            s = db.get_settings(uid)
            shot = renderer.screenshot(tw, s)
        except Exception as e:
            log.error("render failed: %s", traceback.format_exc())
            try:
                bot.edit_message_text(
                    f"❌ خطا: {' '.join(str(e).split())[:500]}",
                    wait.chat.id,
                    wait.message_id,
                    parse_mode=None,
                )
            except Exception:
                send_plain(m.chat.id, f"❌ خطا: {' '.join(str(e).split())[:500]}")
            db.clear_state(uid)
            return

        set_payload(uid, "await_caption", {"shot": shot, "tweet": tw})
        bot.delete_message(wait.chat.id, wait.message_id)
        with open(shot, "rb") as f:
            bot.send_photo(m.chat.id, f, caption="✅ پیش‌نمایش توییت آماده شد!\n\nحالا کپشن مورد نظر خود را ارسال کنید:")
        if tw.get("video_url"):
            send_plain(m.chat.id, f"🎥 ویدیوی توییت: {tw['video_url']}")
        return

    if state == "await_caption":
        lines = m.text.split("\n")
        data["title"] = lines[0].strip()
        data["body"] = "\n".join(lines[1:]).strip()
        s = db.get_settings(uid)
        chans = db.list_channels(uid)
        if not chans:
            bot.reply_to(m, "⚠️ هیچ کانالی ثبت نکرده‌اید. ابتدا از «افزودن کانال» استفاده کنید.")
            return
        set_payload(uid, "await_channel_pick", data)
        preview = renderer.build_caption(data["title"], data["body"], s)
        bot.send_message(
            m.chat.id,
            "📋 کانال مورد نظر خود را از لیست زیر انتخاب کنید:\n\n🔍 پیش‌نمایش کپشن:\n" + preview,
            reply_markup=kbs.channel_picker(chans),
        )
        return

    if state == "await_channel":
        chat_id = m.text.strip()
        try:
            info = bot.get_chat(chat_id)
            title = info.title or ""
        except Exception:
            bot.reply_to(m, "❌ دسترسی به کانال ممکن نیست. ربات را ادمین کانال کنید.")
            return
        cid = db.add_channel(uid, chat_id, title)
        set_payload(uid, "await_logo", {"channel_id": cid})
        bot.reply_to(m, f"✅ کانال <b>{esc(title or chat_id)}</b> ثبت شد.\n\n🖼 اکنون لوگوی کانال را به صورت عکس ارسال کنید (ترجیحاً PNG شفاف):")
        return

    if state.startswith("set:"):
        key = state.split(":", 1)[1]
        value = m.text.strip()
        if key in config.INT_KEYS:
            try:
                value = int("".join(ch for ch in value if ch.isdigit()))
            except ValueError:
                bot.reply_to(m, "❌ عدد معتبر وارد کنید.")
                return
        db.set_setting(uid, key, value)
        db.clear_state(uid)
        bot.reply_to(m, "✅ تنطیم ذخیره شد.".replace("تنطیم", "تنظیم"))
        s = db.get_settings(uid)
        bot.send_message(m.chat.id, "⚙️ تنظیمات ربات:", reply_markup=kbs.settings_menu(s))
        return

    if state == "await_admin_id":
        try:
            new_id = int(m.text.strip())
        except ValueError:
            bot.reply_to(m, "❌ آیدی عددی وارد کنید.")
            return
        db.add_admin(new_id, added_by=uid)
        db.clear_state(uid)
        bot.reply_to(m, f"✅ ادمین <code>{new_id}</code> اضافه شد.")
        return

    if tw_api.parse_url(m.text):
        db.set_state(uid, "await_link")
        on_text(m)
        return

    bot.send_message(m.chat.id, "🔽 یکی از گزینه‌ها را انتخاب کنید:", reply_markup=kbs.main_menu())


@bot.message_handler(content_types=["photo", "document"])
@guard
def on_photo(m):
    uid = m.from_user.id
    if not db.is_admin(uid):
        return
    state, _ = db.get_state(uid)
    data = payload(uid)
    if state != "await_logo":
        return
    channel_id = data.get("channel_id")
    file_id = m.photo[-1].file_id if m.content_type == "photo" else m.document.file_id
    dest = os.path.join(config.LOGO_DIR, f"logo_{channel_id}.png")
    try:
        download_photo(file_id, dest)
    except Exception as e:
        send_plain(m.chat.id, f"❌ دریافت لوگو ناموفق بود: {' '.join(str(e).split())[:400]}")
        return
    db.set_channel_logo(channel_id, dest)
    db.clear_state(uid)
    bot.reply_to(m, "✅ لوگوی کانال ذخیره شد.", reply_markup=kbs.main_menu())


@bot.callback_query_handler(func=lambda c: True)
@guard
def on_callback(c):
    uid = c.from_user.id
    if not db.is_admin(uid):
        bot.answer_callback_query(c.id, "⛔️ دسترسی ندارید.")
        return
    data = c.data or ""

    if data == "noop":
        bot.answer_callback_query(c.id)
        return

    if data == "cancel":
        db.clear_state(uid)
        bot.answer_callback_query(c.id, "لغو شد")
        bot.send_message(c.message.chat.id, "❌ عملیات لغو شد.", reply_markup=kbs.main_menu())
        return

    if data.startswith("ch:"):
        _, action, cid = data.split(":")
        cid = int(cid)
        ch = db.get_channel(cid)
        if not ch or ch["owner_id"] != uid:
            bot.answer_callback_query(c.id, "یافت نشد")
            return
        if action == "del":
            db.delete_channel(cid, uid)
            bot.answer_callback_query(c.id, "حذف شد")
            bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                          reply_markup=kbs.channels_manage(db.list_channels(uid)))
            return
        if action == "logo":
            set_payload(uid, "await_logo", {"channel_id": cid})
            bot.answer_callback_query(c.id)
            bot.send_message(c.message.chat.id, "🖼 لوگوی جدید این کانال را ارسال کنید:")
            return
        if action == "info":
            bot.answer_callback_query(c.id)
            bot.send_message(
                c.message.chat.id,
                f"📣 کانال: <code>{esc(ch['chat_id'])}</code>\nعنوان: {esc(ch['title'] or '-')}\n"
                f"لوگو: {'✅ دارد' if ch['logo_path'] else '❌ ندارد'}",
            )
            return

    if data.startswith("post:"):
        cid = int(data.split(":")[1])
        d = payload(uid)
        d["channel_id"] = cid
        set_payload(uid, "await_confirm", d)
        ch = db.get_channel(cid)
        s = db.get_settings(uid)
        shot = d.get("shot")
        final = renderer.add_watermark(shot, ch["logo_path"], s) if shot else None
        d["final"] = final
        set_payload(uid, "await_confirm", d)
        caption = renderer.build_caption(d.get("title", ""), d.get("body", ""), s, ch["chat_id"])
        bot.answer_callback_query(c.id)
        if final:
            with open(final, "rb") as f:
                bot.send_photo(c.message.chat.id, f, caption="🔍 پیش‌نمایش نهایی:\n\n" + caption,
                               reply_markup=kbs.confirm_send())
        return

    if data == "confirm":
        d = payload(uid)
        ch = db.get_channel(d.get("channel_id", 0))
        s = db.get_settings(uid)
        if not ch or not d.get("final"):
            bot.answer_callback_query(c.id, "اطلاعات منقضی شده، دوباره تلاش کنید")
            return
        caption = renderer.build_caption(d.get("title", ""), d.get("body", ""), s, ch["chat_id"])
        try:
            with open(d["final"], "rb") as f:
                bot.send_photo(ch["chat_id"], f, caption=caption)
            tw = d.get("tweet") or {}
            if tw.get("video_url") and s.get("show_media"):
                bot.send_message(ch["chat_id"], f"🎥 {tw['video_url']}", parse_mode=None)
            bot.answer_callback_query(c.id, "ارسال شد ✅")
            bot.send_message(c.message.chat.id, f"✅ پست به کانال <code>{esc(ch['chat_id'])}</code> ارسال شد.",
                             reply_markup=kbs.main_menu())
        except Exception as e:
            log.error("send failed: %s", traceback.format_exc())
            bot.answer_callback_query(c.id, "خطا در ارسال")
            send_plain(c.message.chat.id, f"❌ ارسال ناموفق: {' '.join(str(e).split())[:400]}")
        db.clear_state(uid)
        return

    if data.startswith("set:"):
        parts = data.split(":")
        if parts[1] == "tg":
            db.toggle_setting(uid, parts[2])
            bot.answer_callback_query(c.id, "بروز شد")
            bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                          reply_markup=kbs.settings_menu(db.get_settings(uid)))
            return
        if parts[1] == "pos":
            s = db.get_settings(uid)
            cur = s.get("watermark_pos", WM_POSITIONS[0])
            nxt = WM_POSITIONS[(WM_POSITIONS.index(cur) + 1) % len(WM_POSITIONS)] if cur in WM_POSITIONS else WM_POSITIONS[0]
            db.set_setting(uid, "watermark_pos", nxt)
            bot.answer_callback_query(c.id, nxt)
            bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                          reply_markup=kbs.settings_menu(db.get_settings(uid)))
            return
        if parts[1] == "reset":
            db.reset_settings(uid)
            bot.answer_callback_query(c.id, "پیش‌فرض شد")
            bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                          reply_markup=kbs.settings_menu(db.get_settings(uid)))
            return
        if parts[1] == "ask":
            key = parts[2]
            db.set_state(uid, f"set:{key}")
            hints = {
                "title_emoji": "ایموجی تیتر را ارسال کنید (مانند 📌)",
                "paragraph_emoji": "ایموجی پاراگراف را ارسال کنید (مانند 🔹)",
                "font_size": "اندازه فونت را به پیکسل بفرستید (مثال: 20)",
                "font_color": "کد رنگ فونت (مثال: #0f1419)",
                "card_bg": "کد رنگ پس‌زمینه کارت توییت (مثال: #ffffff)",
                "page_bg": "کد رنگ پس‌زمینه کلی (مثال: #f5f8fa)",
                "bg_image": "لینک تصویر پس‌زمینه را ارسال کنید (برای حذف: -)",
                "padding": "فاصله از حاشیه به پیکسل (مثال: 40)",
                "width": "عرض نهایی تصویر به پیکسل (مثال: 720)",
                "watermark_scale": "اندازه لوگو بر حسب درصد عرض (مثال: 14)",
                "watermark_opacity": "شفافیت لوگو بر حسب درصد (مثال: 85)",
            }
            bot.answer_callback_query(c.id)
            bot.send_message(c.message.chat.id, "✏️ " + hints.get(key, "مقدار جدید را ارسال کنید:"),
                             reply_markup=kbs.back_menu())
            return

    if data.startswith("adm:"):
        if uid not in config.ADMINS:
            bot.answer_callback_query(c.id, "⛔️ فقط مالک ربات")
            return
        parts = data.split(":")
        if parts[1] == "add":
            db.set_state(uid, "await_admin_id")
            bot.answer_callback_query(c.id)
            bot.send_message(c.message.chat.id, "🆔 آیدی عددی کاربر را ارسال کنید:", reply_markup=kbs.back_menu())
            return
        if parts[1] == "del":
            db.remove_admin(int(parts[2]))
            bot.answer_callback_query(c.id, "حذف شد")
            bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                          reply_markup=kbs.accounts_menu(db.list_admins()))
            return

    bot.answer_callback_query(c.id)


def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN در فایل .env تنطیم نشده است.".replace("تنطیم", "تنظیم"))
    db.init()
    for owner in config.ADMINS:
        db.add_admin(owner)
    log.info("Bot started. Admins: %s", config.ADMINS)
    bot.infinity_polling(skip_pending=True, timeout=30)


if __name__ == "__main__":
    main()
