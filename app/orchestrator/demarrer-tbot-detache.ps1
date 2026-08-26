# demarrer-tbot-detache.ps1 — lance la tBot factory HORS de l'arbre de l'appelant.
#
# Meme raison d'etre que le demarrer-detache.ps1 du prototype (lecon 2026-08-21) :
# une factory descendante d'une session Claude Code retient l'arbre de processus
# de l'application. On passe par WMI (Win32_Process::Create) : la factory nait
# sous le fournisseur WMI, orpheline par construction, console visible.
#
# Adrian n'a pas besoin de ce script : double-clic sur run-tbot-factory.bat
# (ancetre = explorer.exe, deja propre). Ce script sert a cc-support.
#
# TBOT_UI_PORT est fixe dans la ligne de commande (l'env d'un processus WMI ne
# suit pas l'env utilisateur de maniere fiable) : 8790 tant que le prototype
# tient 8742 sur ce poste (jusqu'a E6).

$racine = 'C:\projects\tradingBot'
$cmdline = 'cmd.exe /c start "tBot factory" cmd /k "title tBot factory & chcp 65001 >nul & cd /d C:\projects\tradingBot & set TBOT_UI_PORT=8790 & python app\orchestrator\tbot-factory.py"'

$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine      = $cmdline
    CurrentDirectory = $racine
}
if ($r.ReturnValue -eq 0) {
    Write-Output "tbot factory lancee detachee (pid intermediaire $($r.ProcessId))"
} else {
    Write-Error "echec du lancement WMI, code $($r.ReturnValue)"
    exit 1
}
