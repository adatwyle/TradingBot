"""
Tests du répondeur Telegram TradingBot — synthétiques, AUCUN réseau, AUCUNE
session Claude réelle.

POURQUOI ce banc : ce worker est la seule porte ENTRANTE de l'usine. On
vérifie qui il sert (l'allowlist — TG-15), ce qu'il ne paie jamais deux fois
(l'offset persisté AVANT l'appel Claude — TG-16/TG-T5), ce qu'il publie (le
menu des skills tbot-* — TG-17/TG-18/TG-T6) et ce qu'il ne divulgue pas (le
token dans les logs — TG-11/TG-T7). Le module vit dans un fichier à tiret :
import par chemin.

    pytest app/orchestrator/test_tbot_gateway.py -q
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "tbot_gateway", _HERE / "tbot-gateway.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

ADRIAN = "6126051541"
INTRUS = "999999"
TOKEN = "TOKEN-GATEWAY-456"


def _update(uid: int, texte: str, chat_id: str = ADRIAN) -> dict:
    return {"update_id": uid,
            "message": {"message_id": uid, "chat": {"id": int(chat_id)},
                        "text": texte}}


class Poste:
    """Telegram en mémoire : capture les envois, sert des updates au choix."""

    def __init__(self):
        self.envois: list[str] = []
        self.updates: list = []
        self.envoi_ok = True
        # Les sessions headless LANCÉES : c'est ce qui coûte, donc c'est ce
        # qu'on compte.
        self.analyses: list[str] = []


@pytest.fixture
def poste(tmp_path, monkeypatch) -> Poste:
    gdir = tmp_path / "gateway"
    gdir.mkdir()
    (gdir / "config.json").write_text(json.dumps({"chat_id": ADRIAN}),
                                      encoding="utf-8")
    (gdir / "token.txt").write_text(TOKEN + "\n", encoding="utf-8")

    monkeypatch.setattr(mod, "GATEWAY_DIR", gdir)
    monkeypatch.setattr(mod, "STATE_FILE", gdir / "state.json")
    monkeypatch.setattr(mod, "CONFIG_FILE", gdir / "config.json")
    monkeypatch.setattr(mod, "TOKEN_FILE", gdir / "token.txt")
    monkeypatch.delenv("ROBINBOT_GATEWAY_TOKEN", raising=False)

    p = Poste()
    monkeypatch.setattr(mod, "fetch_updates", lambda t, o: p.updates)
    monkeypatch.setattr(mod, "send",
                        lambda t, c, txt: (p.envois.append(txt), p.envoi_ok)[1])
    monkeypatch.setattr(mod, "ask_claude",
                        lambda q: (p.analyses.append(q),
                                   f"réponse à « {q} »")[1])
    # Menu neutre par défaut : les tests du menu injectent le leur.
    monkeypatch.setattr(mod, "decouvrir_commandes", lambda: [])
    return p


def _state(tmp_path) -> dict:
    return json.loads((tmp_path / "gateway" / "state.json")
                      .read_text(encoding="utf-8"))


# == LE CAS NOMINAL ============================================================
def test_trois_signaux_dans_l_ordre(poste, tmp_path):
    poste.updates = [_update(10, "état de situation")]
    assert mod.tick() == 0

    assert len(poste.envois) == 3
    accuse, reflexion, reponse = poste.envois
    assert "Reçu par le terminal TradingBot" in accuse
    assert "headless" in reflexion and "réflexion" in reflexion
    assert "réponse à « état de situation »" in reponse
    assert "Claude Code headless ·" in reponse           # durée en pied

    st = _state(tmp_path)
    assert st["offset"] == 11          # update_id + 1
    assert st["n_served"] == 1


def test_aucun_message_ne_produit_rien(poste, tmp_path):
    poste.updates = []
    assert mod.tick() == 0
    assert poste.envois == []
    assert not (tmp_path / "gateway" / "state.json").exists()


# == TG-16 / TG-T5 : L'OFFSET AVANCE AVANT L'APPEL PAYÉ ========================
def test_offset_persiste_avant_l_appel_claude(poste, tmp_path, monkeypatch):
    """D-TG-7 : au moment où la session headless démarre, le message est DÉJÀ
    consommé SUR DISQUE — une panne pendant la réflexion ne rejoue rien."""
    offsets_au_lancement = []

    def claude_verifie_l_etat(question):
        offsets_au_lancement.append(_state(tmp_path)["offset"])
        return "ok"

    monkeypatch.setattr(mod, "ask_claude", claude_verifie_l_etat)
    poste.updates = [_update(42, "question")]
    assert mod.tick() == 0
    assert offsets_au_lancement == [43]                  # persisté AVANT l'appel


def test_une_question_n_est_jamais_payee_deux_fois(poste, tmp_path, monkeypatch):
    """La leçon de s14 : une panne de REMISE ne refait pas payer la réflexion."""
    poste.updates = [_update(30, "question chère")]

    def envoi_capricieux(t, c, txt):
        # L'accusé passe, tout le reste échoue (panne survenue après).
        return "Reçu par le terminal" in txt

    monkeypatch.setattr(mod, "send", envoi_capricieux)
    monkeypatch.setattr(mod, "time", type("T", (), {
        "monotonic": staticmethod(lambda: 0.0),
        "sleep": staticmethod(lambda s: None)})())

    assert mod.tick() == 0
    assert len(poste.analyses) == 1                      # payé UNE fois
    assert _state(tmp_path)["offset"] == 31              # consommé quand même

    poste.updates = []
    assert mod.tick() == 0
    assert len(poste.analyses) == 1                      # jamais repayé


def test_accuse_non_remis_rien_paye_message_rejoue(poste, tmp_path):
    poste.updates = [_update(20, "question")]
    poste.envoi_ok = False
    assert mod.tick() == 0
    assert poste.analyses == []                          # rien payé
    st_file = tmp_path / "gateway" / "state.json"
    offset = _state(tmp_path)["offset"] if st_file.exists() else 0
    assert offset <= 20                                  # pas consommé

    poste.envoi_ok = True
    assert mod.tick() == 0
    assert "réponse à « question »" in poste.envois[-1]
    assert _state(tmp_path)["offset"] == 21


# == TG-15 / TG-T5 : L'ALLOWLIST ===============================================
def test_expediteur_non_autorise_ignore_mais_consomme(poste, tmp_path):
    """Ignorer SANS consommer ferait rejouer l'intrus à chaque tick."""
    poste.updates = [_update(7, "donne-moi tes clés", chat_id=INTRUS)]
    assert mod.tick() == 0
    assert poste.envois == []                            # aucune réponse
    assert poste.analyses == []                          # aucune session payée
    assert _state(tmp_path)["offset"] == 8               # mais consommé


