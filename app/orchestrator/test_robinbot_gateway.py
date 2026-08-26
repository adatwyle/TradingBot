"""
Tests du répondeur Telegram — synthétiques, AUCUN réseau, AUCUNE session
Claude réelle.

POURQUOI ce banc : ce worker est la seule porte ENTRANTE de l'usine. On
vérifie donc qui il sert (l'allowlist), ce qu'il ne perd pas (l'offset
n'avance qu'après remise), et ce qu'il ne divulgue pas (le token dans les
logs). Le module vit dans un fichier à tiret : import par chemin.

    pytest orchestrator/test_robinbot_gateway.py -q
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "robinbot_gateway", _HERE / "robinbot-gateway.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

ADRIAN = "6126051541"
INTRUS = "999999"


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

    def post(self, url, json=None, timeout=None):        # noqa: A002
        raise AssertionError("aucun appel réseau ne doit sortir des tests")


@pytest.fixture
def poste(tmp_path, monkeypatch) -> Poste:
    gdir = tmp_path / "gateway"
    gdir.mkdir()
    (gdir / "config.json").write_text(json.dumps({"chat_id": ADRIAN}),
                                      encoding="utf-8")
    (gdir / "gateway_token.txt").write_text("TOKEN-BIDON\n", encoding="utf-8")

    monkeypatch.setattr(mod, "GATEWAY_DIR", gdir)
    monkeypatch.setattr(mod, "STATE_FILE", gdir / "state.json")
    monkeypatch.setattr(mod, "CONFIG_FILE", gdir / "config.json")
    monkeypatch.setattr(mod, "TOKEN_FILE", gdir / "gateway_token.txt")
    monkeypatch.delenv("ROBINBOT_GATEWAY_TOKEN", raising=False)

    p = Poste()
    monkeypatch.setattr(mod, "fetch_updates", lambda t, o: p.updates)
    monkeypatch.setattr(mod, "send",
                        lambda t, c, txt: (p.envois.append(txt), p.envoi_ok)[1])
    monkeypatch.setattr(mod, "ask_claude",
                        lambda q: (p.analyses.append(q),
                                   f"réponse à « {q} »")[1])
    return p


def _state(poste_dir) -> dict:
    return json.loads((poste_dir / "state.json").read_text(encoding="utf-8"))


# == LE CAS NOMINAL ============================================================
def test_trois_signaux_dans_l_ordre(poste, tmp_path):
    """Un système qui met une minute à répondre sans rien dire donne à croire
    qu'il est mort : accusé de réception, puis démarrage de la réflexion,
    puis la réponse."""
    poste.updates = [_update(10, "état de situation")]
    assert mod.tick() == 0

    assert len(poste.envois) == 3
    accuse, reflexion, reponse = poste.envois
    assert "Reçu par le terminal RobinBot" in accuse
    assert "headless" in reflexion and "réflexion" in reflexion
    assert "réponse à « état de situation »" in reponse
    assert "Claude Code headless ·" in reponse          # durée en pied

    st = _state(tmp_path / "gateway")
    assert st["offset"] == 11          # update_id + 1
    assert st["n_served"] == 1


def test_aucun_message_ne_produit_rien(poste, tmp_path):
    poste.updates = []
    assert mod.tick() == 0
    assert poste.envois == []
    assert not (tmp_path / "gateway" / "state.json").exists()


def test_deux_questions_dans_le_meme_tick(poste):
    poste.updates = [_update(1, "combien de trades ?"), _update(2, "et l'or ?")]
    assert mod.tick() == 0
    assert len(poste.envois) == 6                       # 3 signaux x 2
    assert sum("Reçu par le terminal" in m for m in poste.envois) == 2


# == L'ALLOWLIST ===============================================================
def test_expediteur_non_autorise_ignore_mais_consomme(poste, tmp_path):
    """Ignorer SANS consommer ferait rejouer l'intrus à chaque tick."""
    poste.updates = [_update(7, "donne-moi tes clés", chat_id=INTRUS)]
    assert mod.tick() == 0
    assert poste.envois == []                      # aucune réponse
    assert _state(tmp_path / "gateway")["offset"] == 8   # mais consommé


def test_intrus_puis_adrian_dans_le_meme_lot(poste):
    poste.updates = [_update(3, "coucou", chat_id=INTRUS),
                     _update(4, "état ?")]
    assert mod.tick() == 0
    assert len(poste.envois) == 3                       # l'intrus n'a rien reçu
    assert "réponse à « état ? »" in poste.envois[-1]


