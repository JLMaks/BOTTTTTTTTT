"""
République RP — Bot Discord
Commandes : /creer /profil /fiche /liste /classement /supprimer
"""

import os, secrets
import discord
from discord import option
from discord.ext import commands
from dotenv import load_dotenv
import database as db

load_dotenv()

TOKEN   = os.environ["DISCORD_TOKEN"]
WEB_URL = os.environ.get("WEB_URL", "http://localhost:5000")

# ── CONSTANTES ───────────────────────────────────────────────────
GOLD = 0xC9A84C; RED = 0x8B1A1A; BLUE = 0x1A2E5A; DARK = 0x0D0D0D

PARTY_DATA = {
    "none":         ("⚖️",  "Indépendant",                        0x888888),
    "far-left":     ("🔴", "Front Révolutionnaire",               0xCC2200),
    "left":         ("🌹", "Parti Socialiste Uni",                0xCC4477),
    "green":        ("🌿", "Mouvement Écologiste",                0x2A8A2A),
    "center-left":  ("🕊️",  "Alliance Progressiste",              0x4488CC),
    "center":       ("⚖️",  "Parti du Centre",                    0xC9A84C),
    "center-right": ("🏛️", "Union Républicaine",                  0x6688AA),
    "right":        ("🦅", "Rassemblement National-Conservateur", 0x4466AA),
    "far-right":    ("⚔️", "Mouvement Souverainiste",             0x225588),
    "liberal":      ("💼", "Parti Libéral",                       0xC9A84C),
    "custom":       ("✦",  "Parti Personnalisé",                  0xC9A84C),
}

STATS_LABELS = {
    "charisma":"Charisme","rhetoric":"Rhétorique","strategy":"Stratégie",
    "diplomacy":"Diplomatie","integrity":"Intégrité","influence":"Influence",
}

IDEOLOGY_LABELS = [
    (0,15,"Communiste"),(16,30,"Gauche Radicale"),(31,42,"Gauche"),
    (43,57,"Centre"),(58,69,"Droite"),(70,84,"Droite Conservatrice"),(85,100,"Nationaliste"),
]

def ideo_label(v): return next((l for lo,hi,l in IDEOLOGY_LABELS if lo<=v<=hi),"Centre")
def stat_bar(v, mx=10): f=round(v/mx*8); return "█"*f+"░"*(8-f)

