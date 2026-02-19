import logging, json, os, random
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(level=logging.WARNING)
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
DB    = "data.json"
KYIV  = ZoneInfo("Europe/Kiev")

LEVELS = [
    (0,     1,   "🥚", "Яєчко"),
    (100,   3,   "🐛", "Гусінь"),
    (400,   6,   "🐌", "Слизняк"),
    (1000,  12,  "🦎", "Ящірка"),
    (2500,  22,  "🦊", "Лисиця"),
    (6000,  38,  "🦄", "Єдиноріг"),
    (15000, 60,  "🐉", "Дракон"),
    (35000, 95,  "👾", "Легенда"),
    (80000, 150, "✨", "Бог Лупиздрик"),
]
UPGRADES = [
    ("paw",    "🐾 Золота лапа",          "+50% до сили",   500,    1.5),
    ("drink",  "⚡ Енергетик",            "+100% до сили",  2500,   2.0),
    ("rocket", "🚀 Ракетний прискорювач", "+200% до сили",  10000,  3.0),
    ("cosmos", "🌌 Космічна сила",        "+500% до сили",  40000,  6.0),
    ("quantum","🔮 Квантовий тап",        "+1000% до сили", 150000, 11.0),
]
ACHIEVEMENTS = [
    ("t1",    "🎯 Перший тап!",         1,      0),
    ("t100",  "💯 Сотня!",              100,    0),
    ("t1k",   "🔥 Тисячник!",           1000,   0),
    ("t10k",  "💎 Десятитисячник!",     10000,  0),
    ("t50k",  "👑 П'ятдесятитисячник!", 50000,  0),
    ("t100k", "🌟 Легенда!",            100000, 0),
    ("s7",    "📅 Тиждень стріку!",     0,      7),
    ("s30",   "🗓 Місяць стріку!",      0,      30),
]
MEDALS = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

# ── БД ──────────────────────────────────────────────────────────────
def load():
    if os.path.exists(DB):
        d = json.load(open(DB, encoding="utf-8"))
        if "users" not in d:
            d = {"users": d, "groups": {}}
    else:
        d = {"users": {}, "groups": {}}
    d.setdefault("groups", {})
    return d

def save(d):
    json.dump(d, open(DB, "w", encoding="utf-8"), ensure_ascii=False)

def get_user(d, uid):
    u = d["users"].setdefault(str(uid), {})
    u.setdefault("name", "Гравець")
    u.setdefault("uname", None)
    u.setdefault("taps", 0)
    u.setdefault("coins", 0)
    u.setdefault("upg", [])
    u.setdefault("ach", [])
    u.setdefault("streak", 0)
    u.setdefault("hist", {})
    u.setdefault("tap_date", None)
    u.setdefault("bonus_date", None)
    return u

def add_member(d, gid, uid):
    g = d["groups"].setdefault(str(gid), {"title": "", "members": []})
    g.setdefault("members", [])
    if str(uid) not in g["members"]:
        g["members"].append(str(uid))

def get_members(d, gid):
    return d["groups"].get(str(gid), {}).get("members", [])

# ── ІГРОВА ЛОГІКА ────────────────────────────────────────────────────
def kyiv_today():
    return datetime.now(KYIV).date().isoformat()

def can_tap(u):
    return u.get("tap_date") != kyiv_today()

