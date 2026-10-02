# PROBLEMS — Registro de Incidentes

Los problemas **nunca se borran**, ni después de resolverse, para evitar reincidencias.

---

## P-01 — `ssh-copy-id` no disponible en Windows PowerShell

| Campo | Detalle |
|---|---|
| **Fecha** | 2026-05 |
| **Fase** | T-02 · Configuración SSH al NAS |
| **Síntoma** | `ssh-copy-id : El término 'ssh-copy-id' no se reconoce…` al intentar copiar la llave pública al NAS desde PowerShell. |
| **Causa raíz** | `ssh-copy-id` es una utilidad Unix/Linux. No existe en OpenSSH para Windows. |
| **Solución** | El usuario copió la llave manualmente (método alternativo). Workaround en PowerShell hubiera sido: `\ = Get-Content ~/.ssh/id_ed25519.pub; ssh admin@HOST "mkdir -p ~/.ssh && echo '\' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"` |
| **Resultado** | SSH sin contraseña funcionando correctamente. |
| **Prevención** | En Windows, usar siempre el workaround de PowerShell o WSL para copiar llaves SSH. |

---

## P-02 — Clone del repo fallaba por `Host key verification failed`

| Campo | Detalle |
|---|---|
| **Fecha** | 2026-05 |
| **Fase** | T-03 · Clone del repo en el NAS |
| **Síntoma** | `fatal: Could not read from remote repository` al hacer `git clone git@github.com:...` desde el NAS. |
| **Causa raíz** | El NAS no tenía llave SSH registrada en GitHub. La clave de la PC de desarrollo no sirve para el NAS; cada máquina necesita su propia llave. |
| **Solución** | Generar nueva llave `ed25519` en el NAS con `ssh-keygen`, luego agregarla en GitHub ? Settings ? SSH keys. |
| **Resultado** | Clone exitoso en `/mnt/Luis/Finanzas`. |
| **Prevención** | Cada servidor/máquina nueva necesita su propia llave SSH en GitHub. |
