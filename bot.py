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

LEVELS=[
    (0,5,"🥚","Яєчко"),(500,12,"🐛","Гусінь"),(2000,22,"🐌","Слизняк"),
    (6000,40,"🦎","Ящірка"),(15000,65,"🦊","Лисиця"),(35000,100,"🦄","Єдиноріг"),
    (80000,160,"🐉","Дракон"),(180000,250,"👾","Легенда"),(400000,400,"✨","Бог"),
    (1000000,650,"👑","Абсолют"),
]
SKINS={
    "default":("🦎","Звичайний",0,1.0),"fire":("🔥","Вогняний",1000,1.2),
    "ice":("❄️","Крижаний",1000,1.15),"gold":("⭐","Золотий",2500,1.3),
    "shadow":("🌑","Тіньовий",2500,1.25),"rainbow":("🌈","Райдужний",5000,1.4),
    "cosmic":("🌌","Космічний",8000,1.5),"dragon":("🐲","Дракон",10000,1.6),
    "devil":("😈","Диявол",15000,1.5),"angel":("😇","Ангел",15000,1.55),
    "cyber":("🤖","Кіберпанк",20000,1.6),"ghost":("👻","Привид",5000,1.2),
    "king":("👑","Король",30000,1.8),"ninja":("🥷","Ніндзя",12000,1.45),
    "alien":("👽","Прибулець",8000,1.35),"unicorn":("🦄","Єдиноріг",18000,1.65),
    "phoenix":("🦅","Фенікс",25000,1.7),"vip_skin":("💎","VIP",50000,2.0),
}
UPGRADES=[
    ("paw","🐾 Золота лапа","+50%",500,1.5),("drink","⚡ Енергетик","+100%",2500,2.0),
    ("rocket","🚀 Ракета","+200%",10000,3.0),("cosmos","🌌 Космос","+500%",40000,6.0),
    ("quantum","🔮 Квантум","+1000%",150000,11.0),("time","⏰ Машина часу","+2000%",500000,21.0),
]
ACHIEVEMENTS=[
    ("t100","💯 Сотня тапів",100,0),("t1k","🔥 Тисячник",1000,0),
    ("t10k","💎 10к тапів",10000,0),("t50k","👑 50к тапів",50000,0),
    ("t100k","🌟 100к тапів",100000,0),("t500k","🚀 500к тапів",500000,0),
    ("s7","📅 Тиждень стріку",0,7),("s30","🗓 Місяць стріку",0,30),
    ("s100","🔱 100 днів стріку",0,100),("rich","💰 Мільйонер",0,0),
    ("skins5","🎨 Колекціонер 5 скінів",0,0),("upg_all","🔧 Максимальний апгрейд",0,0),
]
QUESTS_POOL=[
    ("tap3","Тапни 3 дні поспіль","streak",3,500,200),
    ("tap7","Тапни 7 днів поспіль","streak",7,2000,500),
    ("earn500","Заробити 500 монет за 1 тап","single_coins",500,800,300),
    ("earn2k","Заробити 2000 монет за 1 тап","single_coins",2000,3000,1000),
    ("jackpot","Отримати ДЖЕКПОТ","jackpot",1,1500,500),
    ("jackpot3","Отримати 3 джекпоти","jackpot",3,5000,1500),
    ("coins5k","Накопичити 5000 монет","total_coins",5000,1000,300),
    ("coins50k","Накопичити 50000 монет","total_coins",50000,5000,1500),
    ("taps5k","Набрати 5000 тапів","total_taps",5000,1000,400),
    ("taps50k","Набрати 50000 тапів","total_taps",50000,5000,2000),
    ("lvl3","Досягти рівня Слизняк","reach_level",2,800,200),
    ("lvl5","Досягти рівня Лисиця","reach_level",4,2000,500),
    ("buy1","Купити будь-яке покращення","buy_upg",1,600,200),
    ("buy3","Купити 3 покращення","buy_upg",3,2500,700),
    ("skin1","Купити будь-який скін","buy_skin",1,700,300),
]
MEDALS=["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
VIP_DAYS=30

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
    defs=[("name","Гравець"),("uname",None),("lang",None),("taps",0),("coins",0),
          ("upg",[]),("ach",[]),("streak",0),("hist",{}),("tap_date",None),
          ("bonus_date",None),("skin","default"),("owned_skins",["default"]),
          ("banned",False),("vip",None),("quests",{}),("active_quests",[]),
          ("jackpots",0),("total_taps_all",0)]
    for k,v in defs:u.setdefault(k,v)
    return u

def add_mb(d,gid,uid):
    g=d["groups"].setdefault(str(gid),{"title":"","members":[]})
    g.setdefault("members",[])
    if str(uid) not in g["members"]:g["members"].append(str(uid))

def get_mb(d,gid):return d["groups"].get(str(gid),{}).get("members",[])
def is_dev(tg):return tg.id==DEV_ID or (tg.username and tg.username.lower()==DEV_UN.lower())
def today_k():return datetime.now(KYIV).date().isoformat()
def can_tap(u):return u.get("tap_date")!=today_k()
def is_vip(u):
    v=u.get("vip")
    if not v:return False
    try:return datetime.fromisoformat(v)>datetime.now(KYIV)
    except:return False

def vip_days_left(u):
    v=u.get("vip")
    if not v:return 0
    try:
        d=(datetime.fromisoformat(v)-datetime.now(KYIV)).days
        return max(0,d)
    except:return 0

def reset_t():
    nw=datetime.now(KYIV);nx=datetime.combine(nw.date()+timedelta(days=1),dtime(0,0),tzinfo=KYIV)
    df=nx-nw;h=int(df.total_seconds()//3600);m=int((df.total_seconds()%3600)//60)
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
    if is_vip(u):p=int(p*2)
    if x2:p=int(p*2)
    return p

def do_tap(u,x2=False):
    base=calc_pow(u,x2);r=random.random()
    if r<.50:mult=random.uniform(0.5,1.5);jack=False
    elif r<.80:mult=random.uniform(1.5,3.0);jack=False
    elif r<.95:mult=random.uniform(3.0,6.0);jack=False
    else:mult=random.uniform(6.0,20.0);jack=True
    sb=SKINS.get(u.get("skin","default"),("","",0,1.0))[3]
    vip_b=1.5 if is_vip(u) else 1.0
    gt=max(1,int(base*mult*sb));gc=max(1,int(gt*random.uniform(0.5,2.0)*vip_b))
    u["taps"]+=gt;u["coins"]+=gc;u["total_taps_all"]=u.get("total_taps_all",0)+gt
    if jack:u["jackpots"]=u.get("jackpots",0)+1
    td=today_k();yest=(datetime.now(KYIV).date()-timedelta(days=1)).isoformat()
    if u.get("bonus_date")==yest:u["streak"]=u.get("streak",0)+1
    elif u.get("bonus_date")!=td:u["streak"]=1
    u["tap_date"]=td;u["bonus_date"]=td
    h=u.setdefault("hist",{});h[td]=h.get(td,0)+gt
    cut=(datetime.now(KYIV).date()-timedelta(days=35)).isoformat()
    u["hist"]={k:v for k,v in h.items() if k>cut}
    update_quests(u,single_coins=gc,jackpot=jack)
    return gt,gc,mult,sb,jack

def check_ach(u):
    new=[]
    for a in ACHIEVEMENTS:
        if a[0] in u.get("ach",[]):continue
        ok=(a[2]>0 and u["taps"]>=a[2]) or (a[3]>0 and u.get("streak",0)>=a[3]) or \
           (a[0]=="rich" and u.get("coins",0)>=1000000) or \
           (a[0]=="skins5" and len(u.get("owned_skins",[]))>=5) or \
           (a[0]=="upg_all" and len(u.get("upg",[]))==len(UPGRADES))
        if ok:u.setdefault("ach",[]).append(a[0]);new.append(a)
    return new

def ptaps(u,period):
    if period=="all":return u.get("taps",0)
    days={"day":1,"week":7,"month":30}[period]
    cut=(datetime.now(KYIV).date()-timedelta(days=days)).isoformat()
    return sum(v for k,v in u.get("hist",{}).items() if k>cut)

def assign_quests(u):
    if len(u.get("active_quests",[]))>=3:return
    done=set(u.get("quests",{}).keys())
    lvl_idx=next((i for i,L in enumerate(LEVELS) if u["taps"]<L[0]),len(LEVELS))-1
    available=[q for q in QUESTS_POOL if q[0] not in done and q[0] not in [aq["id"] for aq in u.get("active_quests",[])] ]
    random.shuffle(available)
    needed=3-len(u.get("active_quests",[]))
    for q in available[:needed]:
        u.setdefault("active_quests",[]).append({"id":q[0],"progress":0})

def update_quests(u,single_coins=0,jackpot=False):
    quests_map={q[0]:q for q in QUESTS_POOL}
    completed=[]
    for aq in u.get("active_quests",[]):
        qdef=quests_map.get(aq["id"])
        if not qdef:continue
        qtype=qdef[3+1]
        if qtype=="streak":aq["progress"]=u.get("streak",0)
        elif qtype=="jackpot" and jackpot:aq["progress"]=u.get("jackpots",0)
        elif qtype=="single_coins" and single_coins>=qdef[4]:aq["progress"]+=1
        elif qtype=="total_coins":aq["progress"]=u.get("coins",0)
        elif qtype=="total_taps":aq["progress"]=u.get("taps",0)
        elif qtype=="reach_level":aq["progress"]=next((i for i,L in enumerate(LEVELS) if u["taps"]<L[0]),len(LEVELS))-1
        if aq["progress"]>=qdef[4]:
            completed.append(aq["id"])
    for qid in completed:
        u["active_quests"]=[aq for aq in u["active_quests"] if aq["id"]!=qid]
        u.setdefault("quests",{})[qid]=True
        qdef=quests_map[qid]
        u["coins"]+=qdef[5];u["taps"]+=qdef[6]
    return [quests_map[qid] for qid in completed]

def on_buy_upg(u):
    quests_map={q[0]:q for q in QUESTS_POOL}
    completed=[]
    for aq in u.get("active_quests",[]):
        qdef=quests_map.get(aq["id"])
        if not qdef:continue
        if qdef[3+1]=="buy_upg":
            aq["progress"]=len(u.get("upg",[]))
            if aq["progress"]>=qdef[4]:completed.append(aq["id"])
    for qid in completed:
        u["active_quests"]=[aq for aq in u["active_quests"] if aq["id"]!=qid]
        u.setdefault("quests",{})[qid]=True
        qdef=quests_map[qid];u["coins"]+=qdef[5];u["taps"]+=qdef[6]

def on_buy_skin(u):
    quests_map={q[0]:q for q in QUESTS_POOL}
    for aq in u.get("active_quests",[])[:]:
        qdef=quests_map.get(aq["id"])
        if not qdef:continue
        if qdef[3+1]=="buy_skin":
            u["active_quests"].remove(aq)
            u.setdefault("quests",{})[aq["id"]]=True
            u["coins"]+=qdef[5];u["taps"]+=qdef[6]
            break

def parse_dur(s):
    s=s.strip().lower()
    try:
        for sfx,mul in [("day",86400),("days",86400),("д",86400),("h",3600),("hour",3600),("год",3600),("min",60),("хв",60),("m",60),("s",1),("с",1),("sec",1)]:
            if s.endswith(sfx):return max(10,int(s[:-len(sfx)].strip())*mul)
        return max(10,int(s))
    except:return 60

def fmt_dur(secs):
    if secs>=86400:return f"{secs//86400}д"
    if secs>=3600:return f"{secs//3600}г {(secs%3600)//60}хв"
    if secs>=60:return f"{secs//60}хв"
    return f"{secs}с"

def sk(u):return SKINS.get(u.get("skin","default"),("🦎",))[0]
def btn(t,c):return InlineKeyboardButton(t,callback_data=c)

def pbar(u):
    L=get_lvl(u["taps"]);nL=get_nlvl(u["taps"])
    if not nL:return "Максимум!"
    total=nL[0]-L[0];done=u["taps"]-L[0]
    pct=min(10,int(done/total*10)) if total else 10
    return f"{'█'*pct}{'░'*(10-pct)} {nL[0]-u['taps']:,} до {nL[2]}"

def vip_badge(u):
    if not is_vip(u):return ""
    d=vip_days_left(u)
    return f" 💎VIP({d}д)"

def main_text(u,d=None,gid=None):
    L=get_lvl(u["taps"]);p=calc_pow(u,is_x2(d) if d else False)
    s=sk(u);sn=SKINS.get(u.get("skin","default"),("","Звичайний"))[1]
    x2m=" ⚡×2" if d and is_x2(d) else ""
    upgs=""
    if u.get("upg"):upgs="\n🔧 "+" · ".join(ug[1] for ug in UPGRADES if ug[0] in u["upg"])
    tap_st="✅ Готово до тапу!" if can_tap(u) else f"⏳ Скид о 00:00 {reset_t()}"
    rank=""
    if d and gid:
        ms=get_mb(d,gid);md=[d["users"][m] for m in ms if m in d["users"]]
        ranked=sorted(md,key=lambda x:x.get("taps",0),reverse=True)
        pos=next((i+1 for i,x in enumerate(ranked) if x is u),"-")
        rank=f"  🏆 #{pos}/{len(ranked)}\n"
    qcount=len(u.get("active_quests",[]))
    return (
        f"{s} *ЛУПИЗДРИК*{vip_badge(u)}{x2m}\n\n"
        f"{L[2]} *{L[3]}*\n"
        f"{pbar(u)}\n\n"
        f"👆 *{u['taps']:,}* тапів\n"
        f"{rank}"
        f"💰 *{u['coins']:,}* монет\n"
        f"⚡ Сила *{p}*  🎨 {sn}\n"
        f"🔥 Стрік *{u.get('streak',0)}д*  🎖 *{len(u.get('ach',[]))}/{len(ACHIEVEMENTS)}*"
        f"{upgs}\n\n"
        f"📋 Квестів: *{qcount}*\n"
        f"{tap_st}"
    )

def main_kb(u,gid=None):
    ct=can_tap(u);s=sk(u)
    lbl=f"{s} ТАП {s}" if ct else "⏳ Вже тапнув"
    return InlineKeyboardMarkup([
        [btn(lbl,"tap")],
        [btn("🏪 Магазин","shop"),btn("🎨 Скіни","skins_0_0")],
        [btn("📋 Квести","quests"),btn("🎖 Досягнення","ach")],
        [btn("🏆 Топ",f"lb_{gid or 0}_all")],
    ])

def lb_text(d,gid,period):
    pn={"day":"День","week":"Тиждень","month":"Місяць","all":"Весь час"}
    ms=get_mb(d,gid)
    if not ms:return f"🏆 Топ {pn[period]}\n\nПоки нікого!"
    top=sorted([(m,d["users"][m]) for m in ms if m in d["users"]],key=lambda x:ptaps(x[1],period),reverse=True)[:10]
    txt=f"🏆 *Топ {pn[period]}*\n\n";shown=0
    for i,(uid,u) in enumerate(top):
        t=ptaps(u,period)
        if t==0:break
        nm=f"@{u['uname']}" if u.get("uname") else u.get("name","?")
        vb="💎" if is_vip(u) else ""
        txt+=f"{MEDALS[i]} *{nm}* {vb}{sk(u)}\n  👆 {t:,}  {get_lvl(u['taps'])[3]}\n";shown+=1
    if not shown:txt+="Ніхто не тапав"
    return txt

def lb_kb(gid,period):
    defs=[("День","day"),("Тиждень","week"),("Місяць","month"),("Все","all")]
    row=[btn(("▶ " if p==period else "")+l,f"lb_{gid}_{p}") for l,p in defs]
    return InlineKeyboardMarkup([row,[btn("↩ Назад",f"back_{gid}")]])

def shop_text(u):
    txt=f"🏪 *Магазин*\n💰 {u['coins']:,} монет\n\n"
    owned=u.get("upg",[]);has=False
    for upg in UPGRADES:
        if upg[0] in owned:continue
        has=True;af="✅" if u.get("coins",0)>=upg[3] else "❌"
        txt+=f"{upg[1]} {af}  {upg[2]}\n  {upg[3]:,} 💰\n\n"
    if not has:txt+="Все куплено! 🎉"
    return txt

def shop_kb(u,gid):
    rows=[[btn(f"✅ {upg[1]}","noop")] if upg[0] in u.get("upg",[]) else [btn(f"{upg[1]}  {upg[3]:,}💰",f"buy_{upg[0]}_{gid}")] for upg in UPGRADES]
    rows.append([btn("↩ Назад",f"back_{gid}")])
    return InlineKeyboardMarkup(rows)

def skins_text(u):
    return f"🎨 *Скіни*\n💰 {u['coins']:,} монет\n\nСкін дає бонус до тапів"

def skins_kb(u,gid,page=0):
    owned=u.get("owned_skins",["default"]);cur=u.get("skin","default")
    sl=[s for s in SKINS if s!="default"];per=6;chunk=sl[page*per:(page+1)*per]
    rows=[]
    for s in chunk:
        em,nm,cost,mul=SKINS[s]
        if s in owned:
            lbl=("▶ " if s==cur else "✓ ")+f"{em} {nm}  ×{mul}"
            rows.append([btn(lbl,f"seq_{s}_{gid}")])
        else:
            rows.append([btn(f"{em} {nm}  ×{mul}  {cost:,}💰",f"sbuy_{s}_{gid}")])
    nav=[]
    if page>0:nav.append(btn("◀",f"skins_{page-1}_{gid}"))
    if (page+1)*per<len(sl):nav.append(btn("▶",f"skins_{page+1}_{gid}"))
    if nav:rows.append(nav)
    rows.append([btn("↩ Назад",f"back_{gid}")])
    return InlineKeyboardMarkup(rows)

def quests_text(u):
    assign_quests(u)
    qmap={q[0]:q for q in QUESTS_POOL}
    txt="📋 *Квести*\n\nВиконуй — отримуй нагороди!\n\n"
    for aq in u.get("active_quests",[]):
        qdef=qmap.get(aq["id"])
        if not qdef:continue
        prog=aq["progress"];target=qdef[4]
        pct=min(10,int(prog/target*10)) if target else 10
        bar=f"{'█'*pct}{'░'*(10-pct)}"
        txt+=f"*{qdef[1]}*\n{bar} {prog}/{target}\n💰+{qdef[5]:,}  👆+{qdef[6]:,}\n\n"
    done=len(u.get("quests",{}))
    txt+=f"\nВиконано всього: {done}/{len(QUESTS_POOL)}"
    return txt

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
    d=load();tg=update.effective_user;u,gid=setup(d,update);assign_quests(u);save(d)
    if is_dev(tg) and update.effective_chat.type=="private":
        await update.message.reply_text(
            f"Привіт, *{tg.first_name}*! 👋\nID: `{tg.id}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[btn("🦎 Грати","play")],[btn("⚙️ Панель розробника","dev")]]))
        return
    if update.effective_chat.type=="private":
        await update.message.reply_text(main_text(u,d,gid),parse_mode=ParseMode.MARKDOWN,reply_markup=main_kb(u,gid))
    else:
        await update.message.reply_text("🦎 *ЛУПИЗДРИК*\n`.профіль`  `.тап`  `.топ`",parse_mode=ParseMode.MARKDOWN)

async def on_profile(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    if not no_rep(update.message):return
    d=load();u,gid=setup(d,update);assign_quests(u);save(d)
    await update.message.reply_text(main_text(u,d,gid),parse_mode=ParseMode.MARKDOWN,reply_markup=main_kb(u,gid))

async def on_tap(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    if not no_rep(update.message):return
    d=load();u,gid=setup(d,update)
    if u.get("banned"):save(d);await update.message.reply_text("🔨 Заблоковано.");return
    if not can_tap(u):save(d);await update.message.reply_text(f"⏳ Вже тапнув!\nСкид о 00:00 Київ  {reset_t()}");return
    x2=is_x2(d);gt,gc,mult,sb,jack=do_tap(u,x2);q_done=update_quests(u);new_ach=check_ach(u);assign_quests(u);save(d)
    hdr="🎰 *ДЖЕКПОТ!*" if jack else "🔥 *Відмінно!*" if mult>=3 else "✨ *Гарний!*" if mult>=1.5 else "👆 *Тап*"
    extras=""
    if x2:extras+=" ⚡×2"
    if sb>1:extras+=f" 🎨×{sb:.1f}"
    if is_vip(u):extras+=" 💎×2"
    ach_t=("\n🎉 "+", ".join(a[1] for a in new_ach)) if new_ach else ""
    q_t=("\n📋 Квест виконано: "+", ".join(q[1] for q in q_done)+" — нагороду отримано!") if q_done else ""
    await update.message.reply_text(
        f"{hdr} ×{mult:.1f}{extras}\n+*{gt:,}* тапів  +*{gc:,}* монет{ach_t}{q_t}\n\n{main_text(u,d,gid)}",
        parse_mode=ParseMode.MARKDOWN,reply_markup=main_kb(u,gid))

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
    if a=="play":assign_quests(u);save(d);await ed(main_text(u,d,gid),main_kb(u,gid));return

    if a.startswith("back_"):
        gs=a[5:];gid=int(gs) if gs.lstrip("-").isdigit() else None
        assign_quests(u);save(d);await ed(main_text(u,d,gid),main_kb(u,gid));return

    if a.startswith("lb_"):
        pts=a.split("_",2);gs=pts[1];period=pts[2];gid=int(gs) if gs.lstrip("-").isdigit() else None;save(d)
        await ed(lb_text(d,gid,period),lb_kb(gid,period));return

    if a=="tap":
        if u.get("banned"):await q.answer("🔨 Заблоковано",show_alert=True);return
        if not can_tap(u):await q.answer(f"⏳ Скид о 00:00  {reset_t()}",show_alert=True);save(d);return
        x2=is_x2(d);gt,gc,mult,sb,jack=do_tap(u,x2);q_done=update_quests(u);new_ach=check_ach(u);assign_quests(u);save(d)
        hdr="🎰 ДЖЕКПОТ!" if jack else "🔥 Відмінно!" if mult>=3 else "✨ Гарно!" if mult>=1.5 else "👆 Тап"
        x2t=" ⚡×2" if x2 else "";vt=" 💎×2" if is_vip(u) else ""
        ach_t=("\n🎉 "+", ".join(a2[1] for a2 in new_ach)) if new_ach else ""
        q_t=("\n📋 Квест: "+", ".join(q2[1] for q2 in q_done)) if q_done else ""
        await ed(f"*{hdr}* ×{mult:.1f}{x2t}{vt}\n+{gt:,} тапів  +{gc:,} монет{ach_t}{q_t}\n\n{main_text(u,d,gid)}",main_kb(u,gid));return

    if a=="shop":save(d);await ed(shop_text(u),shop_kb(u,gid or 0));return

    if a.startswith("buy_"):
        pts=a.split("_",2);upg_id=pts[1];gb=int(pts[2]) if len(pts)>2 and pts[2].lstrip("-").isdigit() else 0
        upg=next((x for x in UPGRADES if x[0]==upg_id),None)
        if not upg:await q.answer("❌");return
        if upg_id in u.get("upg",[]):await q.answer("✅ Вже куплено!");return
        if u.get("coins",0)<upg[3]:await q.answer(f"❌ Потрібно {upg[3]:,}");return
        u["coins"]-=upg[3];u.setdefault("upg",[]).append(upg_id);on_buy_upg(u);check_ach(u);assign_quests(u);save(d)
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
        u["coins"]-=cost;u.setdefault("owned_skins",["default"]).append(sid);u["skin"]=sid
        on_buy_skin(u);check_ach(u);assign_quests(u);save(d)
        await q.answer(f"✅ {SKINS[sid][0]} одягнено!")
        await ed(skins_text(u),skins_kb(u,gb));return

    if a.startswith("seq_"):
        pts=a.split("_",2);sid=pts[1];gb=int(pts[2]) if pts[2].lstrip("-").isdigit() else 0
        if sid not in u.get("owned_skins",[]):await q.answer("❌");return
        u["skin"]=sid;save(d);await q.answer(f"✅ {SKINS[sid][0]} одягнено!")
        await ed(skins_text(u),skins_kb(u,gb));return

    if a=="quests":
        assign_quests(u);save(d);await ed(quests_text(u),InlineKeyboardMarkup([[btn("↩ Назад",f"back_{gid or 0}")]]));return

    if a=="ach":
        txt="🎖 *Досягнення*\n\n"
        for ac in ACHIEVEMENTS:
            earned=ac[0] in u.get("ach",[])
            req=f"{ac[2]:,} тапів" if ac[2] else (f"{ac[3]}д стріку" if ac[3] else ("1M монет" if ac[0]=="rich" else ("5 скінів" if ac[0]=="skins5" else "всі апгрейди")))
            txt+=f"{'✅' if earned else '🔒'} *{ac[1]}*  {req}\n"
        save(d);await ed(txt,InlineKeyboardMarkup([[btn("↩ Назад",f"back_{gid or 0}")]]));return

    if a.startswith("ga_join_"):
        ga_id=a[8:];d2=load()
        ga=next((g for g in d2.get("giveaways",[]) if g["id"]==ga_id),None)
        if not ga or ga.get("ended"):await q.answer("❌ Розіграш завершено");return
        if str(tg.id) in ga.get("participants",[]):await q.answer("✅ Вже в розіграші!");return
        ga.setdefault("participants",[]).append(str(tg.id))
        wu=gu(d2,tg.id);wu["name"]=tg.first_name or "?";wu["uname"]=tg.username
        save(d2);cnt=len(ga["participants"]);await q.answer(f"✅ Ти в розіграші! Учасників: {cnt}")
        try:await q.edit_message_reply_markup(InlineKeyboardMarkup([[btn(f"🎉 Взяти участь ({cnt})",f"ga_join_{ga_id}")]]))
        except:pass
        return

    if not is_dev(tg):save(d);return

    if a=="dev":
        users=d.get("users",{});groups=d.get("groups",{})
        active=sum(1 for u2 in users.values() if u2.get("tap_date")==today_k())
        await ed(
            f"⚙️ *Панель розробника*\n\n👥 {len(users)} юзерів  💬 {len(groups)} груп  🔥 {active} активних",
            InlineKeyboardMarkup([
                [btn("📢 Розсилка","dv_bc"),btn("📣 Анонс","dv_ann")],
                [btn("🎁 Розіграш","dv_ga"),btn("🎰 Подія ×2","dv_x2")],
                [btn("👥 Юзери","dv_users"),btn("📊 Стата","dv_stats")],
                [btn("💬 Чати","dv_chats"),btn("🔍 Юзер","dv_lookup")],
                [btn("💰 Монети","dv_gc"),btn("👆 Тапи","dv_gt")],
                [btn("🎨 Скін","dv_gs"),btn("💎 VIP 30д","dv_vip")],
                [btn("🔨 Бан","dv_ban"),btn("🔄 Скинути","dv_reset")],
                [btn("🦎 Грати","play")],
            ]));return

    if a=="dv_users":
        users=d.get("users",{})
        rows=[]
        for uid,u2 in list(users.items())[:15]:
            un=f"@{u2.get('uname')}" if u2.get("uname") else f"id{uid}"
            flags=("💎" if is_vip(u2) else "")+("🔨" if u2.get("banned") else "")
            rows.append(f"{un} {flags}  👆{u2.get('taps',0):,}  💰{u2.get('coins',0):,}  🌐{u2.get('lang','?') or '?'}")
        txt=f"👥 *Юзери: {len(users)}*\n\n"+"\n".join(rows)
        if len(users)>15:txt+=f"\n\n+{len(users)-15} ще"
        await ed(txt,InlineKeyboardMarkup([[btn("↩ Назад","dev")]]));return

    if a=="dv_stats":
        users=d.get("users",{});groups=d.get("groups",{})
        active=sum(1 for u2 in users.values() if u2.get("tap_date")==today_k())
        tt=sum(u2.get("taps",0) for u2 in users.values())
        tc=sum(u2.get("coins",0) for u2 in users.values())
        vips=sum(1 for u2 in users.values() if is_vip(u2))
        bans=sum(1 for u2 in users.values() if u2.get("banned"))
        x2st="Активна ✅" if is_x2(d) else "Вимкнена"
        txt=(f"📊 *Статистика*\n\n"
             f"👥 Юзерів: *{len(users)}*\n💬 Груп: *{len(groups)}*\n"
             f"🔥 Активних сьогодні: *{active}*\n💎 VIP: *{vips}*\n🔨 Банів: *{bans}*\n"
             f"👆 Тапів всього: *{tt:,}*\n💰 Монет всього: *{tc:,}*\n🎰 Подія ×2: {x2st}")
        await ed(txt,InlineKeyboardMarkup([[btn("↩ Назад","dev")]]));return

    if a=="dv_chats":
        groups=d.get("groups",{});txt=f"💬 *Чати: {len(groups)}*\n\n"
        for gs,g in list(groups.items())[:20]:
            txt+=f"`{gs}`  *{g.get('title','?')}*  👥{len(g.get('members',[]))}\n"
        await ed(txt,InlineKeyboardMarkup([[btn("↩ Назад","dev")]]));return

    def sa(action):ctx.user_data["dev_action"]=action

    if a=="dv_bc":
        await ed("📢 Розсилка — куди?",InlineKeyboardMarkup([
            [btn("Всі чати","dv_bc_all")],[btn("Один чат по ID","dv_bc_one")],[btn("❌ Назад","dev")]
        ]));return
    if a=="dv_bc_all":sa("broadcast_all");await ed("📢 *Розсилка в усі чати*\n\nВідправ текст:",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_bc_one":sa("broadcast_one");await ed("📢 *Один чат*\n\nФормат: `chat_id текст`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_ann":sa("announce");await ed("📣 *Анонс*\n\nВідправ текст:",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_gc":sa("give_coins");await ed("💰 *Монети*\n\n`@юзер 1000`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_gt":sa("give_taps");await ed("👆 *Тапи*\n\n`@юзер 1000`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_gs":sa("give_skin");await ed("🎨 *Скін*\n\n`@юзер fire`\n\nСкіни: "+", ".join(f"`{s}`" for s in SKINS if s!="default"),InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_vip":sa("toggle_vip");await ed(f"💎 *VIP на {VIP_DAYS} днів*\n\n`@юзер`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_ban":sa("toggle_ban");await ed("🔨 *Бан/Розбан*\n\n`@юзер`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_reset":sa("reset_user");await ed("🔄 *Скинути*\n\n`@юзер all|coins|taps|streak|skin`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return
    if a=="dv_lookup":sa("lookup");await ed("🔍 *Пошук юзера*\n\n`@юзер` або `user_id`",InlineKeyboardMarkup([[btn("❌ Скасувати","dev")]]));return

    if a=="dv_x2":
        await ed("🎰 *Подія ×2*",InlineKeyboardMarkup([
            [btn("5хв","x2_5m"),btn("15хв","x2_15m"),btn("30хв","x2_30m")],
            [btn("1год","x2_1h"),btn("2год","x2_2h"),btn("6год","x2_6h")],
            [btn("1день","x2_1d"),btn("❌ Вимкнути","x2_off")],[btn("↩ Назад","dev")],
        ]));return

    if a.startswith("x2_"):
        val=a[3:]
        if val=="off":d["x2_until"]=None;save(d);await ed("✅ Подія ×2 вимкнена",InlineKeyboardMarkup([[btn("↩ Назад","dev")]]));return
        secs=parse_dur(val);d["x2_until"]=(datetime.now(KYIV)+timedelta(seconds=secs)).isoformat();save(d)
        groups_d=d.get("groups",{})
        for gs in groups_d:
            try:await ctx.bot.send_message(int(gs),f"🎰 *ПОДІЯ ×2!*\n\nНаступні {fmt_dur(secs)} всі тапи ×2!\nПиши `.тап`!",parse_mode=ParseMode.MARKDOWN)
            except:pass
        await ed(f"✅ Подія ×2 на {fmt_dur(secs)}!",InlineKeyboardMarkup([[btn("↩ Назад","dev")]]))
        return

    if a=="dv_ga":
        await ed("🎁 *Розіграш*\n\nОбери призи (можна кілька):",InlineKeyboardMarkup([
            [btn("💰 Монети","ga_t_coins"),btn("👆 Тапи","ga_t_taps")],
            [btn("🎨 Скін","ga_t_skin"),btn("💎 VIP","ga_t_vip")],
            [btn("↩ Назад","dev")],
        ]));return

    if a in("ga_t_coins","ga_t_taps","ga_t_skin","ga_t_vip"):
        t=a[5:];ctx.user_data["ga_type"]=t
        tips={"coins":"`10s 5000` — 10 секунд, 5000 монет\n`30min 10000` — 30 хвилин\n`2h 50000` — 2 години","taps":"`5min 3000` — 5 хвилин, 3000 тапів","skin":f"`30s dragon`\nСкіни: {', '.join(f'`{s}`' for s in SKINS if s!='default')}","vip":"`1h` — 1 година"}
        ctx.user_data["dev_action"]="giveaway"
        await ed(f"🎁 Розіграш\n\nФормат: `час приз`\nЧас: `30s` `10min` `2h` `1day`\n\n{tips.get(t,'')}",InlineKeyboardMarkup([[btn("❌ Назад","dv_ga")]]))
        return

    save(d)

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
        pts=text.split(" ",1)
        try:
            chat_id=int(pts[0]);msg=pts[1] if len(pts)>1 else ""
            await ctx.bot.send_message(chat_id,f"📢 {msg}",parse_mode=ParseMode.MARKDOWN)
            await update.message.reply_text("✅ Відправлено")
        except Exception as e:await update.message.reply_text(f"❌ {e}")
        return

    if action=="announce":
        groups=d.get("groups",{});sent=0
        for gs in groups:
            try:await ctx.bot.send_message(int(gs),f"📣 *Оголошення*\n\n{text}",parse_mode=ParseMode.MARKDOWN);sent+=1
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
        u2["skin"]=sid;save(d);await update.message.reply_text(f"✅ {SKINS[sid][0]} → {ref}");return

    if action=="toggle_vip":
        uid,u2=find(text.strip())
        if not u2:await update.message.reply_text("❌ Не знайдений");return
        if is_vip(u2):
            u2["vip"]=None;save(d);await update.message.reply_text(f"✅ VIP знято з {text.strip()}")
        else:
            u2["vip"]=(datetime.now(KYIV)+timedelta(days=VIP_DAYS)).isoformat()
            save(d);await update.message.reply_text(f"✅ VIP на {VIP_DAYS}д → {text.strip()}")
        return

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
            u2.update({"taps":0,"coins":0,"upg":[],"ach":[],"streak":0,"hist":{},"tap_date":None,"bonus_date":None,"skin":"default","owned_skins":["default"],"vip":None,"banned":False,"quests":{},"active_quests":[],"jackpots":0})
        elif what=="coins":u2["coins"]=0
        elif what=="taps":u2["taps"]=0;u2["hist"]={}
        elif what=="streak":u2["streak"]=0
        elif what=="skin":u2["skin"]="default";u2["owned_skins"]=["default"]
        save(d);await update.message.reply_text(f"✅ {ref}: [{what}] скинуто");return

    if action=="lookup":
        uid,u2=find(text.strip())
        if not u2:await update.message.reply_text("❌ Не знайдений");return
        sn=SKINS.get(u2.get("skin","default"),("","?"))[1]
        vip_info=f"Так ({vip_days_left(u2)}д)" if is_vip(u2) else "Ні"
        txt=(f"🔍 *{u2.get('name','?')}*\n\n"
             f"ID: `{uid}`\n@{u2.get('uname') or '—'}\nМова: {u2.get('lang') or '?'}\n"
             f"👆 {u2.get('taps',0):,}  💰 {u2.get('coins',0):,}\n"
             f"🔥 Стрік {u2.get('streak',0)}д  🎖 {len(u2.get('ach',[]))}/{len(ACHIEVEMENTS)}\n"
             f"🎨 {sn}  💎 VIP: {vip_info}\n🔨 Бан: {'Так' if u2.get('banned') else 'Ні'}\n"
             f"📋 Квестів: {len(u2.get('quests',{}))}  🎰 Джекпоти: {u2.get('jackpots',0)}")
        await update.message.reply_text(txt,parse_mode=ParseMode.MARKDOWN);return

    if action=="giveaway":
        ga_type=ctx.user_data.pop("ga_type","coins")
        pts=text.strip().split(" ",1);time_str=pts[0];val=pts[1].strip() if len(pts)>1 else ""
        secs=parse_dur(time_str)
        ga_id=f"ga_{int(datetime.now().timestamp())}"

        prizes=[]
        prize_labels=[]
        if ga_type=="coins" and val:
            n=int(val) if val.isdigit() else 0
            prizes.append(("coins",n));prize_labels.append(f"💰 {n:,} монет")
        elif ga_type=="taps" and val:
            n=int(val) if val.isdigit() else 0
            prizes.append(("taps",n));prize_labels.append(f"👆 {n:,} тапів")
        elif ga_type=="skin":
            prizes.append(("skin",val));prize_labels.append(f"{SKINS.get(val,('🎨','?'))[0]} {SKINS.get(val,('🎨','?'))[1]}")
        elif ga_type=="vip":
            prizes.append(("vip",""));prize_labels.append("💎 VIP 30д")

        prize_txt=" + ".join(prize_labels) or "🎁 Приз"
        ga={"id":ga_id,"prizes":prizes,"participants":[],"ended":False}
        d.setdefault("giveaways",[]).append(ga)
        time_txt=fmt_dur(secs)
        ga_text=f"🎁 *РОЗІГРАШ!*\n\nПриз: *{prize_txt}*\nЧас: *{time_txt}*\n\nНатисни кнопку!"
        ga_kb=InlineKeyboardMarkup([[btn("🎉 Взяти участь (0)",f"ga_join_{ga_id}")]])
        groups=d.get("groups",{});save(d);sent_msgs=[]
        for gs in groups:
            try:
                msg=await ctx.bot.send_message(int(gs),ga_text,parse_mode=ParseMode.MARKDOWN,reply_markup=ga_kb)
                sent_msgs.append((int(gs),msg.message_id))
            except:pass
        await update.message.reply_text(f"✅ Розіграш в {len(sent_msgs)} чатах, {time_txt}")

        async def end_ga():
            await asyncio.sleep(secs)
            d2=load();ga2=next((g for g in d2.get("giveaways",[]) if g["id"]==ga_id),None)
            if not ga2 or ga2.get("ended"):return
            ga2["ended"]=True;participants=ga2.get("participants",[])
            if not participants:
                res="🎁 *Розіграш завершено*\n\nНіхто не взяв участь 😔"
            else:
                wid=random.choice(participants);wu2=gu(d2,wid)
                wn=f"@{wu2['uname']}" if wu2.get("uname") else wu2.get("name","?")
                for ptype,pval in ga2.get("prizes",[]):
                    if ptype=="coins" and pval:wu2["coins"]=wu2.get("coins",0)+int(pval)
                    elif ptype=="taps" and pval:wu2["taps"]=wu2.get("taps",0)+int(pval)
                    elif ptype=="skin" and pval in SKINS:
                        wu2.setdefault("owned_skins",["default"])
                        if pval not in wu2["owned_skins"]:wu2["owned_skins"].append(pval)
                    elif ptype=="vip":wu2["vip"]=(datetime.now(KYIV)+timedelta(days=VIP_DAYS)).isoformat()
                res=f"🎁 *Розіграш завершено!*\n\n🏆 Переможець: *{wn}*\n🎉 Приз: *{prize_txt}*\nУчасників: {len(participants)}"
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
