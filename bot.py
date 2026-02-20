import logging, json, os, random, asyncio
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(level=logging.WARNING)
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
DB    = "data.json"
KYIV  = ZoneInfo("Europe/Kiev")
DEV_USERNAME = "qelry"
DEV_ID       = None  # заповниться при першому /start від розробника

# ══ КОНСТАНТИ ════════════════════════════════════════════════════════
LEVELS = [
    (0,      1,   "🥚",  "Яєчко"),
    (100,    3,   "🐛",  "Гусінь"),
    (400,    6,   "🐌",  "Слизняк"),
    (1000,   12,  "🦎",  "Ящірка"),
    (2500,   22,  "🦊",  "Лисиця"),
    (6000,   38,  "🦄",  "Єдиноріг"),
    (15000,  60,  "🐉",  "Дракон"),
    (35000,  95,  "👾",  "Легенда"),
    (80000,  150, "✨",  "Бог Лупиздрик"),
    (200000, 250, "👑",  "Абсолют"),
]

SKINS = {
    "default":  ("🦎", "Звичайний"),
    "fire":     ("🔥", "Вогняний"),
    "ice":      ("❄️", "Крижаний"),
    "gold":     ("⭐", "Золотий"),
    "shadow":   ("🌑", "Тіньовий"),
    "rainbow":  ("🌈", "Райдужний"),
    "cosmic":   ("🌌", "Космічний"),
    "dragon":   ("🐲", "Дракон"),
    "devil":    ("😈", "Диявол"),
    "angel":    ("😇", "Ангел"),
    "cyber":    ("🤖", "Кіберпанк"),
    "ghost":    ("👻", "Привид"),
    "king":     ("👑", "Король"),
    "ninja":    ("🥷", "Ніндзя"),
    "alien":    ("👽", "Прибулець"),
    "unicorn":  ("🦄", "Єдиноріг"),
    "phoenix":  ("🦅", "Фенікс"),
    "vip":      ("💎", "VIP"),
}
SKIN_COST = {
    "fire": 1000, "ice": 1000, "gold": 2500, "shadow": 2500,
    "rainbow": 5000, "cosmic": 8000, "dragon": 10000,
    "devil": 15000, "angel": 15000, "cyber": 20000,
    "ghost": 5000, "king": 30000, "ninja": 12000,
    "alien": 8000, "unicorn": 18000, "phoenix": 25000,
    "vip": 50000,
}

UPGRADES = [
    ("paw",    "🐾 Золота лапа",          "+50% сили",   500,    1.5),
    ("drink",  "⚡ Енергетик",            "+100% сили",  2500,   2.0),
    ("rocket", "🚀 Ракетний прискорювач", "+200% сили",  10000,  3.0),
    ("cosmos", "🌌 Космічна сила",        "+500% сили",  40000,  6.0),
    ("quantum","🔮 Квантовий тап",        "+1000% сили", 150000, 11.0),
    ("time",   "⏰ Машина часу",          "+2000% сили", 500000, 21.0),
]

ACHIEVEMENTS = [
    ("t1",    "🎯 Перший тап!",          1,      0),
    ("t100",  "💯 Сотня!",               100,    0),
    ("t1k",   "🔥 Тисячник!",            1000,   0),
    ("t10k",  "💎 Десятитисячник!",      10000,  0),
    ("t50k",  "👑 П'ятдесятитисячник!",  50000,  0),
    ("t100k", "🌟 Стотисячник!",         100000, 0),
    ("t500k", "🚀 Пів мільйона!",        500000, 0),
    ("s7",    "📅 Тижень стріку!",       0,      7),
    ("s30",   "🗓 Місяць стріку!",       0,      30),
    ("s100",  "🔱 Сто днів стріку!",     0,      100),
    ("rich",  "💰 Мільйонер!",           0,      0),   # 1M монет — окрема перевірка
    ("skins", "🎨 Колекціонер!",         0,      0),   # 5 скінів
]

MEDALS = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

# ══ БД ═══════════════════════════════════════════════════════════════
def load():
    if os.path.exists(DB):
        d = json.load(open(DB, encoding="utf-8"))
        if "users" not in d:
            d = {"users": d, "groups": {}}
    else:
        d = {"users": {}, "groups": {}}
    d.setdefault("groups", {})
    d.setdefault("giveaways", [])
    return d

def save(d):
    json.dump(d, open(DB,"w",encoding="utf-8"), ensure_ascii=False)

def get_user(d, uid):
    u = d["users"].setdefault(str(uid), {})
    defaults = {
        "name":"Гравець","uname":None,"lang":None,
        "taps":0,"coins":0,"upg":[],"ach":[],
        "streak":0,"hist":{},"tap_date":None,"bonus_date":None,
        "skin":"default","owned_skins":["default"],
        "banned":False,"vip":False,
    }
    for k,v in defaults.items():
        u.setdefault(k,v)
    return u

def add_member(d, gid, uid):
    g = d["groups"].setdefault(str(gid), {"title":"","members":[]})
    g.setdefault("members",[])
    if str(uid) not in g["members"]:
        g["members"].append(str(uid))

