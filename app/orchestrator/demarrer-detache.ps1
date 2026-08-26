# demarrer-detache.ps1 — lance la factory HORS de l'arbre de l'appelant.
#
# POURQUOI ce script existe. Le 2026-08-21, Adrian n'a plus pu ouvrir Claude
# Desktop : « Another program is currently using this file ». La factory avait
# ete lancee depuis une session Claude Code, elle en etait donc DESCENDANTE — et
# comme elle ne s'arrete jamais, l'arbre de processus de l'application ne se
# liberait plus. La mise a jour MSIX, qui exige l'ancien paquet libre, restait
# bloquee. Tuer la factory a debloque.
#
# Start-Process ne suffit pas : le processus cree reste un enfant de l'appelant.
# On passe donc par WMI (Win32_Process::Create), dont le processus nait sous le
# fournisseur WMI et non sous nous. La factory devient orpheline par
# construction : elle survit a la fermeture de la session, et surtout elle ne
# retient plus personne.
#
# Adrian, lui, n'a pas besoin de ce script : un double-clic sur run-factory.bat
# donne explorer.exe comme ancetre, ce qui est deja propre.

$racine = Split-Path -Parent $PSScriptRoot
$bat = Join-Path $PSScriptRoot 'run-factory.bat'
if (-not (Test-Path $bat)) { Write-Error "introuvable : $bat"; exit 1 }

$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine      = "cmd.exe /c start `"RobinBot factory`" `"$bat`""
    CurrentDirectory = $racine
}
if ($r.ReturnValue -eq 0) {
    Write-Output "factory lancee detachee (pid intermediaire $($r.ProcessId))"
} else {
    Write-Error "echec du lancement WMI, code $($r.ReturnValue)"
    exit 1
}
