"""
Tests du portier — synthétiques, AUCUN réseau, AUCUNE session Claude réelle.

POURQUOI ce banc : le portier dépense des tokens et a le droit d'ÉCRIRE dans
FILE_ETUDES.md. On vérifie donc deux choses. D'abord qu'il ne dépense rien pour
rien : ENTRÉE vide ou déjà annotée, aucune session. Ensuite qu'il ne déborde
pas : les scellés sont relevés avant/après, et une divergence sort en 1 même si
la session s'est déclarée satisfaite.

Le module vit dans un fichier à tiret : import par chemin.

    pytest orchestrator/test_robinbot_portier.py -q
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "robinbot_portier", _HERE / "robinbot-portier.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

SCELLES = ("gold_forward", "s13_forward", "macd_ai_paper", "s14_sentiment",
           "portfolio_forward")

IDEE = "**Sentiment Twitter comme filtre d'entrée.** Idée brute d'Adrian."
ANNOTATION = """\
  → PORTIER 2026-08-21
    Déjà instruite : non
    Donnée : X, instantané, aucun historique
    Effectif espéré : nul — pas backtestable
    Avis : INFAISABLE — aucune source historisée."""


def _file_etudes(entree: str = "_(vide)_", n_encours: int = 2) -> str:
    """Une file d'études crédible : même sections, même style que la vraie."""
    cours = "\n\n".join(
        f"### {i}. `etude_{i}` — en mesure\nSon horloge tourne."
        for i in range(1, n_encours + 1)) or "_(aucune)_"
    return f"""\
# FILE DES ÉTUDES — limite d'encours : **2**

> La règle. Au plus DEUX études occupent un créneau de mesure à la fois.

---

## EN COURS — {n_encours} / 2

{cours}

---

## PRÊTES — cadrées, attendent une place

**`s16_confluence` — la stratégie à quatre piliers.** Cadrage écrit, condition
inscrite au dossier.

---

## ENTRÉE — brut, non trié

> Toute idée neuve atterrit ICI, et nulle part ailleurs. Le portier l'annote
> sans jamais rien supprimer.

{entree}

---

## CLOSES — pour ne pas les réinstruire

| Sujet | Verdict | Où |
|---|---|---|
| s90 « fade de l'échec » | PAS D'EDGE | `strategies/s90/VERDICT.md` |
"""


class Usine:
    """Un dépôt jetable : cinq scellés factices, une file, et une session
    headless de papier dont on compte les lancements."""

    def __init__(self, tmp: pathlib.Path):
        self.tmp = tmp
        self.prompts: list[str] = []
        self.rendu: str | None = "Deux idées annotées."
        self.pendant = None          # ce que « la session » fait au passage

    def session(self, question: str) -> str | None:
        self.prompts.append(question)
        if self.pendant is not None:
            self.pendant()
        return self.rendu

    def file(self, entree: str = "_(vide)_", n_encours: int = 2) -> None:
        (self.tmp / "FILE_ETUDES.md").write_text(
            _file_etudes(entree, n_encours), encoding="utf-8")

    def params(self, etude: str) -> pathlib.Path:
        return self.tmp / "studies" / etude / "params.json"


@pytest.fixture
def usine(tmp_path, monkeypatch) -> Usine:
    for nom in SCELLES:
        d = tmp_path / "studies" / nom
        d.mkdir(parents=True)
        (d / "params.json").write_text(json.dumps({"etude": nom}),
                                       encoding="utf-8")
    skill = tmp_path / ".claude" / "skills" / "robinbot-portier"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: robinbot-portier\n---\n",
                                    encoding="utf-8")

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "FILE_ETUDES", tmp_path / "FILE_ETUDES.md")
    monkeypatch.setattr(mod, "PORTIER_DIR", tmp_path / "portier")
    monkeypatch.setattr(mod, "STATE_FILE", tmp_path / "portier" / "state.json")

    u = Usine(tmp_path)
    monkeypatch.setattr(mod, "lancer_session", u.session)
    u.file()
    return u


# == LE CAS GRATUIT (le plus fréquent) =========================================
def test_entree_vide_aucune_session_et_rien_ecrit(usine, tmp_path, capsys):
    assert mod.tick() == 0
    assert usine.prompts == []
    assert not (tmp_path / "portier" / "state.json").exists()
    assert "rien à trier" in capsys.readouterr().out


def test_idee_deja_annotee_aucune_session(usine):
    usine.file(entree=f"{IDEE}\n\n{ANNOTATION}")
    assert mod.tick() == 0
    assert usine.prompts == []


def test_annotation_collee_sous_l_idee_compte_aussi(usine):
    """Le bloc peut être écrit sans ligne vide : c'est la même annotation."""
    usine.file(entree=f"{IDEE}\n{ANNOTATION}")
    assert mod.tick() == 0
    assert usine.prompts == []


def test_idee_sur_deux_lignes_reste_une_seule_idee(usine):
    usine.file(entree="**Une idée dont le titre déborde sur la ligne\n"
                      "suivante.** Et sa description.")
    assert mod.tick() == 0
    assert len(usine.prompts) == 1
    assert mod.idees_de_l_entree(_file_etudes(
        "**Une idée qui déborde\nsur deux lignes.**")) == [
        {"titre": "Une idée qui déborde", "annotee": False}]


