from telebot import types

BTN_SEND = "🕊 ارسال توییت"
BTN_CHANNELS = "▪️ مدیریت کانال ها"
BTN_ADD_CHANNEL = "➕ افزودن کانال"
BTN_SETTINGS = "⚙️ تنطیمات".replace("تنطیمات", "تنظیمات")
BTN_ACCOUNTS = "👑 مدیریت اکانت"
BTN_BACK = "⬅️ بازگشت"


def main_menu() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(BTN_SEND)
    kb.row(BTN_CHANNELS, BTN_ADD_CHANNEL)
    kb.row(BTN_SETTINGS, BTN_ACCOUNTS)
    return kb


def back_menu() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(BTN_BACK)
    return kb


def channels_manage(channels) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("📣 آیدی", callback_data="noop"),
        types.InlineKeyboardButton("👁 لوگو", callback_data="noop"),
        types.InlineKeyboardButton("❌ حذف", callback_data="noop"),
    )
    for ch in channels:
        title = ch["chat_id"]
        kb.row(
            types.InlineKeyboardButton(title[:20], callback_data=f"ch:info:{ch['id']}"),
            types.InlineKeyboardButton("👁", callback_data=f"ch:logo:{ch['id']}"),
            types.InlineKeyboardButton("❌", callback_data=f"ch:del:{ch['id']}"),
        )
    return kb


def channel_picker(channels) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    for ch in channels:
        kb.add(types.InlineKeyboardButton(ch["chat_id"], callback_data=f"post:{ch['id']}"))
    kb.add(types.InlineKeyboardButton("❌ انصراف", callback_data="cancel"))
    return kb


def confirm_send() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ تایید و ارسال", callback_data="confirm"))
    kb.add(types.InlineKeyboardButton("❌ انصراف", callback_data="cancel"))
    return kb


def _onoff(v) -> str:
    return "✅" if int(v) else "❌"


def settings_menu(s) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton(f"{s['title_emoji']}", callback_data="set:ask:title_emoji"),
        types.InlineKeyboardButton("ایموجی تیتر", callback_data="set:ask:title_emoji"),
    )
    kb.row(
        types.InlineKeyboardButton(f"{s['paragraph_emoji']}", callback_data="set:ask:paragraph_emoji"),
        types.InlineKeyboardButton("ایموجی پاراگراف", callback_data="set:ask:paragraph_emoji"),
    )
    kb.row(
        types.InlineKeyboardButton(f"{s['font_size']}px", callback_data="set:ask:font_size"),
        types.InlineKeyboardButton("اندازه فونت", callback_data="set:ask:font_size"),
    )
    kb.row(
        types.InlineKeyboardButton(f"{s['font_color']}", callback_data="set:ask:font_color"),
        types.InlineKeyboardButton("رنگ فونت", callback_data="set:ask:font_color"),
    )
    kb.row(
        types.InlineKeyboardButton(f"{s['card_bg']}", callback_data="set:ask:card_bg"),
        types.InlineKeyboardButton("رنگ پس‌زمینه توییت", callback_data="set:ask:card_bg"),
    )
    kb.row(
        types.InlineKeyboardButton(f"{s['page_bg']}", callback_data="set:ask:page_bg"),
        types.InlineKeyboardButton("رنگ پس‌زمینه کلی", callback_data="set:ask:page_bg"),
    )
    kb.row(
        types.InlineKeyboardButton("🖼" if s["bg_image"] else "—", callback_data="set:ask:bg_image"),
        types.InlineKeyboardButton("تصویر پس‌زمینه (لینک)", callback_data="set:ask:bg_image"),
    )
    kb.row(
        types.InlineKeyboardButton(_onoff(s["show_stats"]), callback_data="set:tg:show_stats"),
        types.InlineKeyboardButton("نمایش آمار (لایک/ریتوییت/کامنت)", callback_data="set:tg:show_stats"),
    )
    kb.row(
        types.InlineKeyboardButton(_onoff(s["show_verified"]), callback_data="set:tg:show_verified"),
        types.InlineKeyboardButton("نمایش تیک تأیید", callback_data="set:tg:show_verified"),
    )
    kb.row(
        types.InlineKeyboardButton(_onoff(s["show_quote"]), callback_data="set:tg:show_quote"),
        types.InlineKeyboardButton("نمایش توییت نقل‌قول", callback_data="set:tg:show_quote"),
    )
    kb.row(
        types.InlineKeyboardButton(_onoff(s["show_date"]), callback_data="set:tg:show_date"),
        types.InlineKeyboardButton("نمایش تاریخ و زمان", callback_data="set:tg:show_date"),
    )
    kb.row(
        types.InlineKeyboardButton(_onoff(s["show_media"]), callback_data="set:tg:show_media"),
        types.InlineKeyboardButton("نمایش عکس/ویدیو", callback_data="set:tg:show_media"),
    )
    kb.row(
        types.InlineKeyboardButton(_onoff(s["shadow"]), callback_data="set:tg:shadow"),
        types.InlineKeyboardButton("سایه کارت", callback_data="set:tg:shadow"),
    )
    kb.row(
        types.InlineKeyboardButton(f"{s['padding']}px", callback_data="set:ask:padding"),
        types.InlineKeyboardButton("فاصله از حاشیه", callback_data="set:ask:padding"),
    )
    kb.row(
        types.InlineKeyboardButton(f"{s['width']}px", callback_data="set:ask:width"),
        types.InlineKeyboardButton("عرض نهایی تصویر", callback_data="set:ask:width"),
    )
    kb.row(
        types.InlineKeyboardButton(f"{s['watermark_scale']}%", callback_data="set:ask:watermark_scale"),
        types.InlineKeyboardButton("اندازه لوگو", callback_data="set:ask:watermark_scale"),
    )
    kb.row(
        types.InlineKeyboardButton(f"{s['watermark_opacity']}%", callback_data="set:ask:watermark_opacity"),
        types.InlineKeyboardButton("شفافیت لوگو", callback_data="set:ask:watermark_opacity"),
    )
    kb.row(
        types.InlineKeyboardButton(s["watermark_pos"], callback_data="set:pos"),
        types.InlineKeyboardButton("جای لوگو", callback_data="set:pos"),
    )
    kb.add(types.InlineKeyboardButton("♻️ بازگردانی پیش‌فرض", callback_data="set:reset"))
    return kb


def accounts_menu(admins) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    for ad in admins:
        label = f"{ad['user_id']}" + (f" (@{ad['username']})" if ad["username"] else "")
        kb.row(
            types.InlineKeyboardButton(label, callback_data="noop"),
            types.InlineKeyboardButton("❌", callback_data=f"adm:del:{ad['user_id']}"),
        )
    kb.add(types.InlineKeyboardButton("➕ افزودن ادمین", callback_data="adm:add"))
    return kb