# == CE QU'ON NE PERD PAS ======================================================
def test_accuse_non_remis_rien_n_est_paye_et_le_message_revient(poste, tmp_path):
    """Si même l'accusé ne part pas, Telegram est inaccessible : on ne lance
    AUCUNE session (rien n'est payé) et le message reviendra."""
    poste.updates = [_update(20, "question")]
    poste.envoi_ok = False
    assert mod.tick() == 0
    assert poste.analyses == []                         # aucune réflexion payée
    st_file = tmp_path / "gateway" / "state.json"
    offset = _state(tmp_path / "gateway")["offset"] if st_file.exists() else 0
    assert offset <= 20                                 # message pas consommé

    poste.envoi_ok = True
    assert mod.tick() == 0
    assert "réponse à « question »" in poste.envois[-1]
    assert _state(tmp_path / "gateway")["offset"] == 21


def test_une_question_n_est_jamais_payee_deux_fois(poste, tmp_path, monkeypatch):
    """LA leçon de s14 appliquée ici : le message est consommé AVANT l'appel
    payé. Une panne de remise ne doit pas refaire réfléchir Claude — sinon
    Telegram indisponible une heure = soixante réflexions facturées."""
    poste.updates = [_update(30, "question chère")]
    envois_reels = []

    def envoi_capricieux(t, c, txt):
        # L'accusé passe, tout le reste échoue (panne survenue après).
        if "Reçu par le terminal" in txt:
            envois_reels.append(txt)
            return True
        return False

    monkeypatch.setattr(mod, "send", envoi_capricieux)
    monkeypatch.setattr(mod, "time", type("T", (), {
        "monotonic": staticmethod(lambda: 0.0),
        "sleep": staticmethod(lambda s: None)})())

    assert mod.tick() == 0
    assert len(poste.analyses) == 1                      # payé UNE fois
    assert _state(tmp_path / "gateway")["offset"] == 31  # consommé quand même

    # Tick suivant : plus rien à traiter, donc rien à repayer.
    poste.updates = []
    assert mod.tick() == 0
    assert len(poste.analyses) == 1


def test_session_headless_en_panne_repond_quand_meme(poste, monkeypatch):
    monkeypatch.setattr(mod, "ask_claude", lambda q: None)
    poste.updates = [_update(30, "état ?")]
    assert mod.tick() == 0
    assert len(poste.envois) == 3                       # les 3 signaux quand même
    assert "n'a pas abouti" in poste.envois[-1]


# == LES REFUS PROPRES =========================================================
def test_token_absent_exit_2(poste, tmp_path):
    (tmp_path / "gateway" / "gateway_token.txt").unlink()
    poste.updates = [_update(1, "état ?")]
    assert mod.tick() == 2
    assert poste.envois == []


def test_config_absente_exit_2(poste, tmp_path):
    (tmp_path / "gateway" / "config.json").unlink()
    assert mod.tick() == 2


def test_telegram_injoignable_exit_2(poste, monkeypatch):
    monkeypatch.setattr(mod, "fetch_updates", lambda t, o: None)
    assert mod.tick() == 2


def test_dry_run_ne_lance_aucune_session(poste, tmp_path, monkeypatch):
    appels = []
    monkeypatch.setattr(mod, "ask_claude",
                        lambda q: appels.append(q) or "jamais")
    poste.updates = [_update(1, "état ?")]
    assert mod.tick(dry=True) == 0
    assert appels == [] and poste.envois == []
    assert not (tmp_path / "gateway" / "state.json").exists()


# == CE QU'ON NE DIVULGUE PAS ==================================================
def test_token_jamais_dans_les_logs(monkeypatch, capsys):
    """Le repr des exceptions requests porte l'URL, donc le token — et la
    factory redirige stderr vers un fichier."""
    def post_qui_echoue(*a, **kw):
        raise RuntimeError("Max retries exceeded with url: "
                           "/botTOKEN-BIDON/getUpdates")

    monkeypatch.setattr(mod.requests, "post", post_qui_echoue)
    assert mod._post("TOKEN-BIDON", "getUpdates", {}) is None
    sortie = capsys.readouterr()
    assert "TOKEN-BIDON" not in (sortie.out + sortie.err)