# == CE QU'IL NE RATE PAS ======================================================
def test_idee_non_annotee_lance_une_session_qui_nomme_la_skill(usine, tmp_path):
    usine.file(entree=IDEE)
    assert mod.tick() == 0
    assert len(usine.prompts) == 1
    prompt = usine.prompts[0]
    assert "robinbot-portier" in prompt
    assert "SKILL.md" in prompt
    assert "Sentiment Twitter" in prompt
    etat = json.loads((tmp_path / "portier" / "state.json").read_text(encoding="utf-8"))
    assert etat["n_sessions"] == 1


def test_seule_l_idee_neuve_est_soumise(usine):
    usine.file(entree=f"{IDEE}\n\n{ANNOTATION}\n\n"
                      "**Polymarket comme source macro.** À reprendre.")
    assert mod.tick() == 0
    assert len(usine.prompts) == 1
    assert "Polymarket" in usine.prompts[0]
    assert "Sentiment Twitter" not in usine.prompts[0]


def test_limite_d_encours_depassee_est_signalee(usine, capsys):
    usine.file(n_encours=3)
    assert mod.tick() == 0                      # ENTRÉE vide : rien à trier
    sortie = capsys.readouterr()
    assert "3 études EN COURS" in sortie.err
    assert "limite" in sortie.err
    assert "encours 3/2 DÉPASSÉ" in sortie.out


def test_l_encours_depasse_entre_dans_le_prompt(usine):
    usine.file(entree=IDEE, n_encours=3)
    assert mod.tick() == 0
    assert "3 entrées" in usine.prompts[0]


# == LE GARDE-FOU MÉCANIQUE ====================================================
def test_scelle_modifie_pendant_la_session_exit_1(usine, tmp_path, capsys):
    usine.file(entree=IDEE)
    usine.pendant = lambda: usine.params("gold_forward").write_text(
        json.dumps({"etude": "gold_forward", "sl": 999}), encoding="utf-8")
    assert mod.tick() == 1
    sortie = capsys.readouterr()
    assert "INCIDENT" in sortie.err
    assert "studies/gold_forward/params.json" in sortie.err
    assert "hash modifié" in sortie.err
    # Rien n'est sauvé : le passage est une alarme, pas un travail accompli.
    assert not (tmp_path / "portier" / "state.json").exists()


def test_scelle_supprime_pendant_la_session_exit_1(usine, capsys):
    usine.file(entree=IDEE)
    usine.pendant = lambda: usine.params("s13_forward").unlink()
    assert mod.tick() == 1
    assert "DISPARU" in capsys.readouterr().err


def test_scelles_intacts_ne_declenchent_rien(usine):
    usine.file(entree=IDEE)
    usine.pendant = lambda: (usine.tmp / "FILE_ETUDES.md").write_text(
        _file_etudes(f"{IDEE}\n\n{ANNOTATION}"), encoding="utf-8")
    assert mod.tick() == 0


# == LES REFUS PROPRES =========================================================
def test_session_indisponible_exit_2_et_rien_ecrit(usine, tmp_path):
    usine.file(entree=IDEE)
    usine.rendu = None
    assert mod.tick() == 2
    assert not (tmp_path / "portier" / "state.json").exists()


def test_dry_run_n_appelle_rien_et_n_ecrit_rien(usine, tmp_path, capsys):
    usine.file(entree=IDEE)
    assert mod.tick(dry=True) == 0
    assert usine.prompts == []
    assert not (tmp_path / "portier" / "state.json").exists()
    assert "DRY-RUN" in capsys.readouterr().out


def test_file_illisible_exit_2(usine, tmp_path):
    (tmp_path / "FILE_ETUDES.md").unlink()
    assert mod.tick() == 2
    assert usine.prompts == []


def test_claude_absent_rend_none_sans_lancer_de_processus(monkeypatch, capsys):
    """La vraie fonction d'invocation, sans binaire : elle refuse avant tout
    Popen. C'est la seule branche de `lancer_session` qu'un banc peut exercer
    sans ouvrir de session réelle."""
    monkeypatch.setattr(mod.shutil, "which", lambda nom: None)
    assert mod.lancer_session("peu importe") is None
    assert "introuvable" in capsys.readouterr().err


# == CE QU'IL A LE DROIT DE FAIRE ==============================================
def test_outils_accordes_annoter_oui_executer_non():
    """Edit parce qu'il annote la file. Rien d'autre : il ne crée aucun fichier
    et n'exécute rien."""
    assert set(mod.ALLOWED_TOOLS.split(",")) == {"Read", "Grep", "Glob", "Edit"}
    for interdit in ("Bash", "Write", "WebFetch"):
        assert interdit not in mod.ALLOWED_TOOLS


def test_derniere_ligne_du_log_resume_le_passage(usine, capsys):
    """La console de la factory ne remonte que la DERNIÈRE ligne du log."""
    usine.file(entree=IDEE)
    mod.tick()
    derniere = [l for l in capsys.readouterr().out.splitlines() if l.strip()][-1]
    assert "passage terminé" in derniere
    assert "scellés intacts" in derniere
