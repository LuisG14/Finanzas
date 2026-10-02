# NEXT-SESSION — Estado dinámico del proyecto

> Actualiza este archivo al final de cada sesión de trabajo.

---

## Estado del proyecto

?? **En progreso** — App funcional en local. Despliegue en NAS pendiente.

---

## Track activo: T-05 — Despliegue en TrueNAS SCALE

### Contexto
- NAS: TrueNAS SCALE, IP `100.104.88.116`, usuario `admin`
- Repo clonado en `/mnt/Luis/Finanzas`
- SSH sin contraseña configurado desde la PC de desarrollo
- Estrategia elegida: **Docker Compose** (no correr Streamlit directo en el shell)

### Tareas

- [ ] Crear `Dockerfile` en la raíz del repo
- [ ] Crear `docker-compose.yml` en la raíz del repo
- [ ] Crear `update.sh` — script para `git pull + docker compose up --build`
- [ ] Levantar el contenedor en el NAS y verificar acceso en `http://100.104.88.116:8501`
- [ ] Confirmar que el servicio sobrevive un reinicio del NAS

---

## Backlog (próximas sesiones)

- [ ] Agregar `README.md` con instrucciones de instalación y uso
- [ ] Evaluar si los datos (`data/`) deben montarse como volumen externo en Docker
      para que un `git pull` no pise los CSVs actuales del NAS

---

## Comandos útiles

```bash
# Conectar al NAS
ssh admin@100.104.88.116

# Ir al repo
cd /mnt/Luis/Finanzas

# Correr la app manualmente (sin Docker, para pruebas rápidas)
pip install -r requirements.txt
streamlit run app.py --server.port 8501 --server.headless true

# Ver logs del contenedor (cuando Docker esté configurado)
docker compose logs -f
```
