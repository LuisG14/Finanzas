# NEXT-SESSION — Estado dinamico del proyecto

> Actualiza este archivo al final de cada sesion de trabajo.

---

## Estado del proyecto

🟡 **En progreso** — Docker configurado. Falta levantar el contenedor en el NAS y verificar.

---

## Track activo: T-05 — Despliegue en TrueNAS SCALE

### Contexto
- NAS: TrueNAS SCALE, IP `100.104.88.116`, usuario `admin`
- Repo clonado en `/mnt/Luis/Finanzas`
- SSH sin contrasena configurado desde la PC de desarrollo
- Estrategia elegida: **Docker Compose**

### Tareas

- [x] Crear `Dockerfile`
- [x] Crear `docker-compose.yml`
- [x] Crear `update.sh`
- [ ] Levantar el contenedor en el NAS: `cd /mnt/Luis/Finanzas && git pull && docker compose up -d --build`
- [ ] Verificar acceso en `http://100.104.88.116:8501`
- [ ] Confirmar que el servicio sobrevive un reinicio del NAS

---

## Backlog (proximas sesiones)

- [ ] Agregar `README.md` con instrucciones de instalacion y uso
- [ ] Evaluar si `data/` debe excluirse del `.gitignore` en el NAS (los CSVs ya estan montados como volumen, pero el repo los sigue trackeando)

---

## Comandos utiles

```bash
# Conectar al NAS
ssh admin@100.104.88.116

# Actualizar la app desde GitHub y reconstruir el contenedor
cd /mnt/Luis/Finanzas && bash update.sh

# O desde la PC directamente
ssh admin@100.104.88.116 "cd /mnt/Luis/Finanzas && bash update.sh"

# Ver logs en vivo
ssh admin@100.104.88.116 "cd /mnt/Luis/Finanzas && docker compose logs -f"
```