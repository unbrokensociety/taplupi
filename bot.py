import logging,json,os,random,asyncio
from datetime import datetime,timedelta,time as dtime
from zoneinfo import ZoneInfo
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import Application,CallbackQueryHandler,MessageHandler,CommandHandler,filters,ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(level=logging.WARNING)
TOKEN=os.environ.get("BOT_TOKEN","YOUR_TOKEN_HERE")
DB="data.json"
KYIV=ZoneInfo("Europe/Kiev")
DEV_ID=1550849366
DEV_UN="qelry"

LEVELS=[(0,1,"🥚","Яєчко"),(100,3,"🐛","Гусінь"),(400,6,"🐌","Слизняк"),(1000,12,"🦎","Ящірка"),(2500,22,"🦊","Лисиця"),(6000,38,"🦄","Єдиноріг"),(15000,60,"🐉","Дракон"),(35000,95,"👾","Легенда"),(80000,150,"✨","Бог"),(200000,250,"👑","Абсолют")]
SKINS={"default":("🦎","Звичайний",0,1.0),"fire":("🔥","Вогняний",1000,1.2),"ice":("❄️","Крижаний",1000,1.15),"gold":("⭐","Золотий",2500,1.3),"shadow":("🌑","Тіньовий",2500,1.25),"rainbow":("🌈","Райдужний",5000,1.4),"cosmic":("🌌","Космічний",8000,1.5),"dragon":("🐲","Дракон",10000,1.6),"devil":("😈","Диявол",15000,1.5),"angel":("😇","Ангел",15000,1.55),"cyber":("🤖","Кіберпанк",20000,1.6),"ghost":("👻","Привид",5000,1.2),"king":("👑","Король",30000,1.8),"ninja":("🥷","Ніндзя",12000,1.45),"alien":("👽","Прибулець",8000,1.35),"unicorn":("🦄","Єдиноріг",18000,1.65),"phoenix":("🦅","Фенікс",25000,1.7),"vip_skin":("💎","VIP Скін",50000,2.0)}
UPGRADES=[("paw","🐾 Золота лапа","+50%",500,1.5),("drink","⚡ Енергетик","+100%",2500,2.0),("rocket","🚀 Ракета","+200%",10000,3.0),("cosmos","🌌 Космос","+500%",40000,6.0),("quantum","🔮 Квантум","+1000%",150000,11.0),("time","⏰ Машина часу","+2000%",500000,21.0)]
ACHIEVEMENTS=[("t1","🎯 Перший тап!",1,0),("t100","💯 Сотня!",100,0),("t1k","🔥 Тисячник!",1000,0),("t10k","💎 10к!",10000,0),("t50k","👑 50к!",50000,0),("t100k","🌟 100к!",100000,0),("t500k","🚀 500к!",500000,0),("s7","📅 Тижень!",0,7),("s30","🗓 Місяць!",0,30),("s100","🔱 100 днів!",0,100),("rich","💰 Мільйонер!",0,0),("skins5","🎨 Колекціонер!",0,0)]
MEDALS=["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

def load():
    if os.path.exists(DB):
        d=json.load(open(DB,encoding="utf-8"))
        if "users" not in d:d={"users":d,"groups":{}}
    else:d={"users":{},"groups":{}}
    for k,v in [("groups",{}),("giveaways",[]),("x2_until",None)]:d.setdefault(k,v)
    return d

def save(d):json.dump(d,open(DB,"w",encoding="utf-8"),ensure_ascii=False)

def gu(d,uid):
    u=d["users"].setdefault(str(uid),{})
    for k,v in [("name","Гравець"),("uname",None),("lang",None),("taps",0),("coins",0),("upg",[]),("ach",[]),("streak",0),("hist",{}),("tap_date",None),("bonus_date",None),("skin","default"),("owned_skins",["default"]),("banned",False),("vip",False)]:
        u.setdefault(k,v)
    return u

def add_mb(d,gid,uid):
    g=d["groups"].setdefault(str(gid),{"title":"","members":[]})
    g.setdefault("members",[])
    if str(uid) not in g["members"]:g["members"].append(str(uid))

def get_mb(d,gid):return d["groups"].get(str(gid),{}).get("members",[])
def is_dev(tg):return tg.id==DEV_ID or (tg.username and tg.username.lower()==DEV_UN.lower())
def today_k():return datetime.now(KYIV).date().isoformat()
def can_tap(u):return u.get("tap_date")!=today_k()

def reset_t():
    nw=datetime.now(KYIV);nx=datetime.combine(nw.date()+timedelta(days=1),dtime(0,0),tzinfo=KYIV)
    d=nx-nw;h=int(d.total_seconds()//3600);m=int((d.total_seconds()%3600)//60)
    return f"{h}г {m}хв"

def get_lvl(t):
    r=LEVELS[0]
    for L in LEVELS:
        if t>=L[0]:r=L
        else:break
    return r

def get_nlvl(t):
    for L in LEVELS:
        if t<L[0]:return L
    return None

def is_x2(d):
    xu=d.get("x2_until")
    if not xu:return False
    try:return datetime.fromisoformat(xu)>datetime.now(KYIV)
    except:return False

def calc_pow(u,x2=False):
    p=get_lvl(u["taps"])[1]
    for uid in u.get("upg",[]):
        for upg in UPGRADES:
            if upg[0]==uid:p=int(p*upg[4])
    if u.get("vip"):p=int(p*1.5)
    if x2:p*=2
    return p

def do_tap(u,x2=False):
    base=calc_pow(u,x2);r=random.random()
    if r<.50:mult=random.uniform(0.5,1.5)
    elif r<.80:mult=random.uniform(1.5,3.0)
    elif r<.95:mult=random.uniform(3.0,6.0)
    else:mult=random.uniform(6.0,20.0)
    sb=SKINS.get(u.get("skin","default"),("","",0,1.0))[3]
    gt=max(1,int(base*mult*sb));gc=max(1,int(gt*random.uniform(0.3,1.5)))
    u["taps"]+=gt;u["coins"]+=gc
    td=today_k();yest=(datetime.now(KYIV).date()-timedelta(days=1)).isoformat()
    if u.get("bonus_date")==yest:u["streak"]=u.get("streak",0)+1
    elif u.get("bonus_date")!=td:u["streak"]=1
    u["tap_date"]=td;u["bonus_date"]=td
    h=u.setdefault("hist",{});h[td]=h.get(td,0)+gt
    cut=(datetime.now(KYIV).date()-timedelta(days=35)).isoformat()
    u["hist"]={k:v for k,v in h.items() if k>cut}
    return gt,gc,mult,sb

def check_ach(u):
    new=[]
    for a in ACHIEVEMENTS:
        if a[0] in u.get("ach",[]):continue
        ok=(a[2]>0 and u["taps"]>=a[2]) or (a[3]>0 and u.get("streak",0)>=a[3]) or (a[0]=="rich" and u.get("coins",0)>=1000000) or (a[0]=="skins5" and len(u.get("owned_skins",[]))>=5)
        if ok:u.setdefault("ach",[]).append(a[0]);new.append(a)
    return new

def ptaps(u,period):
    if period=="all":return u.get("taps",0)
    days={"day":1,"week":7,"month":30}[period]
    cut=(datetime.now(KYIV).date()-timedelta(days=days)).isoformat()
    return sum(v for k,v in u.get("hist",{}).items() if k>cut)

def sk(u):return SKINS.get(u.get("skin","default"),("🦎",))[0]
def btn(t,c):return InlineKeyboardButton(t,callback_data=c)

def pbar(u):
    L=get_lvl(u["taps"]);nL=get_nlvl(u["taps"])
    if not nL:return "✨ Максимум!"
    total=nL[0]-L[0];done=u["taps"]-L[0]
    pct=min(10,int(done/total*10)) if total else 10
    return f"[{'█'*pct+'░'*(10-pct)}] ще {nL[0]-u['taps']:,}"

def main_text(u,d=None,gid=None):
    L=get_lvl(u["taps"]);p=calc_pow(u,is_x2(d) if d else False);s=sk(u)
    sn=SKINS.get(u.get("skin","default"),("","Звичайний"))[1]
    vip=" 💎" if u.get("vip") else ""
    x2t=" ⚡×2" if d and is_x2(d) else ""
    upgs="\n🔧 "+" · ".join(ug[1] for ug in UPGRADES if ug[0] in u.get("upg",[])) if u.get("upg") else ""
    tap_st="✅ Готовий!" if can_tap(u) else f"⏳ Скид о 00:00 ({reset_t()})"
    rank=""
    if d and gid:
        ms=get_mb(d,gid);md=[d["users"][m] for m in ms if m in d["users"]]
        ranked=sorted(md,key=lambda x:x.get("taps",0),reverse=True)
        pos=next((i+1 for i,x in enumerate(ranked) if x is u),"-")
        rank=f" · 🏆#{pos}/{len(ranked)}"
    return (f"{'═'*21}\n"
            f"  {s} *ЛУПИЗДРИК*{vip}{x2t}\n"
            f"  {L[2]} *{L[3]}*\n"
            f"  {pbar(u)} → {get_nlvl(u['taps'])[2] if get_nlvl(u['taps']) else '🏁'}\n"
            f"{'─'*21}\n"
            f"  👆 *{u['taps']:,}* тапів{rank}\n"
            f"  💰 *{u['coins']:,}* монет\n"
            f"  ⚡ Сила *{p}* · 🎨 {sn}"
            f"{upgs}\n"
            f"  🔥 Стрік *{u.get('streak',0)}д* · 🎖 *{len(u.get('ach',[]))}/{len(ACHIEVEMENTS)}*\n"
            f"{'─'*21}\n"
            f"  {tap_st}")

def main_kb(u,gid=None):
    ct=can_tap(u);s=sk(u)
    lbl=f"{s} ТАП! {s}" if ct else "⏳ Вже тапнув сьогодні"
    return InlineKeyboardMarkup([
        [btn(lbl,"tap")],
        [btn("🏪 Магазин","shop"),btn("🎨 Скіни","skins_0_0")],
        [btn("🎖 Досягнення","ach"),btn("🏆 Топ",f"lb_{gid or 0}_all")],
    ])

def lb_text(d,gid,period):
    pn={"day":"📅 День","week":"📆 Тиждень","month":"🗓 Місяць","all":"🏅 Весь час"}
    ms=get_mb(d,gid)
    if not ms:return f"🏆 *Топ · {pn[period]}*\n\n_Поки нікого!_"
    top=sorted([(m,d["users"][m]) for m in ms if m in d["users"]],key=lambda x:ptaps(x[1],period),reverse=True)[:10]
    txt=f"🏆 *Топ · {pn[period]}*\n{'─'*20}\n";shown=0
    for i,(uid,u) in enumerate(top):
        t=ptaps(u,period)
        if t==0:break
        nm=f"@{u['uname']}" if u.get("uname") else u.get("name","?")
        vip="💎" if u.get("vip") else ""
        txt+=f"{MEDALS[i]} *{nm}* {vip}{sk(u)}\n  👆 {t:,} · {get_lvl(u['taps'])[3]}\n";shown+=1
    if not shown:txt+="_Ніхто не тапав_"
    return txt

def lb_kb(gid,period):
    defs=[("📅","day"),("📆","week"),("🗓","month"),("🏅","all")]
    row=[btn(("▶" if p==period else "")+l,f"lb_{gid}_{p}") for l,p in defs]
    return InlineKeyboardMarkup([row,[btn("↩️ Назад",f"back_{gid}")]])

def shop_text(u):
    txt=f"🏪 *Магазин покращень*\n💰 *{u['coins']:,}* монет\n{'─'*20}\n"
    owned=u.get("upg",[]);has=False
    for upg in UPGRADES:
        if upg[0] in owned:continue
        has=True;af="✅" if u.get("coins",0)>=upg[3] else "❌"
        txt+=f"{upg[1]} {af}\n  {upg[2]} · *{upg[3]:,}* 💰\n\n"
    if not has:txt+="🎉 Все куплено!"
    return txt

def shop_kb(u,gid):
    rows=[[btn(f"✅ {upg[1]}","noop")] if upg[0] in u.get("upg",[]) else [btn(f"{upg[1]} — {upg[3]:,}💰",f"buy_{upg[0]}_{gid}")] for upg in UPGRADES]
    rows.append([btn("↩️ Назад",f"back_{gid}")])
    return InlineKeyboardMarkup(rows)

def skins_text(u):
    return f"🎨 *Скіни*\n💰 *{u['coins']:,}* монет\n{'─'*20}\n_Скін дає бонус до тапів_"

def skins_kb(u,gid,page=0):
    owned=u.get("owned_skins",["default"]);cur=u.get("skin","default")
    sl=[s for s in SKINS if s!="default"];per=6;chunk=sl[page*per:(page+1)*per]
    rows=[]
    for s in chunk:
        em,nm,cost,mul=SKINS[s]
        if s in owned:
            lbl=f"{'▶' if s==cur else '✓'} {em} {nm} ×{mul}"
            rows.append([btn(lbl,f"seq_{s}_{gid}")])
        else:
            rows.append([btn(f"{em} {nm} ×{mul} — {cost:,}💰",f"sbuy_{s}_{gid}")])
    nav=[]
    if page>0:nav.append(btn("◀ Назад",f"skins_{page-1}_{gid}"))
    if (page+1)*per<len(sl):nav.append(btn("Далі ▶",f"skins_{page+1}_{gid}"))
    if nav:rows.append(nav)
    rows.append([btn("↩️ Назад",f"back_{gid}")])
    return InlineKeyboardMarkup(rows)

def setup(d,update):
    tg=update.effective_user;chat=update.effective_chat
    u=gu(d,tg.id);u["name"]=tg.first_name or "Гравець";u["uname"]=tg.username;u["lang"]=tg.language_code
    gid=chat.id if chat.type in("group","supergroup") else None
    if gid:
        d["groups"].setdefault(str(gid),{"title":"","members":[]})
        d["groups"][str(gid)]["title"]=chat.title or ""
        add_mb(d,gid,tg.id)
    return u,gid

def no_rep(msg):return msg.reply_to_message is None

async def cmd_start(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    d=load();tg=update.effective_user;u,gid=setup(d,update);save(d)
    if is_dev(tg) and update.effective_chat.type=="private":
        await update.message.reply_text(
            f"{'═'*21}\n  ⚙️ *ПАНЕЛЬ РОЗРОБНИКА*\n{'═'*21}\n\nПривіт, *{tg.first_name}*! 👋\nID: `{tg.id}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[btn("🦎 Грати","play")],[btn("⚙️ Панель розробника","dev")]]))
        return
    if update.effective_chat.type=="private":
        await update.message.reply_text(main_text(u,d,gid),parse_mode=ParseMode.MARKDOWN,reply_markup=main_kb(u,gid))
    else:
        await update.message.reply_text("🦎 *ЛУПИЗДРИК*\n`.профіль` `.тап` `.топ`",parse_mode=ParseMode.MARKDOWN)

async def on_profile(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    if not no_rep(update.message):return
    d=load();u,gid=setup(d,update);save(d)
    await update.message.reply_text(main_text(u,d,gid),parse_mode=ParseMode.MARKDOWN,reply_markup=main_kb(u,gid))

async def on_tap(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    if not no_rep(update.message):return
    d=load();u,gid=setup(d,update)
    if u.get("banned"):save(d);await update.message.reply_text("🔨 Тебе заблоковано.");return
    if not can_tap(u):save(d);await update.message.reply_text(f"⏳ Вже тапнув!\nСкид о 00:00 · {reset_t()}",parse_mode=ParseMode.MARKDOWN);return
    x2=is_x2(d);gt,gc,mult,sb=do_tap(u,x2);new=check_ach(u);save(d)
    hdr="🎰 *ДЖЕКПОТ!*" if mult>=6 else "🔥 *Відмінно!*" if mult>=3 else "✨ *Гарний тап!*" if mult>=1.5 else "👆 *Тап*"
    bns=f" · скін ×{sb:.1f}" if sb>1 else ""
    x2t=" · ⚡×2 ПОДІЯ!" if x2 else ""
    ach=("\n🎉 "+", ".join(a[1] for a in new)) if new else ""
    await update.message.reply_text(f"{hdr} ×{mult:.1f}{bns}{x2t}\n+*{gt:,}* тапів · +*{gc:,}* монет{ach}\n\n{main_text(u,d,gid)}",parse_mode=ParseMode.MARKDOWN,reply_markup=main_kb(u,gid))

async def on_top(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    if not no_rep(update.message):return
    d=load();u,gid=setup(d,update);save(d)
    if not gid:await update.message.reply_text("❌ Тільки для груп!");return
    await update.message.reply_text(lb_text(d,gid,"all"),parse_mode=ParseMode.MARKDOWN,reply_markup=lb_kb(gid,"all"))

async def on_btn(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query;await q.answer()
    d=load();tg=q.from_user;u=gu(d,tg.id)
    u["name"]=tg.first_name or "Гравець";u["uname"]=tg.username;u["lang"]=tg.language_code
    a=q.data;chat=q.message.chat;gid=chat.id if chat.type in("group","supergroup") else None
    if gid:add_mb(d,gid,tg.id)

    async def ed(txt,kb):
        try:await q.edit_message_text(txt,parse_mode=ParseMode.MARKDOWN,reply_markup=kb)
        except:pass

    if a=="noop":return
    if a=="play":save(d);await ed(main_text(u,d,gid),main_kb(u,gid));return

    if a.startswith("back_"):
        gs=a[5:];gid=int(gs) if gs.lstrip("-").isdigit() else None;save(d)
        await ed(main_text(u,d,gid),main_kb(u,gid));return

    if a.startswith("lb_"):
        pts=a.split("_",2);gs=pts[1];period=pts[2];gid=int(gs) if gs.lstrip("-").isdigit() else None;save(d)
        await ed(lb_text(d,gid,period),lb_kb(gid,period));return

    if a=="tap":
        if u.get("banned"):await q.answer("🔨 Заблоковано",show_alert=True);return
        if not can_tap(u):await q.answer(f"⏳ Скид о 00:00 · {reset_t()}",show_alert=True);save(d);return
        x2=is_x2(d);gt,gc,mult,sb=do_tap(u,x2);new=check_ach(u);save(d)
        hdr="🎰 ДЖЕКПОТ!" if mult>=6 else "🔥 Відмінно!" if mult>=3 else "✨ Гарно!" if mult>=1.5 else "👆 Тап"
        x2t=" ⚡×2" if x2 else ""
        ach=("\n🎉 "+", ".join(x[1] for x in new)) if new else ""
        await ed(f"*{hdr}* ×{mult:.1f}{x2t}\n+{gt:,} тапів · +{gc:,} монет{ach}\n\n{main_text(u,d,gid)}",main_kb(u,gid));return

    if a=="shop":save(d);await ed(shop_text(u),shop_kb(u,gid or 0));return

    if a.startswith("buy_"):
        pts=a.split("_",2);upg_id=pts[1];gb=int(pts[2]) if len(pts)>2 and pts[2].lstrip("-").isdigit() else 0
        upg=next((x for x in UPGRADES if x[0]==upg_id),None)
        if not upg:await q.answer("❌");return
        if upg_id in u.get("upg",[]):await q.answer("✅ Вже куплено!");return
        if u.get("coins",0)<upg[3]:await q.answer(f"❌ Потрібно {upg[3]:,}");return
        u["coins"]-=upg[3];u.setdefault("upg",[]).append(upg_id);check_ach(u);save(d)
        await q.answer(f"✅ {upg[1]} куплено!")
        await ed(shop_text(u),shop_kb(u,gb));return

    if a.startswith("skins_"):
        pts=a.split("_");pg=int(pts[1]);gb=int(pts[2]) if len(pts)>2 and pts[2].lstrip("-").isdigit() else gid or 0
        save(d);await ed(skins_text(u),skins_kb(u,gb,pg));return

    if a.startswith("sbuy_"):
        pts=a.split("_",2);sid=pts[1];gb=int(pts[2]) if pts[2].lstrip("-").isdigit() else 0
        if sid not in SKINS:await q.answer("❌");return
        if sid in u.get("owned_skins",[]):await q.answer("✅ Вже є!");return
        cost=SKINS[sid][2]
        if u.get("coins",0)<cost:await q.answer(f"❌ Потрібно {cost:,}");return
        u["coins"]-=cost;u.setdefault("owned_skins",["default"]).append(sid);u["skin"]=sid;check_ach(u);save(d)
        await q.answer(f"✅ {SKINS[sid][0]} одягнено!")
        await ed(skins_text(u),skins_kb(u,gb));return

    if a.startswith("seq_"):
        pts=a.split("_",2);sid=pts[1];gb=int(pts[2]) if pts[2].lstrip("-").isdigit() else 0
        if sid not in u.get("owned_skins",[]):await q.answer("❌");return
        u["skin"]=sid;save(d);await q.answer(f"✅ {SKINS[sid][0]} одягнено!")
        await ed(skins_text(u),skins_kb(u,gb));return

    if a=="ach":
        txt=f"🎖 *Досягнення*\n{'─'*20}\n"
        for ac in ACHIEVEMENTS:
            earned=ac[0] in u.get("ach",[])
            req=f"{ac[2]:,} тапів" if ac[2] else f"{ac[3]}д стріку" if ac[3] else ("1M монет" if ac[0]=="rich" else "5 скінів")
            txt+=f"{'✅' if earned else '🔒'} *{ac[1]}* — _{req}_\n"
        save(d);await ed(txt,InlineKeyboardMarkup([[btn("↩️ Назад",f"back_{gid or 0}")]]));return

    if a.startswith("ga_join_"):
        ga_id=a[8:];d2=load()
        ga=next((g for g in d2.get("giveaways",[]) if g["id"]==ga_id),None)
        if not ga or ga.get("ended"):await q.answer("❌ Розіграш завершено");return
        if str(tg.id) in ga.get("participants",[]):await q.answer("✅ Ти вже в розіграші!");return
        ga.setdefault("participants",[]).append(str(tg.id))
        wu=gu(d2,tg.id);wu["name"]=tg.first_name or "?";wu["uname"]=tg.username
        save(d2);cnt=len(ga["participants"]);await q.answer(f"✅ Ти в розіграші! Учасників: {cnt}")
        try:await q.edit_message_reply_markup(InlineKeyboardMarkup([[btn(f"🎉 Взяти участь ({cnt})",f"ga_join_{ga_id}")]]))
        except:pass
        return

    if not is_dev(tg):save(d);return

    if a=="dev":
        await ed(
            f"{'═'*21}\n  ⚙️ *ПАНЕЛЬ РОЗРОБНИКА*\n{'═'*21}\n\n👥 Юзерів: *{len(d.get('users',{}))}* · 💬 Груп: *{len(d.get('groups',{}))}*\n{'─'*21}",
            InlineKeyboardMarkup([
                [btn("📢 Розсилка","dv_bc"),btn("🎁 Розіграш","dv_ga")],
                [btn("📣 Анонс","dv_ann"),btn("🎰 Подія ×2","dv_x2")],
                [btn("👥 Юзери","dv_users"),btn("📊 Стата","dv_stats")],
                [btn("💬 Чати","dv_chats"),btn("🔍 Знайти юзера","dv_lookup")],
                [btn("💰 Монети","dv_gc"),btn("👆 Тапи","dv_gt")],
                [btn("🎨 Скін","dv_gs"),btn("💎 VIP","dv_vip")],
                [btn("🔨 Бан","dv_ban"),btn("🔄 Скинути","dv_reset")],
                [btn("🦎 Грати","play")],
            ]));return

    if a=="dv_users":
        users=d.get("users",{});txt=f"👥 *Юзери: {len(users)}*\n{'─'*20}\n"
        for uid,u2 in list(users.items())[:15]:
            un=f"@{u2.get('uname')}" if u2.get("uname") else f"`{uid}`"
            flags=("💎" if u2.get("vip") else "")+("🔨" if u2.get("banned") else "")
            txt+=f"{un} {flags}\n  👆{u2.get('taps',0):,} · 💰{u2.get('coins',0):,} · 🌐{u2.get('lang','?') or '?'}\n"
        if len(users)>15:txt+=f"\n_+{len(users)-15} ще..._"
        await ed(txt,InlineKeyboardMarkup([[btn("↩️ Назад","dev")]]));return

    if a=="dv_stats":
        users=d.get("users",{});groups=d.get("groups",{})
        active=sum(1 for u2 in users.values() if u2.get("tap_date")==today_k())
        tt=sum(u2.get("taps",0) for u2 in users.values())
        tc=sum(u2.get("coins",0) for u2 in users.values())
        vips=sum(1 for u2 in users.values() if u2.get("vip"))
        bans=sum(1 for u2 in users.values() if u2.get("banned"))
        x2st="Активна ✅" if is_x2(d) else "Неактивна"
        txt=(f"📊 *Статистика*\n{'─'*20}\n"
             f"👥 Юзерів: *{len(users)}*\n💬 Груп: *{len(groups)}*\n"
             f"🔥 Активних сьогодні: *{active}*\n💎 VIP: *{vips}*\n🔨 Банів: *{bans}*\n"
             f"👆 Тапів всього: *{tt:,}*\n💰 Монет всього: *{tc:,}*\n"
             f"🎰 Подія ×2: *{x2st}*")
        await ed(txt,InlineKeyboardMarkup([[btn("↩️ Назад","dev")]]));return

    if a=="dv_chats":
        groups=d.get("groups",{});txt=f"💬 *Чати бота: {len(groups)}*\n{'─'*20}\n"
        for gs,g in list(groups.items())[:20]:
            txt+=f"`{gs}`\n  *{g.get('title','?')}* · 👥{len(g.get('members',[]))}\n"
        await ed(txt,InlineKeyboardMarkup([[btn("↩️ Назад","dev")]]));return

    def sa(action):ctx.user_data["dev_action"]=action

    if a=="dv_bc":
        await ed("📢 *Розсилка — куди?*",InlineKeyboardMarkup([
            [btn("📡 Всі чати","dv_bc_all")],[btn("🎯 Один чат (по ID)","dv_bc_one")],[btn("❌ Назад","dev")]
        ]));return
    if a=="dv_bc_all":sa("broadcast_all");await ed("📢 *Розсилка в усі чати*\n\nВідправ текст:",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_bc_one":sa("broadcast_one");await ed("📢 *Розсилка в один чат*\n\nФормат: `chat_id текст`\nПриклад: `-100123456789 Привіт!`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_ann":sa("announce");await ed("📣 *Анонс у всі чати*\n\nВідправ текст анонсу:",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_gc":sa("give_coins");await ed("💰 *Дати монети*\n\nФормат: `@юзер 1000`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_gt":sa("give_taps");await ed("👆 *Дати тапи*\n\nФормат: `@юзер 1000`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_gs":sa("give_skin");await ed("🎨 *Дати скін*\n\nФормат: `@юзер fire`\n\nСкіни: "+", ".join(f"`{s}`" for s in SKINS if s!="default"),InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_vip":sa("toggle_vip");await ed("💎 *VIP*\n\nФормат: `@юзер` або `user_id`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_ban":sa("toggle_ban");await ed("🔨 *Бан/Розбан*\n\nФормат: `@юзер` або `user_id`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_reset":sa("reset_user");await ed("🔄 *Скинути юзера*\n\nФормат: `@юзер all|coins|taps|streak|skin`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_lookup":sa("lookup");await ed("🔍 *Інфо юзера*\n\nФормат: `@юзер` або `user_id`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return

    if a=="dv_x2":
        await ed("🎰 *Подія ×2 тапів*\n\nОбери тривалість:",InlineKeyboardMarkup([
            [btn("5 хв","x2_5m"),btn("15 хв","x2_15m"),btn("30 хв","x2_30m")],
            [btn("1 год","x2_1h"),btn("2 год","x2_2h"),btn("6 год","x2_6h")],
            [btn("1 день","x2_1d"),btn("❌ Вимкнути","x2_off")],[btn("↩️ Назад","dev")],
        ]));return

    if a.startswith("x2_"):
        val=a[3:]
        if val=="off":d["x2_until"]=None;save(d);await ed("✅ Подія ×2 вимкнена",InlineKeyboardMarkup([[btn("↩️ Назад","dev")]]));return
        units={"m":60,"h":3600,"d":86400}
        secs=int(val[:-1])*units.get(val[-1],60)
        d["x2_until"]=(datetime.now(KYIV)+timedelta(seconds=secs)).isoformat();save(d)
        label=val;groups_d=d.get("groups",{})
        for gs in groups_d:
            try:await ctx.bot.send_message(int(gs),f"🎰 *ПОДІЯ ×2 ТАПІВ!*\n\nНаступні {label} всі тапи подвоєні!\nПиши `.тап` зараз!",parse_mode=ParseMode.MARKDOWN)
            except:pass
        await ed(f"✅ Подія ×2 на {label} запущена!",InlineKeyboardMarkup([[btn("↩️ Назад","dev")]]))
        return

    if a=="dv_ga":
        await ed("🎁 *Розіграш — обери приз:*",InlineKeyboardMarkup([
            [btn("💰 Монети","ga_t_coins"),btn("👆 Тапи","ga_t_taps")],
            [btn("🎨 Скін","ga_t_skin"),btn("💎 VIP","ga_t_vip")],
            [btn("↩️ Назад","dev")],
        ]));return

    if a in("ga_t_coins","ga_t_taps","ga_t_skin","ga_t_vip"):
        t=a[5:];ctx.user_data["ga_type"]=t
        tips={"coins":"Формат: `час кількість`\nПриклад: `300 5000` (300 сек, 5000 монет)\n`25.02 10000` (до 25 лютого, 10k)","taps":"Формат: `час кількість`\nПриклад: `600 3000`","skin":f"Формат: `час скін`\nПриклад: `300 dragon`\nСкіни: {', '.join(f'`{s}`' for s in SKINS if s!='default')}","vip":"Формат: `час`\nПриклад: `300` або `25.02`"}
        ctx.user_data["dev_action"]="giveaway"
        await ed(f"🎁 *Розіграш*\n\n{tips.get(t,'Формат: час [значення]')}\n\nЧас: секунди / `Xm` хвилини / `Xh` години / `Xd` дні / `дд.мм`",InlineKeyboardMarkup([[btn("❌ Скасувати","dv_ga")]]))
        return

    save(d)

def parse_time(s):
    try:
        if "." in s:
            pts=s.split(".");dd,mm=int(pts[0]),int(pts[1]);yy=int(pts[2]) if len(pts)>2 else datetime.now(KYIV).year
            return max(10,int((datetime(yy,mm,dd,23,59,tzinfo=KYIV)-datetime.now(KYIV)).total_seconds()))
        if s.endswith("m"):return int(s[:-1])*60
        if s.endswith("h"):return int(s[:-1])*3600
        if s.endswith("d"):return int(s[:-1])*86400
        return int(s)
    except:return 60

def fmt_time(secs):
    if secs>=86400:return f"{secs//86400}д {(secs%86400)//3600}г"
    if secs>=3600:return f"{secs//3600}г {(secs%3600)//60}хв"
    if secs>=60:return f"{secs//60}хв"
    return f"{secs}сек"

async def dev_text(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    tg=update.effective_user
    if not is_dev(tg) or update.effective_chat.type!="private":return
    action=ctx.user_data.get("dev_action")
    if not action:return
    text=update.message.text.strip()
    d=load()

    def find(ref):
        ref=ref.lstrip("@").lower()
        for uid,u2 in d["users"].items():
            if (u2.get("uname") or "").lower()==ref or uid==ref:return uid,u2
        return None,None

    ctx.user_data.pop("dev_action",None)

    if action=="broadcast_all":
        groups=d.get("groups",{});sent=0
        for gs in groups:
            try:await ctx.bot.send_message(int(gs),f"📢 {text}",parse_mode=ParseMode.MARKDOWN);sent+=1
            except:pass
        await update.message.reply_text(f"✅ Відправлено в {sent} чатів");return

    if action=="broadcast_one":
        pts=text.split(" ",1);chat_id=int(pts[0]);msg=pts[1] if len(pts)>1 else ""
        try:await ctx.bot.send_message(chat_id,f"📢 {msg}",parse_mode=ParseMode.MARKDOWN);await update.message.reply_text("✅ Відправлено")
        except Exception as e:await update.message.reply_text(f"❌ Помилка: {e}")
        return

    if action=="announce":
        groups=d.get("groups",{});sent=0
        for gs in groups:
            try:await ctx.bot.send_message(int(gs),f"📣 *ОГОЛОШЕННЯ*\n\n{text}",parse_mode=ParseMode.MARKDOWN);sent+=1
            except:pass
        await update.message.reply_text(f"✅ Анонс в {sent} чатів");return

    if action=="give_coins":
        pts=text.split();ref=pts[0];amt=int(pts[1]) if len(pts)>1 else 0
        uid,u2=find(ref)
        if not u2:await update.message.reply_text("❌ Не знайдений");return
        u2["coins"]=u2.get("coins",0)+amt;save(d);await update.message.reply_text(f"✅ +{amt:,} 💰 → {ref}");return

    if action=="give_taps":
        pts=text.split();ref=pts[0];amt=int(pts[1]) if len(pts)>1 else 0
        uid,u2=find(ref)
        if not u2:await update.message.reply_text("❌ Не знайдений");return
        u2["taps"]=u2.get("taps",0)+amt;save(d);await update.message.reply_text(f"✅ +{amt:,} 👆 → {ref}");return

    if action=="give_skin":
        pts=text.split();ref=pts[0];sid=pts[1] if len(pts)>1 else ""
        uid,u2=find(ref)
        if not u2:await update.message.reply_text("❌ Не знайдений");return
        if sid not in SKINS:await update.message.reply_text("❌ Скін не існує");return
        u2.setdefault("owned_skins",["default"])
        if sid not in u2["owned_skins"]:u2["owned_skins"].append(sid)
        u2["skin"]=sid;save(d);await update.message.reply_text(f"✅ {SKINS[sid][0]} {SKINS[sid][1]} → {ref}");return

    if action=="toggle_vip":
        uid,u2=find(text.strip())
        if not u2:await update.message.reply_text("❌ Не знайдений");return
        u2["vip"]=not u2.get("vip",False);save(d)
        await update.message.reply_text(f"✅ VIP {'видано 💎' if u2['vip'] else 'знято'} → {text.strip()}");return

    if action=="toggle_ban":
        uid,u2=find(text.strip())
        if not u2:await update.message.reply_text("❌ Не знайдений");return
        u2["banned"]=not u2.get("banned",False);save(d)
        await update.message.reply_text(f"{'🔨 Заблоковано' if u2['banned'] else '✅ Розблоковано'}: {text.strip()}");return

    if action=="reset_user":
        pts=text.split();ref=pts[0];what=pts[1] if len(pts)>1 else "all"
        uid,u2=find(ref)
        if not u2:await update.message.reply_text("❌ Не знайдений");return
        if what=="all":
            u2.update({"taps":0,"coins":0,"upg":[],"ach":[],"streak":0,"hist":{},"tap_date":None,"bonus_date":None,"skin":"default","owned_skins":["default"],"vip":False,"banned":False})
        elif what=="coins":u2["coins"]=0
        elif what=="taps":u2["taps"]=0;u2["hist"]={}
        elif what=="streak":u2["streak"]=0
        elif what=="skin":u2["skin"]="default";u2["owned_skins"]=["default"]
        save(d);await update.message.reply_text(f"✅ {ref}: [{what}] скинуто");return

    if action=="lookup":
        uid,u2=find(text.strip())
        if not u2:await update.message.reply_text("❌ Не знайдений");return
        sn=SKINS.get(u2.get("skin","default"),("","?"))[1]
        txt=(f"🔍 *Юзер: {u2.get('name','?')}*\n{'─'*20}\n"
             f"ID: `{uid}`\nUsername: @{u2.get('uname') or '—'}\nМова: {u2.get('lang') or '?'}\n"
             f"👆 {u2.get('taps',0):,} тапів\n💰 {u2.get('coins',0):,} монет\n"
             f"🔥 Стрік: {u2.get('streak',0)}д\n🎖 Досяг: {len(u2.get('ach',[]))}/{len(ACHIEVEMENTS)}\n"
             f"🎨 Скін: {sn}\n💎 VIP: {'Так' if u2.get('vip') else 'Ні'}\n🔨 Бан: {'Так' if u2.get('banned') else 'Ні'}")
        await update.message.reply_text(txt,parse_mode=ParseMode.MARKDOWN);return

    if action=="giveaway":
        ga_type=ctx.user_data.pop("ga_type","coins")
        pts=text.strip().split(" ",1);time_str=pts[0];val=pts[1].strip() if len(pts)>1 else ""
        secs=max(10,parse_time(time_str))
        ga_id=f"ga_{int(datetime.now().timestamp())}"
        ga={"id":ga_id,"type":ga_type,"value":val,"participants":[],"ended":False}
        d.setdefault("giveaways",[]).append(ga)
        prize_map={"coins":f"💰 {int(val):,} монет" if val.isdigit() else "💰 монети","taps":f"👆 {int(val):,} тапів" if val.isdigit() else "👆 тапи","skin":f"{SKINS.get(val,('🎨','?',0,0))[0]} {SKINS.get(val,('🎨','?',0,0))[1]}" if val else "🎨 скін","vip":"💎 VIP статус"}
        prize_txt=prize_map.get(ga_type,"🎁 Приз")
        time_txt=fmt_time(secs)
        ga_text=(f"{'═'*21}\n🎁 *РОЗІГРАШ!*\n{'─'*21}\n\n🏆 Приз: *{prize_txt}*\n⏱ Час: *{time_txt}*\n\nНатисни кнопку нижче!")
        ga_kb=InlineKeyboardMarkup([[btn("🎉 Взяти участь (0)",f"ga_join_{ga_id}")]])
        groups=d.get("groups",{});save(d);sent_msgs=[]
        for gs in groups:
            try:
                msg=await ctx.bot.send_message(int(gs),ga_text,parse_mode=ParseMode.MARKDOWN,reply_markup=ga_kb)
                sent_msgs.append((int(gs),msg.message_id))
            except:pass
        await update.message.reply_text(f"✅ Розіграш запущено в {len(sent_msgs)} чатах!\nЧерез {time_txt} оберу переможця.")

        async def end_ga():
            await asyncio.sleep(secs)
            d2=load();ga2=next((g for g in d2.get("giveaways",[]) if g["id"]==ga_id),None)
            if not ga2 or ga2.get("ended"):return
            ga2["ended"]=True;participants=ga2.get("participants",[])
            if not participants:
                res=f"🎁 *Розіграш завершено*\n\n_Ніхто не взяв участь_ 😔"
            else:
                wid=random.choice(participants);wu2=gu(d2,wid)
                wn=f"@{wu2['uname']}" if wu2.get("uname") else wu2.get("name","?")
                if ga_type=="coins" and val.isdigit():wu2["coins"]=wu2.get("coins",0)+int(val)
                elif ga_type=="taps" and val.isdigit():wu2["taps"]=wu2.get("taps",0)+int(val)
                elif ga_type=="skin" and val in SKINS:
                    wu2.setdefault("owned_skins",["default"])
                    if val not in wu2["owned_skins"]:wu2["owned_skins"].append(val)
                elif ga_type=="vip":wu2["vip"]=True
                res=(f"{'═'*21}\n🎁 *Розіграш завершено!*\n{'─'*21}\n\n🏆 Переможець: *{wn}*\n🎉 Приз: *{prize_txt}*\n👥 Учасників: {len(participants)}")
            save(d2)
            for gid_s,mid in sent_msgs:
                try:await ctx.bot.edit_message_text(res,chat_id=gid_s,message_id=mid,parse_mode=ParseMode.MARKDOWN)
                except:pass
        asyncio.create_task(end_ga());return

def main():
    app=Application.builder().token(TOKEN).build()
    no_r=filters.TEXT&~filters.REPLY
    app.add_handler(CommandHandler("start",cmd_start))
    app.add_handler(MessageHandler(filters.Regex(r"^\.профіль$")&no_r,on_profile))
    app.add_handler(MessageHandler(filters.Regex(r"^\.тап$")&no_r,on_tap))
    app.add_handler(MessageHandler(filters.Regex(r"^\.топ$")&no_r,on_top))
    app.add_handler(MessageHandler(filters.TEXT&filters.ChatType.PRIVATE&~filters.COMMAND,dev_text))
    app.add_handler(CallbackQueryHandler(on_btn))
    logging.warning("🦎 запущено!")
    app.run_polling(allowed_updates=Update.ALL_TYPES,drop_pending_updates=True)

if __name__=="__main__":main()
