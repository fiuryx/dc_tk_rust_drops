# Rust Drops Discord Bot

Bot de Discord que detecta automáticamente **nuevos Rust Drops** en:

* Twitch
* Kick

El bot monitoriza las páginas oficiales de Facepunch y envía una alerta al servidor cuando detecta cambios o nuevos eventos.

---

# Características

* Detección automática de **nuevos Rust Drops**
* Soporte para **Twitch y Kick**
* Sistema de **notificaciones por DM**
* Comandos slash de Discord
* Deploy sencillo en **Railway**
* Monitorización con **UptimeRobot**
* Sistema anti-spam (solo avisa si hay cambios)

---

# Requisitos

* Python 3.10+
* Cuenta en GitHub
* Cuenta en Railway
* Bot de Discord
* Canal de Discord para alertas

---

# 1. Crear el bot de Discord

Ir a:

https://discord.com/developers/applications

Crear una nueva aplicación.

Luego ir a **Bot → Add Bot**

---

## Activar Intents necesarios

En la sección **Bot → Privileged Gateway Intents**

Activar:

* Message Content Intent

---

# 2. Invitar el bot al servidor

Generar el link de invitación con permisos.

Permisos necesarios:

* View Channels
* Send Messages
* Embed Links
* Read Message History

Permisos en número entero:

```
2147485696
```

Link de invitación ejemplo:

```
https://discord.com/oauth2/authorize?client_id=TU_CLIENT_ID&permissions=2147485696&scope=bot%20applications.commands
```

---

# 3. Obtener el ID del canal

En Discord:

1. Activar **Modo desarrollador**
2. Click derecho en el canal
3. **Copiar ID**

---

# 4. Subir el proyecto a GitHub

Clonar el repositorio:

```
git clone https://github.com/tuusuario/dc_tk_rust_drops
```

Estructura del proyecto:

```
dc_tk_rust_drops
│
├── bot.py
├── requirements.txt
├── Procfile
├── last_drops.json
├── subscribers.json
```

Subir cambios:

```
git add .
git commit -m "initial version"
git push
```

---

# 5. Deploy en Railway

Ir a:

https://railway.app

### Crear proyecto

1. New Project
2. Deploy from GitHub Repo
3. Seleccionar el repositorio

Railway detectará automáticamente Python.

---

# 6. Variables de entorno

En Railway → **Variables**

Añadir:

```
DISCORD_TOKEN=tu_token_de_bot
CHANNEL_ID=id_del_canal
```

Dónde conseguir el token:

Discord Developer Portal → Bot → **Reset Token**

---

# 7. Configurar Procfile

El proyecto incluye:

```
worker: python bot.py
```

Railway ejecutará automáticamente el bot.

---

# 8. Reiniciar el deploy

Después de añadir variables:

```
Deploy → Redeploy
```

En los logs debería aparecer:

```
Bot conectado como ...
X comandos sincronizados
```

---

# 9. Monitorización con UptimeRobot

Para asegurarse de que Railway reinicie el bot si se detiene.

Crear cuenta en:

https://uptimerobot.com/

Crear monitor:

* Tipo: HTTP
* URL: cualquier endpoint público (ej: github o web propia)
* Intervalo: 5 minutos

Esto evita que Railway ponga el proyecto en idle.

---

# 10. Comandos del bot

## /drops

Muestra el estado actual de los drops.

Ejemplo:

```
/drops
```

Resultado:

```
Twitch: Activo/Inactivo
Kick: Activo/Inactivo
```

---

## /forcecheck

Fuerza una comprobación manual.

```
/forcecheck
```

---

## /notify on

Suscribirse a notificaciones por DM.

```
/notify on
```

---

## /notify off

Cancelar notificaciones.

```
/notify off
```

---

# 11. Cómo funciona el bot

El bot comprueba cada 10 minutos:

## Twitch

https://twitch.facepunch.com/

Detecta:

* activación de drops
* cambios en la página
* cambios de campaña

---

## Kick

https://kick.facepunch.com/

Detecta:

* activación de drops
* cambios en la página
* nuevos streamers
* nuevos eventos

---

# 12. Archivos de datos

## last_drops.json

Guarda el último estado detectado.

Evita enviar alertas repetidas.

---

## subscribers.json

Lista de usuarios suscritos a notificaciones.

---

# 13. Logs en Railway

Ver logs en:

```
Railway → Deployments → View Logs
```

Ejemplo correcto:

```
Bot conectado como RustDropsBot
3 comandos sincronizados
```

---

# 14. Problemas comunes

### PrivilegedIntentsRequired

Activar:

```
Message Content Intent
```

en Discord Developer Portal.

---

### Commands not showing

Esperar 1-2 minutos después del deploy.

O reiniciar el bot.

---

### Bot no envía mensajes

Verificar:

* ID del canal correcto
* permisos del bot en el canal
* 
---

# Licencia

MIT License