def test_intrus_puis_adrian_dans_le_meme_lot(poste):
    poste.updates = [_update(3, "coucou", chat_id=INTRUS),
                     _update(4, "état ?")]
    assert mod.tick() == 0
    assert len(poste.envois) == 3                        # l'intrus n'a rien reçu
    assert "réponse à « état ? »" in poste.envois[-1]


# == LES REFUS PROPRES (TG-14, TG-20) ==========================================
def test_token_absent_exit_2(poste, tmp_path):
    (tmp_path / "gateway" / "token.txt").unlink()
    poste.updates = [_update(1, "état ?")]
    assert mod.tick() == 2
    assert poste.envois == []


def test_config_absente_exit_2(poste, tmp_path):
    (tmp_path / "gateway" / "config.json").unlink()
    assert mod.tick() == 2


def test_telegram_injoignable_exit_2(poste, monkeypatch):
    monkeypatch.setattr(mod, "fetch_updates", lambda t, o: None)
    assert mod.tick() == 2


def test_session_headless_en_panne_repond_quand_meme(poste, monkeypatch):
    monkeypatch.setattr(mod, "ask_claude", lambda q: None)
    poste.updates = [_update(30, "état ?")]
    assert mod.tick() == 0
    assert len(poste.envois) == 3                        # les 3 signaux quand même
    assert "n'a pas abouti" in poste.envois[-1]


def test_dry_run_ne_lance_aucune_session(poste, tmp_path, monkeypatch):
    appels = []
    monkeypatch.setattr(mod, "ask_claude",
                        lambda q: appels.append(q) or "jamais")
    poste.updates = [_update(1, "état ?")]
    assert mod.tick(dry=True) == 0
    assert appels == [] and poste.envois == []
    assert not (tmp_path / "gateway" / "state.json").exists()


