# Guía del servidor — javigmdev-server

Mini PC NiPoGi (Ryzen 7 5700U, 32 GB RAM, Ubuntu). Accesible en la red local como `http://javigmdev-server.local`.

Las apps se sirven por rutas: `http://javigmdev-server.local/<nombre-app>/`

---

## Infraestructura (instalada una sola vez)

```bash
sudo apt install -y avahi-daemon nginx
sudo ufw allow 80
sudo ufw allow 5353/udp
```

- **avahi-daemon** — publica `javigmdev-server.local` en la red local (mDNS)
- **nginx** — proxy inverso en el puerto 80, enruta por rutas a cada app

---

## Añadir una nueva app

### 1. Desplegar la app

```bash
cd ~/apps
git clone <repo> <nombre-app>
cd <nombre-app>
bash setup.sh          # si tiene script de instalación
```

La app debe escuchar en un puerto local (ej. 5001, 5002…). Asegúrate de que no colisiona con apps existentes.

### 2. Añadir la ruta en nginx

```bash
sudo nano /etc/nginx/sites-available/audiobookconverter
```

Añade un bloque `location` dentro del `server` existente:

```nginx
location = /<nombre-app> { return 301 /<nombre-app>/; }

location /<nombre-app>/ {
    proxy_pass http://127.0.0.1:<puerto>/;
    proxy_set_header Host $host;
    proxy_read_timeout 86400;
    proxy_buffering off;
    proxy_cache off;
}

location /<nombre-app>/static/ {
    proxy_pass http://127.0.0.1:<puerto>/static/;
    proxy_set_header Host $host;
}
```

Recarga nginx:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 3. Arrancar la app

```bash
cd ~/apps/<nombre-app>
source venv/bin/activate
python app.py
```

Accede en `http://javigmdev-server.local/<nombre-app>/`

---

## Apps actuales

| Ruta | Puerto | Repo |
|------|--------|------|
| `/audiobookconverter/` | 5000 | audiobook-pipeline |

---

## Config nginx completa

El fichero está en `/etc/nginx/sites-available/audiobookconverter`.

Config actual con todas las opciones:

```nginx
server {
    listen 80;
    server_name javigmdev-server.local;
    client_max_body_size 50M;

    location = /audiobookconverter {
        return 301 /audiobookconverter/;
    }

    location /audiobookconverter/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
        proxy_buffering off;
        proxy_cache off;
    }

    location /static/ {
        proxy_pass http://127.0.0.1:5000/static/;
        proxy_set_header Host $host;
    }

    # nueva-app
    # location = /nueva-app { return 301 /nueva-app/; }
    # location /nueva-app/ {
    #     proxy_pass http://127.0.0.1:5001/;
    #     proxy_set_header Host $host;
    #     proxy_read_timeout 86400;
    #     proxy_buffering off;
    #     proxy_cache off;
    # }
}
```

- `client_max_body_size 50M` — permite subir EPUBs grandes
- `proxy_read_timeout 86400` — 24h, necesario para libros largos
- `proxy_buffering off` — necesario para que el log SSE fluya en tiempo real

---

## Arranque automático al encender el servidor

Para que una app arranque sola sin tener que conectarse por SSH:

```bash
sudo nano /etc/systemd/system/<nombre-app>.service
```

```ini
[Unit]
Description=<nombre-app>
After=network.target

[Service]
User=javigmdev
WorkingDirectory=/home/javigmdev/apps/<nombre-app>
ExecStart=/home/javigmdev/apps/<nombre-app>/venv/bin/python app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now <nombre-app>
```

---

## Comandos útiles

```bash
# Ver apps corriendo
sudo systemctl list-units --type=service --state=running

# Ver logs de una app
sudo journalctl -u <nombre-app> -f

# Recargar nginx tras cambios
sudo nginx -t && sudo systemctl reload nginx

# Ver puertos en uso
ss -tlnp
```
