"""
Tests du mesureur — synthétiques, AUCUN réseau, AUCUNE session Claude réelle,
AUCUNE commande git réelle.

POURQUOI ce banc : c'est le worker le plus puissant du dépôt (Write + Bash). Sa
sûreté ne tient pas à sa liste d'outils mais à deux contrôles mécaniques, et
c'est donc eux qu'on éprouve en priorité : un scellé qui bouge pendant la
session, un commit qui apparaît. Les deux doivent sortir en 1, crier, et laisser
la trace dans le rapport. Le reste vérifie que le cas « aucun mandat » ne coûte
rien.

Le module vit dans un fichier à tiret : import par chemin.

    pytest orchestrator/test_robinbot_mesureur.py -q
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "robinbot_mesureur", _HERE / "robinbot-mesureur.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

SCELLES = ("gold_forward", "s13_forward", "macd_ai_paper", "s14_sentiment",
           "portfolio_forward")
HEAD_INITIAL = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
MANDAT = "portfolio_forward : porter la cellule S1 sur core/, avec ses tests."


class Usine:
    """Un dépôt jetable : cinq scellés factices, un mandat, un git de papier,
    et une session headless dont on compte les lancements."""

    def __init__(self, tmp: pathlib.Path):
        self.tmp = tmp
        self.prompts: list[str] = []
        self.rendu: str | None = "Un pas fait, pytest vert."
        self.pendant = None          # ce que « la session » fait au passage
        self.head = HEAD_INITIAL     # git de papier : jamais de vrai appel

    def session(self, question: str) -> str | None:
        self.prompts.append(question)
        if self.pendant is not None:
            self.pendant()
        return self.rendu

    def mandat(self, contenu: str) -> None:
        (self.tmp / "orchestrator" / "mesureur-mandat.txt").write_text(
            contenu, encoding="utf-8")

    def rapport(self) -> str:
        f = self.tmp / "orchestrator" / "mesureur-rapport.md"
        return f.read_text(encoding="utf-8") if f.exists() else ""

    def params(self, etude: str) -> pathlib.Path:
        return self.tmp / "studies" / etude / "params.json"


@pytest.fixture
def usine(tmp_path, monkeypatch) -> Usine:
    for nom in SCELLES:
        d = tmp_path / "studies" / nom
        d.mkdir(parents=True)
        (d / "params.json").write_text(json.dumps({"etude": nom}),
                                       encoding="utf-8")
    (tmp_path / "orchestrator").mkdir()
    skill = tmp_path / ".claude" / "skills" / "robinbot-mesureur"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: robinbot-mesureur\n---\n",
                                    encoding="utf-8")

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "MANDAT_FILE",
                        tmp_path / "orchestrator" / "mesureur-mandat.txt")
    monkeypatch.setattr(mod, "RAPPORT_FILE",
                        tmp_path / "orchestrator" / "mesureur-rapport.md")
    monkeypatch.setattr(mod, "MESUREUR_DIR", tmp_path / "mesureur")
    monkeypatch.setattr(mod, "STATE_FILE", tmp_path / "mesureur" / "state.json")

    u = Usine(tmp_path)
    monkeypatch.setattr(mod, "lancer_session", u.session)
    monkeypatch.setattr(mod, "git_head", lambda: u.head)
    return u


# == LE CAS GRATUIT (le plus fréquent) =========================================
def test_mandat_absent_aucune_session_et_rien_ecrit(usine, tmp_path, capsys):
    assert mod.tick() == 0
    assert usine.prompts == []
    assert not (tmp_path / "mesureur" / "state.json").exists()
    assert "aucun mandat" in capsys.readouterr().out


def test_mandat_vide_aucune_session(usine):
    usine.mandat("   \n\n")
    assert mod.tick() == 0
    assert usine.prompts == []


def test_mandat_seulement_commente_aucune_session(usine, capsys):
    """Le gabarit reste dans le fichier entre deux mandats : il ne doit pas
    faire travailler l'usine."""
    usine.mandat("# Un mandat par ligne. Vide = rien à faire.\n"
                 "#   exemple : portfolio_forward — porter la cellule S1\n")
    assert mod.tick() == 0
    assert usine.prompts == []
    assert "aucun mandat" in capsys.readouterr().out


# == LE CAS NOMINAL ============================================================
def test_mandat_present_lance_une_session_qui_nomme_la_skill(usine, tmp_path):
    usine.mandat(f"# gabarit conservé\n{MANDAT}\n")
    assert mod.tick() == 0
    assert len(usine.prompts) == 1
    prompt = usine.prompts[0]
    assert "robinbot-mesureur" in prompt
    assert "SKILL.md" in prompt
    assert MANDAT in prompt
    assert "gabarit conservé" not in prompt        # les commentaires sont retirés
    etat = json.loads((tmp_path / "mesureur" / "state.json").read_text(encoding="utf-8"))
    assert etat["n_sessions"] == 1
    assert etat["dernier_mandat"].startswith("portfolio_forward")


def test_la_porte_atteinte_remonte_dans_la_derniere_ligne(usine, capsys):
    """La console de la factory ne remonte que la DERNIÈRE ligne du log : elle
    doit dire à quoi le passage s'est arrêté."""
    usine.mandat(MANDAT)
    usine.pendant = lambda: (usine.tmp / "orchestrator" / "mesureur-rapport.md"
                             ).write_text("# Mesureur\nTESTS : vert\n"
                                          "BLOQUÉ : le scellement de P2 demande Adrian.\n",
                                          encoding="utf-8")
    assert mod.tick() == 0
    derniere = [l for l in capsys.readouterr().out.splitlines() if l.strip()][-1]
    assert "passage terminé" in derniere
    assert "scellement de P2" in derniere