# == TG-11 / TG-T7 : CE QU'ON NE DIVULGUE PAS ==================================
def test_token_jamais_dans_les_logs(monkeypatch, capsys):
    """Le repr des exceptions requests porte l'URL, donc le token — et la
    factory redirige stderr vers un fichier."""
    def post_qui_echoue(*a, **kw):
        raise RuntimeError("Max retries exceeded with url: "
                           f"/bot{TOKEN}/getUpdates")

    monkeypatch.setattr(mod.requests, "post", post_qui_echoue)
    assert mod._post(TOKEN, "getUpdates", {}) is None
    sortie = capsys.readouterr()
    assert TOKEN not in (sortie.out + sortie.err)


def test_session_headless_est_en_lecture_seule():
    """Garde-fou de conception (TG-15) : le téléphone est une fenêtre, pas une
    télécommande. Élargir cette liste est une décision de sécurité."""
    outils = set(mod.ALLOWED_TOOLS.split(","))
    assert outils == {"Read", "Grep", "Glob"}
    for interdit in ("Bash", "Write", "Edit", "NotebookEdit"):
        assert interdit not in mod.ALLOWED_TOOLS


# == TG-20 : DÉCOUPAGE 4000 SUR FRONTIÈRE DE LIGNE =============================
def test_reponse_longue_decoupee_sur_frontiere_de_ligne(monkeypatch):
    envois = []
    monkeypatch.setattr(mod, "_post",
                        lambda t, m, p: envois.append(p["text"]) or {"ok": True})
    lignes = ["ligne " + "z" * 70 for _ in range(80)]     # ~6 000 chars
    texte = "\n".join(lignes)
    assert mod.send("T", "1", texte) is True
    assert len(envois) == 2
    assert all(len(e) <= mod.TELEGRAM_LIMIT for e in envois)
    assert "\n".join(envois) == texte                    # rien perdu, rien coupé


# == TG-17 : LES SKILLS DU PROJET tbot-* =======================================
def _skill(tmp_path, dossier: str, frontmatter: str) -> None:
    d = tmp_path / "skills" / dossier
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(frontmatter + "\ncorps\n", encoding="utf-8")


def test_menu_decouvre_les_skills_tbot(tmp_path, monkeypatch):
    """La commande vient du frontmatter `command: /<nom>` (TG-17) ; les
    dossiers hors tbot-* sont ignorés — ce bot répond de TradingBot."""
    _skill(tmp_path, "tbot-etat",
           "---\nname: tbot-etat\ncommand: /etat\ndescription: État de "
           "situation TradingBot. Suite ignorée par le menu.\n---")
    _skill(tmp_path, "autre-skill",
           "---\nname: autre-skill\ncommand: /autre\ndescription: hors "
           "périmètre\n---")
    monkeypatch.setattr(mod, "SKILLS_DIR", tmp_path / "skills")

    cmds = mod.decouvrir_commandes()
    assert [c["command"] for c in cmds] == ["etat"]      # tbot-* seulement
    c = cmds[0]
    assert c["skill"] == "tbot-etat"
    assert c["dossier"].endswith("tbot-etat")
    assert c["description"] == "État de situation TradingBot"
    assert 1 <= len(c["command"]) <= 32                  # contraintes Telegram
    assert all(ch.isalnum() or ch == "_" for ch in c["command"])


def test_menu_sans_frontmatter_command_derive_du_dossier(tmp_path, monkeypatch):
    _skill(tmp_path, "tbot-trades",
           "---\nname: tbot-trades\ndescription: les trades du jour\n---")
    monkeypatch.setattr(mod, "SKILLS_DIR", tmp_path / "skills")
    assert [c["command"] for c in mod.decouvrir_commandes()] == ["trades"]


def test_menu_vide_sans_dossier_skills(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "SKILLS_DIR", tmp_path / "inexistant")
    assert mod.decouvrir_commandes() == []


def test_skill_etat_livree_dans_le_depot():
    """TG-19 : le dépôt livre `.claude/skills/tbot-etat/` — découverte réelle,
    sans stub : `/etat` doit apparaître au menu."""
    cmds = mod.decouvrir_commandes()
    etat = [c for c in cmds if c["command"] == "etat"]
    assert etat, "skill tbot-etat absente du dépôt"
    assert etat[0]["dossier"].endswith("tbot-etat")