# ── EMBED PERSONNAGE ─────────────────────────────────────────────
def char_embed(char):
    pk = char.get("party","none")
    icon, pname_def, color = PARTY_DATA.get(pk, PARTY_DATA["none"])
    pname = char.get("party_name") or pname_def
    if pk == "custom" and char.get("party_name"): pname = char["party_name"]
    iv = char.get("ideology",50)
    il = ideo_label(iv)
    ibar = "◀ " + "░"*(iv//10) + "▮" + "░"*(10-iv//10) + " ▶"

    em = discord.Embed(
        title=f"⚜  {char.get('name','???')}",
        description=f"*{char.get('title','')}*",
        color=color,
    )
    em.add_field(name=f"{icon}  Parti", value=pname, inline=True)
    em.add_field(name="📍  Région", value=char.get("region") or "—", inline=True)
    em.add_field(name="🎂  Âge", value=char.get("age") or "—", inline=True)
    bio = char.get("bio","")
    if bio:
        em.add_field(name="📜  Biographie", value=f"*{bio[:300]}{'…' if len(bio)>300 else ''}*", inline=False)
    em.add_field(name=f"⚖️  Idéologie — {il}", value=f"```{ibar}```", inline=False)
    stats = char.get("stats",{})
    sl = "\n".join(
        f"`{STATS_LABELS.get(k,k):<12}` {stat_bar(v)}  **{v}**/10"
        for k,v in stats.items() if k in STATS_LABELS
    )
    if sl: em.add_field(name="📊  Compétences", value=sl, inline=False)
    em.set_footer(text="République RP  •  Système de personnage politique")
    return em

# ── BOT ──────────────────────────────────────────────────────────
intents = discord.Intents.default()
bot = discord.Bot(intents=intents)

@bot.event
async def on_ready():
    print(f"✅  {bot.user} connecté | {len(bot.guilds)} serveur(s)")

# ─── /creer ──────────────────────────────────────────────────────
@bot.slash_command(name="creer", description="🎨 Créer ou modifier votre personnage politique 3D")
async def creer(ctx):
    token = secrets.token_urlsafe(22)
    db.create_session(token, str(ctx.author.id), str(ctx.guild_id))
    link = f"{WEB_URL}/creer?token={token}"

    em = discord.Embed(
        title="⚜  Créateur de Personnage 3D",
        description=(
            "Ouvrez le lien ci-dessous pour accéder au **créateur de personnage 3D**.\n"
            "Personnalisez votre avatar, choisissez votre parti et définissez vos compétences."
        ),
        color=GOLD,
    )
    em.add_field(name="⏳  Validité du lien", value="30 minutes (usage unique recommandé)", inline=False)
    em.set_footer(text="République RP  •  Interface 3D exclusive")

    v = discord.ui.View()
    v.add_item(discord.ui.Button(label="🎨  Ouvrir le Créateur", url=link, style=discord.ButtonStyle.link))
    await ctx.respond(embed=em, view=v, ephemeral=True)

# ─── /profil ─────────────────────────────────────────────────────
@bot.slash_command(name="profil", description="👤 Afficher une fiche de personnage")
@option("utilisateur", discord.Member, description="Voir le profil d'un autre membre", required=False)
async def profil(ctx, utilisateur: discord.Member = None):
    target = utilisateur or ctx.author
    char = db.get_character_by_user(str(target.id), str(ctx.guild_id))
    if not char:
        em = discord.Embed(title="Personnage introuvable",
            description=f"**{target.display_name}** n'a pas de personnage.\nUtilisez `/creer` pour en créer un !",
            color=RED)
        await ctx.respond(embed=em, ephemeral=True); return

    em = char_embed(char)
    em.set_author(name=target.display_name, icon_url=target.display_avatar.url)
    v = discord.ui.View()
    if target.id == ctx.author.id:
        v.add_item(discord.ui.Button(label="✏️  Modifier", custom_id=f"edit_{target.id}", style=discord.ButtonStyle.secondary))
    await ctx.respond(embed=em, view=v)

# ─── /liste ──────────────────────────────────────────────────────
@bot.slash_command(name="liste", description="📋 Lister tous les personnages du serveur")
async def liste(ctx):
    chars = db.list_characters(str(ctx.guild_id))
    if not chars:
        em = discord.Embed(title="⚜  Registre vide",
            description="Aucun personnage n'a encore été créé.\nUtilisez `/creer` pour commencer !",
            color=GOLD)
        await ctx.respond(embed=em); return

    lines = []
    for c in chars[:25]:
        pk = c.get("party","none")
        icon = PARTY_DATA.get(pk, PARTY_DATA["none"])[0]
        lines.append(f"{icon}  **{c['name']}** — *{c.get('title','') or 'Sans titre'}*")

    em = discord.Embed(title=f"⚜  Registre des Personnages ({len(chars)})",
        description="\n".join(lines), color=GOLD)
    em.set_footer(text=f"République RP  •  {ctx.guild.name}")
    await ctx.respond(embed=em)

# ─── /fiche ──────────────────────────────────────────────────────
@bot.slash_command(name="fiche", description="📄 Générer la fiche texte Discord")
@option("utilisateur", discord.Member, required=False)
async def fiche(ctx, utilisateur: discord.Member = None):
    target = utilisateur or ctx.author
    char = db.get_character_by_user(str(target.id), str(ctx.guild_id))
    if not char:
        await ctx.respond("Aucun personnage trouvé. Utilisez `/creer` d'abord.", ephemeral=True); return

    pk = char.get("party","none")
    icon, pname_def, _ = PARTY_DATA.get(pk, PARTY_DATA["none"])
    pname = char.get("party_name") or pname_def
    iv = char.get("ideology",50)
    ibar = "░"*(iv//10)+"█"+"░"*(10-iv//10)
    stats = char.get("stats",{})
    sl = "\n".join(f"  {STATS_LABELS.get(k,k):<12} {'█'*v}{'░'*(10-v)} {v}/10" for k,v in stats.items() if k in STATS_LABELS)

    txt = (
        f"╔══════════════════════════════════════╗\n"
        f"║        FICHE DE PERSONNAGE — RP      ║\n"
        f"╚══════════════════════════════════════╝\n\n"
        f"👤 {char.get('name','???')}\n   {char.get('title','')}\n\n"
        f"{icon} {pname}\n\n"
        f"📍 {char.get('region','—')}  •  🎂 {char.get('age','—')}\n\n"
        f"───────────────────────────────────────\n📜 BIOGRAPHIE\n───────────────────────────────────────\n"
        f"{char.get('bio','')}\n\n"
        f"───────────────────────────────────────\n⚖️  IDÉOLOGIE — {ideo_label(iv)}\n"
        f"   GAUCHE {ibar} DROITE\n\n"
        f"───────────────────────────────────────\n📊 COMPÉTENCES\n───────────────────────────────────────\n"
        f"{sl}\n\n───────────────────────────────────────\n*Fiche générée — République RP*"
    )
    await ctx.respond(f"```\n{txt}\n```")

# ─── /classement ─────────────────────────────────────────────────
@bot.slash_command(name="classement", description="🏆 Classement des personnages par compétence")
@option("competence", str, required=False, choices=list(STATS_LABELS.values()))
async def classement(ctx, competence: str = "Charisme"):
    sk = next((k for k,v in STATS_LABELS.items() if v==competence), "charisma")
    chars = db.list_characters(str(ctx.guild_id))
    ranked = sorted(chars, key=lambda c: c.get("stats",{}).get(sk,0), reverse=True)
    medals = ["🥇","🥈","🥉"]
    lines = [f"{'🥇🥈🥉'[i] if i<3 else f'`{i+1}.`'}  **{c['name']}** — {stat_bar(c.get('stats',{}).get(sk,0))}  **{c.get('stats',{}).get(sk,0)}**/10"
             for i,c in enumerate(ranked[:10])]
    em = discord.Embed(title=f"🏆  Classement — {competence}",
        description="\n".join(lines) if lines else "Aucun personnage.", color=GOLD)
    em.set_footer(text="République RP")
    await ctx.respond(embed=em)

# ─── /supprimer ──────────────────────────────────────────────────
@bot.slash_command(name="supprimer", description="🗑️ Supprimer votre personnage")
async def supprimer(ctx):
    char = db.get_character_by_user(str(ctx.author.id), str(ctx.guild_id))
    if not char:
        await ctx.respond("Vous n'avez pas de personnage.", ephemeral=True); return

    class Confirm(discord.ui.View):
        @discord.ui.button(label="Confirmer la suppression", style=discord.ButtonStyle.danger, emoji="🗑️")
        async def yes(self, btn, inter):
            db.delete_character(str(ctx.author.id), str(ctx.guild_id))
            await inter.response.edit_message(content="✅ Personnage supprimé.", embed=None, view=None)
        @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
        async def no(self, btn, inter):
            await inter.response.edit_message(content="Annulé.", embed=None, view=None)

    em = discord.Embed(title="⚠️  Confirmer la suppression",
        description=f"Supprimer **{char['name']}** ? Action irréversible.", color=RED)
    await ctx.respond(embed=em, view=Confirm(), ephemeral=True)

# ─── Bouton Modifier ─────────────────────────────────────────────
@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        cid = interaction.data.get("custom_id","")
        if cid.startswith("edit_"):
            tid = cid.split("_")[1]
            if str(interaction.user.id) != tid:
                await interaction.response.send_message("Vous ne pouvez modifier que votre propre personnage.", ephemeral=True); return
            token = secrets.token_urlsafe(22)
            db.create_session(token, str(interaction.user.id), str(interaction.guild_id))
            link = f"{WEB_URL}/creer?token={token}"
            v = discord.ui.View()
            v.add_item(discord.ui.Button(label="✏️  Modifier mon personnage", url=link, style=discord.ButtonStyle.link))
            await interaction.response.send_message("Voici votre lien d'édition :", view=v, ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