# == LES GARDE-FOUS MÉCANIQUES =================================================
def test_scelle_modifie_pendant_la_session_exit_1(usine, tmp_path, capsys):
    usine.mandat(MANDAT)
    usine.pendant = lambda: usine.params("portfolio_forward").write_text(
        json.dumps({"etude": "portfolio_forward", "spread": 0.1}),
        encoding="utf-8")
    assert mod.tick() == 1

    sortie = capsys.readouterr()
    # L'alerte est la PREMIÈRE ligne de stderr — avant tout le reste.
    premiere = [l for l in sortie.err.splitlines() if l.strip()][0]
    assert "INCIDENT" in premiere
    assert "studies/portfolio_forward/params.json" in sortie.err
    assert "hash modifié" in sortie.err
    # Le rapport le mentionne : c'est lui qu'un humain relit.
    assert "INCIDENT" in usine.rapport()
    assert "portfolio_forward/params.json" in usine.rapport()
    assert not (tmp_path / "mesureur" / "state.json").exists()


def test_scelle_cree_pendant_la_session_exit_1(usine, capsys):
    """Créer un params.json, c'est sceller — un acte d'Adrian, jamais du worker."""
    usine.mandat(MANDAT)

    def naissance():
        d = usine.tmp / "studies" / "s15_cot"
        d.mkdir(parents=True)
        (d / "params.json").write_text("{}", encoding="utf-8")

    usine.pendant = naissance
    assert mod.tick() == 1
    assert "APPARU" in capsys.readouterr().err


def test_head_git_deplace_pendant_la_session_exit_1(usine, tmp_path, capsys):
    usine.mandat(MANDAT)

    def commit():
        usine.head = "ffffffffffffffffffffffffffffffffffffffff"

    usine.pendant = commit
    assert mod.tick() == 1

    sortie = capsys.readouterr()
    assert "INCIDENT" in sortie.err
    assert "HEAD a bougé" in sortie.err
    assert "HEAD a bougé" in usine.rapport()
    assert not (tmp_path / "mesureur" / "state.json").exists()


def test_git_indisponible_ne_fabrique_pas_d_incident(usine, monkeypatch, capsys):
    """Sans git, le contrôle est impossible — on le dit, on n'invente pas une
    violation."""
    monkeypatch.setattr(mod, "git_head", lambda: None)
    usine.mandat(MANDAT)
    assert mod.tick() == 0
    assert "git indisponible" in capsys.readouterr().out


def test_scelles_et_head_intacts_ne_declenchent_rien(usine):
    usine.mandat(MANDAT)
    usine.pendant = lambda: (usine.tmp / "core.py").write_text("# du code",
                                                               encoding="utf-8")
    assert mod.tick() == 0


def test_scelles_verifies_meme_si_la_session_echoue(usine, capsys):
    """Un timeout tue une session EN COURS d'écriture : il ne prouve pas
    qu'elle n'a rien fait. L'incident prime sur le refus propre."""
    usine.mandat(MANDAT)
    usine.rendu = None
    usine.pendant = lambda: usine.params("gold_forward").write_text(
        "{}", encoding="utf-8")
    assert mod.tick() == 1
    assert "INCIDENT" in capsys.readouterr().err


# == LES REFUS PROPRES =========================================================
def test_session_indisponible_exit_2_et_rien_ecrit(usine, tmp_path):
    usine.mandat(MANDAT)
    usine.rendu = None
    assert mod.tick() == 2
    assert not (tmp_path / "mesureur" / "state.json").exists()
    assert usine.rapport() == ""


def test_dry_run_n_appelle_rien_et_n_ecrit_rien(usine, tmp_path, capsys):
    usine.mandat(MANDAT)
    assert mod.tick(dry=True) == 0
    assert usine.prompts == []
    assert not (tmp_path / "mesureur" / "state.json").exists()
    assert "DRY-RUN" in capsys.readouterr().out


def test_claude_absent_rend_none_sans_lancer_de_processus(monkeypatch, capsys):
    """La vraie fonction d'invocation, sans binaire : elle refuse avant tout
    Popen. C'est la seule branche de `lancer_session` qu'un banc peut exercer
    sans ouvrir de session réelle."""
    monkeypatch.setattr(mod.shutil, "which", lambda nom: None)
    assert mod.lancer_session("peu importe") is None
    assert "introuvable" in capsys.readouterr().err


# == CE QU'IL A LE DROIT DE FAIRE ==============================================
def test_outils_accordes_ecrire_et_tester():
    """Il écrit du code et lance pytest — c'est assumé. Ce qui le tient, ce sont
    les hash des scellés et le HEAD git, pas cette liste."""
    assert set(mod.ALLOWED_TOOLS.split(",")) == {
        "Read", "Grep", "Glob", "Edit", "Write", "Bash"}


def test_le_plafond_reste_sous_celui_de_la_factory():
    """La factory tue l'arbre d'un tick à 1200 s : un plafond plus haut ferait
    couper la session par la factory, sans que le worker sache dire pourquoi."""
    assert mod.CLAUDE_TIMEOUT_S == 900
    assert mod.CLAUDE_TIMEOUT_S < 1200