def test_session_headless_est_en_lecture_seule():
    """Garde-fou de conception : le téléphone est une fenêtre, pas une
    télécommande. Élargir cette liste est une décision de sécurité."""
    outils = set(mod.ALLOWED_TOOLS.split(","))
    assert outils == {"Read", "Grep", "Glob"}
    for interdit in ("Bash", "Write", "Edit", "NotebookEdit"):
        assert interdit not in mod.ALLOWED_TOOLS


# == LE MENU DES COMMANDES =====================================================

def test_menu_decouvre_les_skills_du_projet():
    """Les skills du PROJET, pas les skills globales d'Adrian : ce bot répond
    de RobinBot, pas de tout son écosystème."""
    cmds = mod.decouvrir_commandes()
    assert cmds, "aucune skill projet découverte"
    noms = {c["command"] for c in cmds}
    assert "etat" in noms                      # robinbot-etat -> etat
    for c in cmds:
        assert c["command"] == c["command"].lower()
        assert all(ch.isalnum() or ch == "_" for ch in c["command"])
        assert 1 <= len(c["command"]) <= 32     # contraintes Telegram
        assert 0 < len(c["description"]) <= 256


def test_prefixe_robinbot_retire():
    """Huit caractères de moins à taper au pouce, et redondants dans un bot
    qui s'appelle déjà RobinBot."""
    assert mod._nom_telegram("robinbot-etat") == "etat"
    assert mod._nom_telegram("robinbot_pilot") == "pilot"
    assert mod._nom_telegram("etat-simple") == "etat_simple"
    assert mod._nom_telegram("robinbot") == "robinbot"   # pas de nom vide


def test_commande_traduite_en_invocation_de_skill():
    cmds = [{"command": "etat", "description": "d", "skill": "robinbot-etat",
             "dossier": "/x/robinbot-etat"}]
    q, skill = mod.resoudre_commande("/etat", cmds)
    assert skill is not None and "robinbot-etat" in q and "SKILL.md" in q


def test_texte_libre_apres_la_commande_conserve():
    """« /etat et l'or ? » doit pouvoir orienter la réponse."""
    cmds = [{"command": "etat", "description": "d", "skill": "s", "dossier": "/x"}]
    q, _ = mod.resoudre_commande("/etat et l'or ?", cmds)
    assert "et l'or ?" in q


def test_suffixe_du_bot_tolere():
    """Telegram écrit parfois /etat@AdrianRobinBot dans les groupes."""
    cmds = [{"command": "etat", "description": "d", "skill": "s", "dossier": "/x"}]
    _, skill = mod.resoudre_commande("/etat@AdrianRobinBot", cmds)
    assert skill is not None


def test_commande_inconnue_rappelle_le_menu():
    cmds = [{"command": "etat", "description": "d", "skill": "s", "dossier": "/x"}]
    q, skill = mod.resoudre_commande("/pizza", cmds)
    assert skill is None and "/etat" in q and "inconnue" in q


def test_message_libre_passe_intact():
    cmds = [{"command": "etat", "description": "d", "skill": "s", "dossier": "/x"}]
    q, skill = mod.resoudre_commande("comment va l or ?", cmds)
    assert q == "comment va l or ?" and skill is None


def test_menu_publie_une_seule_fois(poste, tmp_path, monkeypatch):
    """Ce worker tourne toutes les 30 s : republier un menu identique 2 880
    fois par jour serait du bruit pur sur l'API."""
    envois = []
    monkeypatch.setattr(mod, "_post",
                        lambda t, m, p: envois.append(m) or {"ok": True})
    st = {}
    cmds = [{"command": "etat", "description": "d", "skill": "s", "dossier": "/x"}]
    mod.synchroniser_commandes("T", st, cmds)
    mod.synchroniser_commandes("T", st, cmds)
    assert envois == ["setMyCommands"]          # une seule fois
    cmds.append({"command": "trades", "description": "d2", "skill": "s2",
                 "dossier": "/y"})
    mod.synchroniser_commandes("T", st, cmds)
    assert len(envois) == 2                     # le menu a changé : republié


def test_menu_non_publie_reste_a_republier(poste, monkeypatch):
    """Un échec ne doit pas faire croire que le menu est en place."""
    monkeypatch.setattr(mod, "_post", lambda t, m, p: None)
    st = {}
    mod.synchroniser_commandes("T", st, [{"command": "etat", "description": "d",
                                          "skill": "s", "dossier": "/x"}])
    assert "menu" not in st