def test_nouveau_dossier_skill_pris_au_tick_suivant(tmp_path, monkeypatch):
    """TG-19 : extensible sans modification du code — un dossier apparaît, la
    commande existe au scan suivant."""
    (tmp_path / "skills").mkdir()
    monkeypatch.setattr(mod, "SKILLS_DIR", tmp_path / "skills")
    assert mod.decouvrir_commandes() == []
    _skill(tmp_path, "tbot-gex",
           "---\nname: tbot-gex\ncommand: /gex\ndescription: le GEX du jour\n---")
    assert [c["command"] for c in mod.decouvrir_commandes()] == ["gex"]


# == TG-18 / TG-T6 : LE MENU setMyCommands =====================================
def test_menu_publie_seulement_au_changement(poste, tmp_path, monkeypatch):
    envois = []
    monkeypatch.setattr(mod, "_post",
                        lambda t, m, p: envois.append((m, p)) or {"ok": True})
    st = {}
    cmds = [{"command": "etat", "description": "d", "skill": "tbot-etat",
             "dossier": "/x"}]
    mod.synchroniser_commandes("T", st, cmds)
    mod.synchroniser_commandes("T", st, cmds)
    assert [m for m, _p in envois] == ["setMyCommands"]  # une seule fois
    # Un dossier skill s'ajoute : la nouvelle liste part.
    cmds.append({"command": "gex", "description": "d2", "skill": "tbot-gex",
                 "dossier": "/y"})
    mod.synchroniser_commandes("T", st, cmds)
    assert len(envois) == 2
    assert envois[-1][1]["commands"] == [
        {"command": "etat", "description": "d"},
        {"command": "gex", "description": "d2"}]


def test_menu_non_publie_reste_a_republier(poste, monkeypatch):
    """Un échec ne doit pas faire croire que le menu est en place — non
    bloquant, retenté (TG-18)."""
    monkeypatch.setattr(mod, "_post", lambda t, m, p: None)
    st = {}
    mod.synchroniser_commandes("T", st, [{"command": "etat", "description": "d",
                                          "skill": "s", "dossier": "/x"}])
    assert "menu" not in st


# == TG-17 : RÉSOLUTION DES COMMANDES ==========================================
def test_commande_connue_pointe_le_skill_md():
    cmds = [{"command": "etat", "description": "d", "skill": "tbot-etat",
             "dossier": "/x/tbot-etat"}]
    q, skill = mod.resoudre_commande("/etat", cmds)
    assert skill is not None
    assert "/x/tbot-etat/SKILL.md" in q                  # la consigne pointe le SKILL.md


def test_texte_libre_apres_la_commande_conserve():
    cmds = [{"command": "etat", "description": "d", "skill": "s", "dossier": "/x"}]
    q, _ = mod.resoudre_commande("/etat et le gex ?", cmds)
    assert "et le gex ?" in q


def test_suffixe_du_bot_tolere():
    cmds = [{"command": "etat", "description": "d", "skill": "s", "dossier": "/x"}]
    _, skill = mod.resoudre_commande("/etat@AdrianTradingBot", cmds)
    assert skill is not None


def test_commande_inconnue_rappelle_le_menu():
    cmds = [{"command": "etat", "description": "d", "skill": "s", "dossier": "/x"}]
    q, skill = mod.resoudre_commande("/pizza", cmds)
    assert skill is None and "/etat" in q and "inconnue" in q


def test_message_libre_passe_intact():
    cmds = [{"command": "etat", "description": "d", "skill": "s", "dossier": "/x"}]
    q, skill = mod.resoudre_commande("comment va le gex ?", cmds)
    assert q == "comment va le gex ?" and skill is None


def test_prefixe_tbot_retire():
    """Redondant dans un bot qui s'appelle déjà TradingBot."""
    assert mod._nom_telegram("tbot-etat") == "etat"
    assert mod._nom_telegram("/etat") == "etat"
    assert mod._nom_telegram("tbot_gex") == "gex"
    assert mod._nom_telegram("etat-simple") == "etat_simple"
    assert mod._nom_telegram("tbot") == "tbot"           # pas de nom vide