def time_to_reset():
    now  = datetime.now(KYIV)
    next_midnight = datetime.combine(now.date() + timedelta(days=1), dtime(0, 0), tzinfo=KYIV)
    diff = next_midnight - now
    h = int(diff.total_seconds() // 3600)
    m = int((diff.total_seconds() % 3600) // 60)
    return f"{h}год {m}хв"

def calc_power(u):
    p = get_level(u["taps"])[1]
    for uid in u.get("upg", []):
        for upg in UPGRADES:
            if upg[0] == uid:
                p = int(p * upg[4])
    return p

def do_tap(u):
    base = calc_power(u)
    r = random.random()
    if   r < 0.50: mult = random.uniform(0.5,  1.5)   # 50% — звичайно
    elif r < 0.80: mult = random.uniform(1.5,  3.0)   # 30% — добре
    elif r < 0.95: mult = random.uniform(3.0,  6.0)   # 15% — відмінно
    else:          mult = random.uniform(6.0, 15.0)   #  5% — ДЖЕКПОТ

    gt = max(1, int(base * mult))
    gc = max(1, int(gt * random.uniform(0.3, 1.2)))
    u["taps"]  += gt
    u["coins"] += gc

    today = kyiv_today()
    yest  = (datetime.now(KYIV).date() - timedelta(days=1)).isoformat()

    if u.get("bonus_date") == yest:
        u["streak"] = u.get("streak", 0) + 1
    elif u.get("bonus_date") != today:
        u["streak"] = 1
    u["tap_date"]   = today
    u["bonus_date"] = today

    h = u.setdefault("hist", {})
    h[today] = h.get(today, 0) + gt
    cut = (datetime.now(KYIV).date() - timedelta(days=35)).isoformat()
    u["hist"] = {k: v for k, v in h.items() if k > cut}

    return gt, gc, mult

def get_level(taps):
    result = LEVELS[0]
    for L in LEVELS:
        if taps >= L[0]: result = L
        else: break
    return result

def get_next_level(taps):
    for L in LEVELS:
        if taps < L[0]: return L
    return None

def check_achievements(u):
    new = []
    for a in ACHIEVEMENTS:
        if a[0] in u.get("ach", []): continue
        unlocked = (a[2] > 0 and u["taps"] >= a[2]) or \
                   (a[3] > 0 and u.get("streak", 0) >= a[3])
        if unlocked:
            u.setdefault("ach", []).append(a[0])
            new.append(a)
    return new

def period_taps(u, period):
    if period == "all":
        return u.get("taps", 0)
    days = {"day": 1, "week": 7, "month": 30}[period]
    cut  = (datetime.now(KYIV).date() - timedelta(days=days)).isoformat()
    return sum(v for k, v in u.get("hist", {}).items() if k > cut)

# ── ТЕКСТ / КЛАВІАТУРИ ───────────────────────────────────────────────
def btn(text, cb):
    return InlineKeyboardButton(text, callback_data=cb)

def progress_bar(u):
    L  = get_level(u["taps"])
    nL = get_next_level(u["taps"])
    if not nL:
        return "🌟 Максимальний рівень!"
    total = nL[0] - L[0]
    done  = u["taps"] - L[0]
    pct   = min(10, int(done / total * 10)) if total else 10
    need  = nL[0] - u["taps"]
    return f"`[{'█'*pct+'░'*(10-pct)}]` ще {need:,} → {nL[2]} {nL[3]}"

def main_text(u, d=None, gid=None):
    L   = get_level(u["taps"])
    p   = calc_power(u)
    ct  = can_tap(u)
    upg_txt = ""
    if u.get("upg"):
        names = [ug[1] for ug in UPGRADES if ug[0] in u["upg"]]
        upg_txt = "\n🔧 " + " · ".join(names)
    tap_st = "✅ Можеш тапнути!" if ct else f"⏳ Наступний о 00:00 (через {time_to_reset()})"
    rank_txt = ""
    if d and gid:
        ms     = get_members(d, gid)
        md     = [d["users"][m] for m in ms if m in d["users"]]
        ranked = sorted(md, key=lambda x: x.get("taps", 0), reverse=True)
        pos    = next((i + 1 for i, x in enumerate(ranked) if x is u), "-")
        rank_txt = f"\n🏆 Місце в групі: *#{pos}* з {len(ranked)}"
    return (
        f"╔══════════════════╗\n"
        f"    🦎 *ЛУПИЗДРИК* 🦎\n"
        f"╚══════════════════╝\n\n"
        f"{L[2]} *{L[3]}* {L[2]}\n"
        f"{progress_bar(u)}\n\n"
        f"👆 Тапів: *{u['taps']:,}*{rank_txt}\n"
        f"💰 Монет: *{u['coins']:,}* | ⚡ Сила: *{p}*\n"
        f"🔥 Стрік: *{u.get('streak', 0)} дн* | "
        f"🎖 Досяг: *{len(u.get('ach', []))}/{len(ACHIEVEMENTS)}*"
        f"{upg_txt}\n\n"
        f"{tap_st}"
    )

def main_kb(u, gid=None):
    L   = get_level(u["taps"])
    ct  = can_tap(u)
    lbl = f"{L[2]} ТАП! {L[2]}" if ct else "⏳ Вже тапнув сьогодні"
    return InlineKeyboardMarkup([
        [btn(lbl, "tap")],
        [btn("🏪 Магазин", "shop"), btn("🎖 Досягнення", "ach")],
        [btn("🏆 Топ групи", f"lb_{gid or 0}_all")],
    ])

def lb_text(d, gid, period):
    labels = {"day":"📅 ДЕНЬ","week":"📆 ТИЖДЕНЬ","month":"🗓 МІСЯЦЬ","all":"🏅 УСЕ"}
    ms  = get_members(d, gid)
    hdr = f"🏆 *ТОП — {labels[period]}*\n\n"
    if not ms:
        return hdr + "_Поки нікого. Напиши_ `.тап`_!_"
    top = sorted(
        [(m, d["users"][m]) for m in ms if m in d["users"]],
        key=lambda x: period_taps(x[1], period),
        reverse=True
    )[:10]
    txt   = hdr
    shown = 0
    for i, (uid, u) in enumerate(top):
        t = period_taps(u, period)
        if t == 0: break
        nm  = f"@{u['uname']}" if u.get("uname") else u.get("name", "???")
        txt += f"{MEDALS[i]} *{nm}* {get_level(u['taps'])[2]}\n   👆 {t:,} тапів\n\n"
        shown += 1
    if not shown:
        txt += "_Ніхто не тапав за цей період_"
    return txt

def lb_kb(gid, period):
    defs = [("📅 День","day"),("📆 Тиждень","week"),("🗓 Місяць","month"),("🏅 Все","all")]
    row  = [btn(("▶ " if p == period else "") + l, f"lb_{gid}_{p}") for l, p in defs]
    return InlineKeyboardMarkup([row, [btn("🔙 Назад", f"back_{gid}")]])

def shop_text(u):
    txt     = f"🏪 *Магазин покращень*\n💰 У тебе: *{u['coins']:,}* монет\n\n"
    owned   = u.get("upg", [])
    has_any = False
    for upg in UPGRADES:
        if upg[0] in owned:
            continue
        has_any = True
        mark = "✅" if u.get("coins", 0) >= upg[3] else "❌"
        txt += f"{upg[1]} {mark}\n  └ {upg[2]} · *{upg[3]:,}* 💰\n\n"
    if not has_any:
        txt += "🎉 _Усі покращення куплені!_"
    return txt

def shop_kb(u, gid):
    owned = u.get("upg", [])
    rows  = []
    for upg in UPGRADES:
        if upg[0] in owned:
            rows.append([btn(f"✅ {upg[1]}", "noop")])
        else:
            rows.append([btn(f"{upg[1]} — {upg[3]:,} 💰", f"buy_{upg[0]}_{gid}")])
    rows.append([btn("🔙 Назад", f"back_{gid}")])
    return InlineKeyboardMarkup(rows)

# ── ХЕНДЛЕРИ ─────────────────────────────────────────────────────────
def setup(d, update):
    tg   = update.effective_user
    chat = update.effective_chat
    u    = get_user(d, tg.id)
    u["name"]  = tg.first_name or "Гравець"
    u["uname"] = tg.username
    gid = chat.id if chat.type in ("group", "supergroup") else None
    if gid:
        d["groups"].setdefault(str(gid), {"title": "", "members": []})
        d["groups"][str(gid)]["title"] = chat.title or ""
        add_member(d, gid, tg.id)
    return u, gid

def is_direct(msg):
    return msg.reply_to_message is None

async def on_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_direct(update.message): return
    d = load()
    u, gid = setup(d, update)
    save(d)
    await update.message.reply_text(
        main_text(u, d, gid),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb(u, gid)
    )

async def on_tap(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_direct(update.message): return
    d = load()
    u, gid = setup(d, update)
    if not can_tap(u):
        save(d)
        await update.message.reply_text(
            f"⏳ *Вже тапнув сьогодні!*\n\nНаступний тап о 00:00 по Києву\n(через {time_to_reset()})",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    gt, gc, mult = do_tap(u)
    new = check_achievements(u)
    save(d)
    if   mult >= 6:   hdr = f"🎰 *ДЖЕКПОТ! ×{mult:.1f}!*"
    elif mult >= 3:   hdr = f"🔥 *Відмінно! ×{mult:.1f}*"
    elif mult >= 1.5: hdr = f"✨ *Гарний тап! ×{mult:.1f}*"
    else:             hdr = f"👆 *Тап ×{mult:.1f}*"
    ach_txt = ("\n\n🎉 " + ", ".join(a[1] for a in new)) if new else ""
    await update.message.reply_text(
        f"{hdr}\n👆 +*{gt:,}* тапів | 💰 +*{gc:,}* монет{ach_txt}\n\n{main_text(u, d, gid)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb(u, gid)
    )

async def on_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_direct(update.message): return
    d = load()
    u, gid = setup(d, update)
    save(d)
    if not gid:
        await update.message.reply_text("❌ Ця команда тільки для груп!")
        return
    await update.message.reply_text(
        lb_text(d, gid, "all"),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=lb_kb(gid, "all")
    )

async def on_btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()
    d    = load()
    tg   = q.from_user
    u    = get_user(d, tg.id)
    u["name"]  = tg.first_name or "Гравець"
    u["uname"] = tg.username
    a    = q.data
    chat = q.message.chat
    gid  = chat.id if chat.type in ("group", "supergroup") else None
    if gid:
        add_member(d, gid, tg.id)

    # noop — куплені апгрейди
    if a == "noop":
        return

    # Назад
    if a.startswith("back_"):
        gid_s = a[5:]
        gid   = int(gid_s) if gid_s.lstrip("-").isdigit() else None
        save(d)
        try:
            await q.edit_message_text(
                main_text(u, d, gid),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_kb(u, gid)
            )
        except Exception:
            pass
        return

    # Топ
    if a.startswith("lb_"):
        parts  = a.split("_", 2)
        gid_s  = parts[1]
        period = parts[2]
        gid    = int(gid_s) if gid_s.lstrip("-").isdigit() else None
        save(d)
        try:
            await q.edit_message_text(
                lb_text(d, gid, period),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=lb_kb(gid, period)
            )
        except Exception:
            pass
        return

    # Тап через кнопку
    if a == "tap":
        if not can_tap(u):
            await q.answer(
                f"⏳ Вже тапнув! Наступний о 00:00 Київ (через {time_to_reset()})",
                show_alert=True
            )
            save(d)
            return
        gt, gc, mult = do_tap(u)
        new = check_achievements(u)
        save(d)
        if   mult >= 6:   hdr = f"🎰 ДЖЕКПОТ ×{mult:.1f}!"
        elif mult >= 3:   hdr = f"🔥 Відмінно! ×{mult:.1f}"
        elif mult >= 1.5: hdr = f"✨ Гарний тап! ×{mult:.1f}"
        else:             hdr = f"👆 Тап ×{mult:.1f}"
        ach_txt = ("\n🎉 " + ", ".join(x[1] for x in new)) if new else ""
        try:
            await q.edit_message_text(
                f"*{hdr}*\n+{gt:,} тапів | +{gc:,} монет{ach_txt}\n\n{main_text(u, d, gid)}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_kb(u, gid)
            )
        except Exception:
            pass
        return

    # Магазин
    if a == "shop":
        save(d)
        try:
            await q.edit_message_text(
                shop_text(u),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=shop_kb(u, gid or 0)
            )
        except Exception:
            pass
        return

    # Купівля
    if a.startswith("buy_"):
        parts   = a.split("_", 2)
        upg_id  = parts[1]
        gid_buy = int(parts[2]) if len(parts) > 2 and parts[2].lstrip("-").isdigit() else 0
        upg = next((x for x in UPGRADES if x[0] == upg_id), None)
        if not upg:
            await q.answer("❌ Не знайдено!")
            return
        if upg_id in u.get("upg", []):
            await q.answer("✅ Вже куплено!")
            return
        if u.get("coins", 0) < upg[3]:
            await q.answer(f"❌ Потрібно {upg[3]:,}, є {u['coins']:,}")
            return
        u["coins"] -= upg[3]
        u.setdefault("upg", []).append(upg_id)
        check_achievements(u)
        save(d)
        await q.answer(f"✅ {upg[1]} куплено! Сила тапу: {calc_power(u)}")
        try:
            await q.edit_message_text(
                shop_text(u),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=shop_kb(u, gid_buy)
            )
        except Exception:
            pass
        return

    # Досягнення
    if a == "ach":
        txt = "🎖 *Досягнення*\n\n"
        for ac in ACHIEVEMENTS:
            earned = ac[0] in u.get("ach", [])
            req    = f"{ac[2]:,} тапів" if ac[2] else f"{ac[3]} днів стріку"
            txt   += f"{'✅' if earned else '🔒'} *{ac[1]}* — _{req}_\n"
        save(d)
        try:
            await q.edit_message_text(
                txt,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[btn("🔙 Назад", f"back_{gid or 0}")]])
            )
        except Exception:
            pass
        return

    save(d)

# ── ЗАПУСК ───────────────────────────────────────────────────────────
def main():
    app  = Application.builder().token(TOKEN).build()
    no_r = filters.TEXT & ~filters.REPLY

    app.add_handler(MessageHandler(filters.Regex(r"^\.профіль$") & no_r, on_profile))
    app.add_handler(MessageHandler(filters.Regex(r"^\.тап$")     & no_r, on_tap))
    app.add_handler(MessageHandler(filters.Regex(r"^\.топ$")     & no_r, on_top))
    app.add_handler(CallbackQueryHandler(on_btn))

    logging.warning("🦎 Лупиздрик запущено!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