def get_members(d, gid):
    return d["groups"].get(str(gid), {}).get("members", [])

def is_dev(tg_user):
    return tg_user.username and tg_user.username.lower() == DEV_USERNAME.lower()

# ══ ІГРОВА ЛОГІКА ════════════════════════════════════════════════════
def kyiv_today():
    return datetime.now(KYIV).date().isoformat()

def can_tap(u):
    return u.get("tap_date") != kyiv_today()

def time_to_reset():
    now  = datetime.now(KYIV)
    nxt  = datetime.combine(now.date()+timedelta(days=1), dtime(0,0), tzinfo=KYIV)
    diff = nxt - now
    h    = int(diff.total_seconds()//3600)
    m    = int((diff.total_seconds()%3600)//60)
    return f"{h}год {m}хв"

def get_level(taps):
    r = LEVELS[0]
    for L in LEVELS:
        if taps >= L[0]: r = L
        else: break
    return r

def get_next_level(taps):
    for L in LEVELS:
        if taps < L[0]: return L
    return None

def calc_power(u):
    p = get_level(u["taps"])[1]
    for uid in u.get("upg",[]):
        for upg in UPGRADES:
            if upg[0]==uid: p=int(p*upg[4])
    if u.get("vip"): p = int(p*1.5)
    return p

def do_tap(u):
    base = calc_power(u)
    r    = random.random()
    if   r < 0.50: mult = random.uniform(0.5,  1.5)
    elif r < 0.80: mult = random.uniform(1.5,  3.0)
    elif r < 0.95: mult = random.uniform(3.0,  6.0)
    else:          mult = random.uniform(6.0, 20.0)

    # Скін-бонус
    skin_bonus = {
        "fire":1.2,"gold":1.3,"rainbow":1.4,"cosmic":1.5,
        "dragon":1.6,"devil":1.5,"king":1.8,"phoenix":1.7,"vip":2.0
    }.get(u.get("skin","default"), 1.0)

    gt = max(1, int(base * mult * skin_bonus))
    gc = max(1, int(gt * random.uniform(0.3, 1.5)))

    u["taps"]  += gt
    u["coins"] += gc

    today = kyiv_today()
    yest  = (datetime.now(KYIV).date()-timedelta(days=1)).isoformat()
    if u.get("bonus_date")==yest:   u["streak"]=u.get("streak",0)+1
    elif u.get("bonus_date")!=today: u["streak"]=1
    u["tap_date"]   = today
    u["bonus_date"] = today

    h = u.setdefault("hist",{})
    h[today] = h.get(today,0)+gt
    cut = (datetime.now(KYIV).date()-timedelta(days=35)).isoformat()
    u["hist"] = {k:v for k,v in h.items() if k>cut}
    return gt, gc, mult, skin_bonus

def check_ach(u):
    new=[]
    for a in ACHIEVEMENTS:
        if a[0] in u.get("ach",[]): continue
        ok=False
        if a[2]>0 and u["taps"]>=a[2]: ok=True
        if a[3]>0 and u.get("streak",0)>=a[3]: ok=True
        if a[0]=="rich" and u.get("coins",0)>=1000000: ok=True
        if a[0]=="skins" and len(u.get("owned_skins",[]))>=5: ok=True
        if ok:
            u.setdefault("ach",[]).append(a[0])
            new.append(a)
    return new

def period_taps(u, period):
    if period=="all": return u.get("taps",0)
    days={"day":1,"week":7,"month":30}[period]
    cut=(datetime.now(KYIV).date()-timedelta(days=days)).isoformat()
    return sum(v for k,v in u.get("hist",{}).items() if k>cut)

# ══ UI / ТЕКСТ ════════════════════════════════════════════════════════
def btn(text, cb):
    return InlineKeyboardButton(text, callback_data=cb)

def get_skin_emoji(u):
    skin = u.get("skin","default")
    return SKINS.get(skin,("🦎",""))[0]

def progress_bar(u):
    L  = get_level(u["taps"])
    nL = get_next_level(u["taps"])
    if not nL: return "🌟 Максимальний рівень!"
    total = nL[0]-L[0]; done = u["taps"]-L[0]
    pct   = min(10, int(done/total*10)) if total else 10
    return f"`[{'█'*pct+'░'*(10-pct)}]` ще {nL[0]-u['taps']:,} → {nL[2]} {nL[3]}"

def main_text(u, d=None, gid=None):
    L    = get_level(u["taps"])
    p    = calc_power(u)
    ct   = can_tap(u)
    sk   = get_skin_emoji(u)
    skin_name = SKINS.get(u.get("skin","default"),("","Звичайний"))[1]
    vip_mark = " 💎" if u.get("vip") else ""
    upg_txt=""
    if u.get("upg"):
        upg_txt="\n🔧 "+" · ".join(ug[1] for ug in UPGRADES if ug[0] in u["upg"])
    tap_st="✅ Можеш тапнути!" if ct else f"⏳ О 00:00 (через {time_to_reset()})"
    rank_txt=""
    if d and gid:
        ms     = get_members(d,gid)
        md     = [d["users"][m] for m in ms if m in d["users"]]
        ranked = sorted(md, key=lambda x:x.get("taps",0), reverse=True)
        pos    = next((i+1 for i,x in enumerate(ranked) if x is u), "-")
        rank_txt=f"\n🏆 Місце: *#{pos}* з {len(ranked)}"
    return (
        f"╔══════════════════╗\n"
        f"  {sk} *ЛУПИЗДРИК* {sk}\n"
        f"╚══════════════════╝\n\n"
        f"{L[2]} *{L[3]}*{vip_mark}\n"
        f"{progress_bar(u)}\n\n"
        f"👆 Тапів: *{u['taps']:,}*{rank_txt}\n"
        f"💰 Монет: *{u['coins']:,}* | ⚡ Сила: *{p}*\n"
        f"🔥 Стрік: *{u.get('streak',0)} дн* | "
        f"🎖 Досяг: *{len(u.get('ach',[]))}/{len(ACHIEVEMENTS)}*\n"
        f"🎨 Скін: *{skin_name}* {sk}"
        f"{upg_txt}\n\n"
        f"{tap_st}"
    )

def main_kb(u, gid=None):
    L   = get_level(u["taps"])
    ct  = can_tap(u)
    lbl = f"{get_skin_emoji(u)} ТАП! {get_skin_emoji(u)}" if ct else "⏳ Вже тапнув сьогодні"
    return InlineKeyboardMarkup([
        [btn(lbl, "tap")],
        [btn("🏪 Магазин", "shop"), btn("🎨 Скіни", "skins_menu")],
        [btn("🎖 Досягнення", "ach"), btn("🏆 Топ", f"lb_{gid or 0}_all")],
    ])

def lb_text(d, gid, period):
    labels={"day":"📅 ДЕНЬ","week":"📆 ТИЖДЕНЬ","month":"🗓 МІСЯЦЬ","all":"🏅 УСЕ"}
    ms  = get_members(d,gid)
    hdr = f"🏆 *ТОП — {labels[period]}*\n\n"
    if not ms: return hdr+"_Поки нікого. Напиши_ `.тап`_!_"
    top = sorted([(m,d["users"][m]) for m in ms if m in d["users"]],
                 key=lambda x:period_taps(x[1],period), reverse=True)[:10]
    txt=hdr; shown=0
    for i,(uid,u) in enumerate(top):
        t=period_taps(u,period)
        if t==0: break
        sk  = get_skin_emoji(u)
        nm  = f"@{u['uname']}" if u.get("uname") else u.get("name","???")
        vip = " 💎" if u.get("vip") else ""
        txt+=f"{MEDALS[i]} *{nm}*{vip} {sk}\n   👆 {t:,} тапів | {get_level(u['taps'])[3]}\n\n"
        shown+=1
    if not shown: txt+="_Ніхто не тапав за цей період_"
    return txt

def lb_kb(gid, period):
    defs=[("📅 День","day"),("📆 Тиждень","week"),("🗓 Місяць","month"),("🏅 Все","all")]
    row=[btn(("▶ " if p==period else "")+l, f"lb_{gid}_{p}") for l,p in defs]
    return InlineKeyboardMarkup([row,[btn("🔙 Назад",f"back_{gid}")]])

def shop_text(u):
    txt=f"🏪 *Магазин покращень*\n💰 У тебе: *{u['coins']:,}* монет\n\n"
    owned=u.get("upg",[])
    has_any=False
    for upg in UPGRADES:
        if upg[0] in owned: continue
        has_any=True
        mark="✅" if u.get("coins",0)>=upg[3] else "❌"
        txt+=f"{upg[1]} {mark}\n  └ {upg[2]} · *{upg[3]:,}* 💰\n\n"
    if not has_any: txt+="🎉 _Усі покращення куплені!_"
    return txt

def shop_kb(u, gid):
    owned=u.get("upg",[])
    rows=[]
    for upg in UPGRADES:
        if upg[0] in owned:
            rows.append([btn(f"✅ {upg[1]}","noop")])
        else:
            rows.append([btn(f"{upg[1]} — {upg[3]:,}💰",f"buy_{upg[0]}_{gid}")])
    rows.append([btn("🔙 Назад",f"back_{gid}")])
    return InlineKeyboardMarkup(rows)

def skins_text(u):
    txt=f"🎨 *Магазин скінів*\n💰 У тебе: *{u['coins']:,}* монет\n\n"
    txt+="_Скін дає бонус до тапів та змінює вигляд бота_\n\n"
    return txt

def skins_kb(u, gid, page=0):
    owned=u.get("owned_skins",["default"])
    current=u.get("skin","default")
    skin_list=[s for s in SKINS if s!="default"]
    per_page=5
    start=page*per_page; end=start+per_page
    chunk=skin_list[start:end]
    rows=[]
    for s in chunk:
        em,name=SKINS[s]; cost=SKIN_COST.get(s,999)
        if s in owned:
            lbl=f"✅ {em} {name}" + (" ◀ активний" if s==current else "")
            rows.append([btn(lbl, f"skin_equip_{s}_{gid}")])
        else:
            rows.append([btn(f"{em} {name} — {cost:,}💰", f"skin_buy_{s}_{gid}")])
    nav=[]
    if page>0: nav.append(btn("◀",f"skins_page_{page-1}_{gid}"))
    if end<len(skin_list): nav.append(btn("▶",f"skins_page_{page+1}_{gid}"))
    if nav: rows.append(nav)
    rows.append([btn("🔙 Назад",f"back_{gid}")])
    return InlineKeyboardMarkup(rows)

# ══ DEV ПАНЕЛЬ ════════════════════════════════════════════════════════
def dev_menu_text():
    return (
        "⚙️ *ПАНЕЛЬ РОЗРОБНИКА*\n\n"
        "Обери дію:"
    )

def dev_menu_kb():
    return InlineKeyboardMarkup([
        [btn("📢 Розсилка","dev_broadcast")],
        [btn("👥 Юзери","dev_users"), btn("📊 Статистика","dev_stats")],
        [btn("🎁 Розіграш","dev_giveaway")],
        [btn("💰 Видати монети","dev_give_coins"), btn("👆 Видати тапи","dev_give_taps")],
        [btn("🎨 Видати скін","dev_give_skin")],
        [btn("💎 VIP","dev_vip"), btn("🔨 Бан","dev_ban")],
        [btn("🔄 Скинути юзера","dev_reset")],
        [btn("📋 Чати бота","dev_chats")],
    ])

def dev_users_text(d):
    users=d.get("users",{})
    txt=f"👥 *Юзери бота: {len(users)}*\n\n"
    for uid,u in list(users.items())[:20]:
        nm=u.get("name","?"); un=f"@{u['uname']}" if u.get("uname") else uid
        lang=u.get("lang","?") or "?"
        vip="💎" if u.get("vip") else ""
        ban="🔨" if u.get("banned") else ""
        txt+=f"`{uid}` {un} {vip}{ban}\n  └ {u.get('taps',0):,} тапів | {u.get('coins',0):,} монет | 🌐{lang}\n"
    if len(users)>20: txt+=f"\n_...і ще {len(users)-20} користувачів_"
    return txt

def dev_stats_text(d):
    users=d.get("users",{})
    groups=d.get("groups",{})
    total_taps=sum(u.get("taps",0) for u in users.values())
    total_coins=sum(u.get("coins",0) for u in users.values())
    active=sum(1 for u in users.values() if u.get("tap_date")==kyiv_today())
    return (
        f"📊 *Статистика бота*\n\n"
        f"👥 Юзерів: *{len(users)}*\n"
        f"💬 Груп: *{len(groups)}*\n"
        f"🔥 Активних сьогодні: *{active}*\n"
        f"👆 Тапів всього: *{total_taps:,}*\n"
        f"💰 Монет всього: *{total_coins:,}*\n"
    )

# ══ ХЕНДЛЕРИ ══════════════════════════════════════════════════════════
def setup(d, update):
    tg   = update.effective_user
    chat = update.effective_chat
    u    = get_user(d, tg.id)
    u["name"]  = tg.first_name or "Гравець"
    u["uname"] = tg.username
    u["lang"]  = tg.language_code
    gid = chat.id if chat.type in ("group","supergroup") else None
    if gid:
        d["groups"].setdefault(str(gid),{"title":"","members":[]})
        d["groups"][str(gid)]["title"]=chat.title or ""
        add_member(d,gid,tg.id)
    return u, gid

def is_direct(msg):
    return msg.reply_to_message is None

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    tg  = update.effective_user
    u, gid = setup(d, update)
    save(d)

    # Розробник — показуємо dev-меню в ЛС
    if is_dev(tg) and update.effective_chat.type == "private":
        await update.message.reply_text(
            f"👋 Привіт, *{tg.first_name}* — розробник!\n\n"
            f"🦎 *ЛУПИЗДРИК БОТ*\n\n"
            f"Обери розділ:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [btn("🦎 Грати","play_menu")],
                [btn("⚙️ Панель розробника","dev_menu")],
            ])
        )
        return

    if update.effective_chat.type == "private":
        await update.message.reply_text(
            f"👋 Привіт, *{tg.first_name}*!\n\n"
            f"🦎 *ЛУПИЗДРИК БОТ*\n\n"
            f"Тригери в групі:\n"
            f"`.профіль` — профіль і меню\n"
            f"`.тап` — тапнути\n"
            f"`.топ` — топ групи",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_kb(u, gid)
        )
    else:
        await update.message.reply_text(
            f"🦎 *ЛУПИЗДРИК БОТ*\n\n"
            f"Команди:\n`.профіль` `.тап` `.топ`",
            parse_mode=ParseMode.MARKDOWN
        )

async def on_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_direct(update.message): return
    d=load(); u,gid=setup(d,update); save(d)
    await update.message.reply_text(
        main_text(u,d,gid), parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb(u,gid)
    )

async def on_tap(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_direct(update.message): return
    d=load(); u,gid=setup(d,update)
    if u.get("banned"):
        save(d)
        await update.message.reply_text("🔨 Тебе заблоковано.")
        return
    if not can_tap(u):
        save(d)
        await update.message.reply_text(
            f"⏳ *Вже тапнув сьогодні!*\nНаступний о 00:00 по Києву (через {time_to_reset()})",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    gt,gc,mult,sb=do_tap(u); new=check_ach(u); save(d)
    if   mult>=6:   hdr=f"🎰 *ДЖЕКПОТ! ×{mult:.1f}!*"
    elif mult>=3:   hdr=f"🔥 *Відмінно! ×{mult:.1f}*"
    elif mult>=1.5: hdr=f"✨ *Гарний тап! ×{mult:.1f}*"
    else:           hdr=f"👆 *Тап ×{mult:.1f}*"
    skin_txt=f" (скін {get_skin_emoji(u)} ×{sb:.1f})" if sb>1 else ""
    ach_txt=("\n\n🎉 "+", ".join(a[1] for a in new)) if new else ""
    await update.message.reply_text(
        f"{hdr}{skin_txt}\n👆 +*{gt:,}* тапів | 💰 +*{gc:,}* монет{ach_txt}\n\n{main_text(u,d,gid)}",
        parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb(u,gid)
    )

async def on_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_direct(update.message): return
    d=load(); u,gid=setup(d,update); save(d)
    if not gid:
        await update.message.reply_text("❌ Тільки для груп!"); return
    await update.message.reply_text(
        lb_text(d,gid,"all"), parse_mode=ParseMode.MARKDOWN,
        reply_markup=lb_kb(gid,"all")
    )

async def on_btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()
    d    = load()
    tg   = q.from_user
    u    = get_user(d,tg.id)
    u["name"]=tg.first_name or "Гравець"
    u["uname"]=tg.username
    u["lang"]=tg.language_code
    a    = q.data
    chat = q.message.chat
    gid  = chat.id if chat.type in ("group","supergroup") else None
    if gid: add_member(d,gid,tg.id)
    cid  = chat.id
    mid  = q.message.message_id

    async def edit(txt, kb):
        try: await q.edit_message_text(txt,parse_mode=ParseMode.MARKDOWN,reply_markup=kb)
        except: pass

    # ── noop
    if a=="noop": return

    # ── play_menu (для розробника в лс)
    if a=="play_menu":
        save(d)
        await edit(main_text(u,d,gid), main_kb(u,gid)); return

    # ── назад
    if a.startswith("back_"):
        gid_s=a[5:]; gid=int(gid_s) if gid_s.lstrip("-").isdigit() else None
        save(d)
        await edit(main_text(u,d,gid), main_kb(u,gid)); return

    # ── топ
    if a.startswith("lb_"):
        parts=a.split("_",2); gid_s=parts[1]; period=parts[2]
        gid=int(gid_s) if gid_s.lstrip("-").isdigit() else None
        save(d)
        await edit(lb_text(d,gid,period), lb_kb(gid,period)); return

    # ── тап
    if a=="tap":
        if u.get("banned"):
            await q.answer("🔨 Тебе заблоковано.", show_alert=True); return
        if not can_tap(u):
            await q.answer(f"⏳ Наступний о 00:00 (через {time_to_reset()})", show_alert=True)
            save(d); return
        gt,gc,mult,sb=do_tap(u); new=check_ach(u); save(d)
        if   mult>=6:   hdr=f"🎰 ДЖЕКПОТ ×{mult:.1f}!"
        elif mult>=3:   hdr=f"🔥 Відмінно! ×{mult:.1f}"
        elif mult>=1.5: hdr=f"✨ Гарний тап! ×{mult:.1f}"
        else:           hdr=f"👆 Тап ×{mult:.1f}"
        ach_txt=("\n🎉 "+", ".join(x[1] for x in new)) if new else ""
        await edit(
            f"*{hdr}*\n+{gt:,} тапів | +{gc:,} монет{ach_txt}\n\n{main_text(u,d,gid)}",
            main_kb(u,gid)
        ); return

    # ── магазин
    if a=="shop":
        save(d); await edit(shop_text(u), shop_kb(u,gid or 0)); return

    # ── купівля апгрейду
    if a.startswith("buy_"):
        parts=a.split("_",2); upg_id=parts[1]
        gid_buy=int(parts[2]) if len(parts)>2 and parts[2].lstrip("-").isdigit() else 0
        upg=next((x for x in UPGRADES if x[0]==upg_id),None)
        if not upg: await q.answer("❌ Не знайдено!"); return
        if upg_id in u.get("upg",[]): await q.answer("✅ Вже куплено!"); return
        if u.get("coins",0)<upg[3]:
            await q.answer(f"❌ Потрібно {upg[3]:,}, є {u['coins']:,}"); return
        u["coins"]-=upg[3]; u.setdefault("upg",[]).append(upg_id)
        check_ach(u); save(d)
        await q.answer(f"✅ {upg[1]} куплено! Сила: {calc_power(u)}")
        await edit(shop_text(u), shop_kb(u,gid_buy)); return

    # ── скіни меню
    if a=="skins_menu":
        save(d)
        await edit(skins_text(u), skins_kb(u,gid or 0)); return

    if a.startswith("skins_page_"):
        parts=a.split("_"); page=int(parts[2]); gid_s=parts[3]
        gid_s2=int(gid_s) if gid_s.lstrip("-").isdigit() else 0
        await edit(skins_text(u), skins_kb(u,gid_s2,page)); return

    if a.startswith("skin_buy_"):
        parts=a.split("_",3); skin_id=parts[2]
        gid_s=int(parts[3]) if parts[3].lstrip("-").isdigit() else 0
        if skin_id not in SKINS: await q.answer("❌"); return
        if skin_id in u.get("owned_skins",[]): await q.answer("✅ Вже є!"); return
        cost=SKIN_COST.get(skin_id,0)
        if u.get("coins",0)<cost:
            await q.answer(f"❌ Потрібно {cost:,}, є {u['coins']:,}"); return
        u["coins"]-=cost; u.setdefault("owned_skins",["default"]).append(skin_id)
        u["skin"]=skin_id; check_ach(u); save(d)
        await q.answer(f"✅ {SKINS[skin_id][0]} {SKINS[skin_id][1]} куплено і одягнено!")
        await edit(skins_text(u), skins_kb(u,gid_s)); return

    if a.startswith("skin_equip_"):
        parts=a.split("_",3); skin_id=parts[2]
        gid_s=int(parts[3]) if parts[3].lstrip("-").isdigit() else 0
        if skin_id not in u.get("owned_skins",[]): await q.answer("❌ Не куплено"); return
        u["skin"]=skin_id; save(d)
        await q.answer(f"✅ {SKINS[skin_id][0]} {SKINS[skin_id][1]} одягнено!")
        await edit(skins_text(u), skins_kb(u,gid_s)); return

    # ── досягнення
    if a=="ach":
        txt="🎖 *Досягнення*\n\n"
        for ac in ACHIEVEMENTS:
            earned=ac[0] in u.get("ach",[])
            if ac[2]>0: req=f"{ac[2]:,} тапів"
            elif ac[3]>0: req=f"{ac[3]} дн стріку"
            elif ac[0]=="rich": req="1,000,000 монет"
            elif ac[0]=="skins": req="5 скінів"
            else: req=""
            txt+=f"{'✅' if earned else '🔒'} *{ac[1]}*"
            if req: txt+=f" — _{req}_"
            txt+="\n"
        save(d)
        await edit(txt, InlineKeyboardMarkup([[btn("🔙 Назад",f"back_{gid or 0}")]])); return

    # ══ DEV ПАНЕЛЬ ════════════════════════════════════════════════════
    if not is_dev(tg):
        return

    if a=="dev_menu":
        await edit(dev_menu_text(), dev_menu_kb()); return

    if a=="dev_users":
        await edit(dev_users_text(d), InlineKeyboardMarkup([[btn("🔙 Назад","dev_menu")]])); return

    if a=="dev_stats":
        await edit(dev_stats_text(d), InlineKeyboardMarkup([[btn("🔙 Назад","dev_menu")]])); return

    if a=="dev_chats":
        groups=d.get("groups",{})
        txt=f"💬 *Чати бота: {len(groups)}*\n\n"
        for gid_s,g in list(groups.items())[:20]:
            txt+=f"`{gid_s}` *{g.get('title','?')}*\n  └ {len(g.get('members',[]))} учасників\n"
        await edit(txt, InlineKeyboardMarkup([[btn("🔙 Назад","dev_menu")]])); return

    if a=="dev_broadcast":
        ctx.user_data["dev_action"]="broadcast"
        await edit(
            "📢 *Розсилка*\n\nВідправ мені текст повідомлення:",
            InlineKeyboardMarkup([[btn("❌ Скасувати","dev_menu")]])
        ); return

    if a=="dev_give_coins":
        ctx.user_data["dev_action"]="give_coins"
        await edit(
            "💰 *Видати монети*\n\nФормат: `@username 1000` або `user_id 1000`",
            InlineKeyboardMarkup([[btn("❌ Скасувати","dev_menu")]])
        ); return

    if a=="dev_give_taps":
        ctx.user_data["dev_action"]="give_taps"
        await edit(
            "👆 *Видати тапи*\n\nФормат: `@username 1000` або `user_id 1000`",
            InlineKeyboardMarkup([[btn("❌ Скасувати","dev_menu")]])
        ); return

    if a=="dev_give_skin":
        ctx.user_data["dev_action"]="give_skin"
        skins_str=", ".join(f"`{s}`" for s in SKINS if s!="default")
        await edit(
            f"🎨 *Видати скін*\n\nДоступні: {skins_str}\n\nФормат: `@username fire`",
            InlineKeyboardMarkup([[btn("❌ Скасувати","dev_menu")]])
        ); return

    if a=="dev_vip":
        ctx.user_data["dev_action"]="toggle_vip"
        await edit(
            "💎 *VIP статус*\n\nФормат: `@username` або `user_id`",
            InlineKeyboardMarkup([[btn("❌ Скасувати","dev_menu")]])
        ); return

    if a=="dev_ban":
        ctx.user_data["dev_action"]="toggle_ban"
        await edit(
            "🔨 *Бан/Розбан*\n\nФормат: `@username` або `user_id`",
            InlineKeyboardMarkup([[btn("❌ Скасувати","dev_menu")]])
        ); return

    if a=="dev_reset":
        ctx.user_data["dev_action"]="reset_user"
        await edit(
            "🔄 *Скинути юзера*\n\nФормат: `@username all` або `@username coins` або `@username taps`",
            InlineKeyboardMarkup([[btn("❌ Скасувати","dev_menu")]])
        ); return

    if a=="dev_giveaway":
        ctx.user_data["dev_action"]="giveaway"
        await edit(
            "🎁 *Розіграш*\n\nФормат:\n"
            "`coins 10000` — монети переможцю\n"
            "`taps 5000` — тапи переможцю\n"
            "`skin dragon` — скін переможцю\n"
            "`vip` — VIP статус\n\n"
            "Бот запустить розіграш у всіх групах!",
            InlineKeyboardMarkup([[btn("❌ Скасувати","dev_menu")]])
        ); return

    if a.startswith("giveaway_join_"):
        ga_id=a[14:]
        d2=load()
        ga=next((g for g in d2.get("giveaways",[]) if g["id"]==ga_id),None)
        if not ga:
            await q.answer("❌ Розіграш не знайдено"); return
        if ga.get("ended"):
            await q.answer("❌ Розіграш вже завершено"); return
        if str(tg.id) in ga.get("participants",[]):
            await q.answer("✅ Ти вже в розіграші!"); return
        ga.setdefault("participants",[]).append(str(tg.id))
        gu=get_user(d2,tg.id); gu["name"]=tg.first_name or "?"; gu["uname"]=tg.username
        save(d2)
        await q.answer(f"✅ Ти в розіграші! Учасників: {len(ga['participants'])}")
        try:
            await q.edit_message_reply_markup(
                InlineKeyboardMarkup([[btn(f"🎉 Взяти участь ({len(ga['participants'])})",f"giveaway_join_{ga_id}")]])
            )
        except: pass
        return

    save(d)

# ── DEV: текстові команди від розробника ─────────────────────────────
async def dev_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg=update.effective_user
    if not is_dev(tg) or update.effective_chat.type!="private": return
    action=ctx.user_data.get("dev_action")
    if not action: return
    text=update.message.text.strip()
    d=load()

    def find_user_by_ref(ref):
        """Знайти uid по @username або id"""
        ref=ref.lstrip("@")
        for uid,u in d["users"].items():
            if u.get("uname","").lower()==ref.lower() or uid==ref:
                return uid,u
        return None,None

    if action=="broadcast":
        ctx.user_data.pop("dev_action",None)
        groups=d.get("groups",{})
        sent=0
        for gid_s in groups:
            try:
                await ctx.bot.send_message(int(gid_s), f"📢 *Повідомлення від адміна:*\n\n{text}", parse_mode=ParseMode.MARKDOWN)
                sent+=1
            except: pass
        await update.message.reply_text(f"✅ Розсилка відправлена в {sent} чатів")
        return

    if action=="give_coins":
        ctx.user_data.pop("dev_action",None)
        parts=text.split(); ref=parts[0]; amt=int(parts[1]) if len(parts)>1 else 0
        uid,u=find_user_by_ref(ref)
        if not u: await update.message.reply_text("❌ Юзер не знайдений"); return
        u["coins"]=u.get("coins",0)+amt; save(d)
        await update.message.reply_text(f"✅ +{amt:,} монет для {ref}")
        return

    if action=="give_taps":
        ctx.user_data.pop("dev_action",None)
        parts=text.split(); ref=parts[0]; amt=int(parts[1]) if len(parts)>1 else 0
        uid,u=find_user_by_ref(ref)
        if not u: await update.message.reply_text("❌ Юзер не знайдений"); return
        u["taps"]=u.get("taps",0)+amt; save(d)
        await update.message.reply_text(f"✅ +{amt:,} тапів для {ref}")
        return

    if action=="give_skin":
        ctx.user_data.pop("dev_action",None)
        parts=text.split(); ref=parts[0]; skin_id=parts[1] if len(parts)>1 else ""
        uid,u=find_user_by_ref(ref)
        if not u: await update.message.reply_text("❌ Юзер не знайдений"); return
        if skin_id not in SKINS: await update.message.reply_text("❌ Скін не знайдений"); return
        u.setdefault("owned_skins",["default"])
        if skin_id not in u["owned_skins"]: u["owned_skins"].append(skin_id)
        save(d)
        await update.message.reply_text(f"✅ Скін {SKINS[skin_id][0]} {SKINS[skin_id][1]} видано {ref}")
        return

    if action=="toggle_vip":
        ctx.user_data.pop("dev_action",None)
        uid,u=find_user_by_ref(text.strip())
        if not u: await update.message.reply_text("❌ Юзер не знайдений"); return
        u["vip"]=not u.get("vip",False); save(d)
        status="видано 💎" if u["vip"] else "знято"
        await update.message.reply_text(f"✅ VIP {status} для {text.strip()}")
        return

    if action=="toggle_ban":
        ctx.user_data.pop("dev_action",None)
        uid,u=find_user_by_ref(text.strip())
        if not u: await update.message.reply_text("❌ Юзер не знайдений"); return
        u["banned"]=not u.get("banned",False); save(d)
        status="заблоковано 🔨" if u["banned"] else "розблоковано ✅"
        await update.message.reply_text(f"{text.strip()} {status}")
        return

    if action=="reset_user":
        ctx.user_data.pop("dev_action",None)
        parts=text.split(); ref=parts[0]; what=parts[1] if len(parts)>1 else "all"
        uid,u=find_user_by_ref(ref)
        if not u: await update.message.reply_text("❌ Юзер не знайдений"); return
        if what=="all":
            u.update({"taps":0,"coins":0,"upg":[],"ach":[],"streak":0,
                      "hist":{},"tap_date":None,"bonus_date":None,
                      "skin":"default","owned_skins":["default"],"vip":False})
        elif what=="coins": u["coins"]=0
        elif what=="taps":  u["taps"]=0; u["hist"]={}
        elif what=="streak": u["streak"]=0
        save(d)
        await update.message.reply_text(f"✅ {ref}: скинуто [{what}]")
        return

    if action=="giveaway":
        ctx.user_data.pop("dev_action",None)
        parts=text.strip().split()
        prize_type=parts[0] if parts else ""
        prize_val=parts[1] if len(parts)>1 else ""
        ga_id=f"ga_{int(datetime.now().timestamp())}"
        ga={"id":ga_id,"type":prize_type,"value":prize_val,"participants":[],"ended":False}
        d.setdefault("giveaways",[]).append(ga)

        prize_txt={
            "coins":f"💰 {int(prize_val):,} монет",
            "taps":f"👆 {int(prize_val):,} тапів",
            "skin":f"🎨 Скін {SKINS.get(prize_val,('?','?'))[0]} {SKINS.get(prize_val,('?','?'))[1]}",
            "vip":"💎 VIP статус",
        }.get(prize_type,"🎁 Приз")

        ga_text=(
            f"🎁 *РОЗІГРАШ!*\n\n"
            f"Приз: *{prize_txt}*\n\n"
            f"Натисни кнопку щоб взяти участь!\n"
            f"Переможець буде обраний через 60 секунд."
        )
        ga_kb=InlineKeyboardMarkup([[btn(f"🎉 Взяти участь (0)",f"giveaway_join_{ga_id}")]])

        groups=d.get("groups",{}); save(d)
        sent_msgs=[]
        for gid_s in groups:
            try:
                msg=await ctx.bot.send_message(int(gid_s), ga_text,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=ga_kb)
                sent_msgs.append((int(gid_s),msg.message_id))
            except: pass

        await update.message.reply_text(f"✅ Розіграш запущено в {len(sent_msgs)} чатах!\nЧерез 60 сек буде обраний переможець.")

        # Завершення через 60 сек
        async def end_giveaway():
            await asyncio.sleep(60)
            d2=load()
            ga2=next((g for g in d2.get("giveaways",[]) if g["id"]==ga_id),None)
            if not ga2 or ga2.get("ended"): return
            ga2["ended"]=True
            parts2=ga2.get("participants",[])
            if not parts2:
                result_txt="🎁 *Розіграш завершено*\n\n_Ніхто не взяв участь_ 😔"
            else:
                winner_id=random.choice(parts2)
                wu=get_user(d2,winner_id)
                wname=f"@{wu['uname']}" if wu.get("uname") else wu.get("name","?")
                # Видати приз
                if ga2["type"]=="coins":
                    wu["coins"]=wu.get("coins",0)+int(ga2["value"])
                elif ga2["type"]=="taps":
                    wu["taps"]=wu.get("taps",0)+int(ga2["value"])
                elif ga2["type"]=="skin":
                    s=ga2["value"]
                    wu.setdefault("owned_skins",["default"])
                    if s not in wu["owned_skins"]: wu["owned_skins"].append(s)
                elif ga2["type"]=="vip":
                    wu["vip"]=True
                result_txt=(
                    f"🎁 *Розіграш завершено!*\n\n"
                    f"🏆 Переможець: *{wname}*\n"
                    f"🎉 Отримує: *{prize_txt}*\n\n"
                    f"Учасників було: {len(parts2)}"
                )
            save(d2)
            for gid_s2,msg_id in sent_msgs:
                try:
                    await ctx.bot.edit_message_text(
                        result_txt, chat_id=gid_s2, message_id=msg_id,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except: pass

        asyncio.create_task(end_giveaway())
        return

# ══ ЗАПУСК ════════════════════════════════════════════════════════════
def main():
    app  = Application.builder().token(TOKEN).build()
    no_r = filters.TEXT & ~filters.REPLY

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.Regex(r"^\.профіль$") & no_r, on_profile))
    app.add_handler(MessageHandler(filters.Regex(r"^\.тап$")     & no_r, on_tap))
    app.add_handler(MessageHandler(filters.Regex(r"^\.топ$")     & no_r, on_top))
    # Dev text handler — тільки ЛС
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, dev_text
    ))
    app.add_handler(CallbackQueryHandler(on_btn))

    logging.warning("🦎 Лупиздрик запущено!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
