# GUÍA GOOGLE CLOUD — Poner tu bot en la nube GRATIS (paso a paso)

Esta guía te lleva de la mano, **sin palabras raras**, desde cero hasta tener tu
bot de inventario funcionando **24 horas al día, todos los días, gratis para
siempre**, sin cobros y sin perder tus datos.

**Cómo usar esta guía:** hay 3 tipos de acción, fáciles de distinguir:

- **"Haz clic en..."** → es una ventana o página del navegador.
- **"Escribe esto"** → es un cuadro gris con UN comando. Lo copias, lo pegas en
  la ventana negra y presionas **Enter**. Cada cuadro es **un solo comando**;
  hazlos **uno por uno**, esperando a que termine cada uno.
- **"Pregunta"** → es algo que el bot te preguntará. Tú respondes con el teclado.

Cuando veas **IMPORTANTE:**, léelo dos veces. Ahí es donde la gente comete
errores que terminan en cobros.

---

## PARTE 1 — Lo que necesitas tener a mano (antes de empezar)

Reúne esto primero:

1. **Tu tarjeta de débito o crédito normal** (Visa/Mastercard) a tu nombre.
   Las tarjetas **prepagadas normalmente no sirven**.
2. **Tu BOT_TOKEN** de Telegram (el código largo de @BotFather, como `123456:ABC...`).
3. **Tu número de usuario de Telegram:** `6296592750` (tu propio número, ya
   configurado como administrador).
4. **Tu cuenta de Google** (la de Gmail).

> No necesitas comprar nada. Todo lo de esta guía es gratis.

---

## PARTE 2 — Crear tu cuenta de Google Cloud (10 minutos)

1. Abre tu navegador y entra a: **https://cloud.google.com**
2. Haz clic en **"Empezar gratis"** (o "Start free").
3. Inicia sesión con tu **Gmail**.
4. Te preguntarán:
   - **País:** Ecuador
   - **Términos y condiciones:** acéptalos.
5. **IMPORTANTE — La tarjeta:** te pedirán una tarjeta de débito o crédito.
   - **NO te van a cobrar nada.** Solo la usan para verificar que eres una
     persona real.
   - Verás un **"cargo pendiente" de entre $0 y $1** en tu banco. **No es un
     cobro**: es una retención temporal que desaparece sola en 1 a 14 días
     hábiles (a veces tarda un poco más, depende de tu banco).
6. ¡Listo! Google te regala **$300 de crédito** válidos por 90 días.

> Si te aparece una ventana que dice **"Activate"** o **"Upgrade"**: **NO la
> toques todavía**. Ese botón lo usaremos a propósito el día 88 (Parte 11).

---

## PARTE 3 — Crear tu "proyecto" (5 minutos)

Un proyecto es la carpeta donde viven todas tus cosas en Google Cloud.

1. Entra a: **https://console.cloud.google.com**
2. Arriba a la izquierda hay un recuadro con el nombre de un proyecto
   (ej: "My First Project"). Haz clic ahí.
3. En la ventanita que aparece, haz clic en **"Nuevo proyecto"**.
4. **Nombre del proyecto:** escribe `inventario-bot`
5. Haz clic en **"Crear"**.
6. Arriba a la izquierda, vuelve a hacer clic en el recuadro del proyecto y
   **selecciona `inventario-bot`** para entrar en él.

---

## PARTE 4 — Crear la computadora virtual (la parte más delicada)

Aquí es donde ocurren casi todos los errores de cobro. Sigue **exactamente**
estos valores. Cada valor importante está explicado.

1. En el menú de tres líneas (☰) arriba a la izquierda, ve a:
   **Compute Engine → VM instances**.
2. Haz clic en **"Crear instancia"**.
3. **Nombre:** escribe `bot-inventario`
4. **IMPORTANTE — Región y zona:** elige **UNA** de estas 3 regiones (son las
   únicas gratis):
   - `us-central1 (Iowa)`  ← **recomendada**
   - `us-west1 (Oregon)`
   - `us-east1 (South Carolina)`
   - Cualquier otra región (Europa, Sudamérica, Asia) **COBRA**.
   - La zona: da igual cuál elijas.
5. **Tipo de máquina:** haz clic en el desplegable, ve a la pestaña
   **"Uso general"**, busca la serie **E2** y elige **`e2-micro`**
   (2 vCPU compartidas, 1 GB de memoria).
   - **IMPORTANTE:** es la ÚNICA máquina gratis. Elegir otra = cobro.
6. **Disco de arranque:** haz clic en **"Cambiar"**.
   - Pestaña **"Imágenes públicas"**.
   - **Sistema operativo:** `Ubuntu`
   - **Versión:** `Ubuntu 22.04 LTS` (o 24.04 LTS, ambas sirven)
   - **Tamaño:** escribe `30` GB
   - **IMPORTANTE — Tipo:** verás un desplegable que dice
     **"Balanced persistent disk"**. **CÁMBIALO a "Standard persistent disk"**.
     - El "Balanced" y el "SSD" **COBRAN**. El "Standard" es el único gratis.
   - Haz clic en **"Seleccionar"**.
7. **IMPORTANTE — Nivel de servicio de red** (para que el tráfico no cobre):
   - Despliega **"Opciones avanzadas"**.
   - Entra en **"Redes"** (Networking).
   - En **"Interfaces de red"**, haz clic en el **lápiz** (editar).
   - Busca **"Nivel de servicio de red"** y cámbialo de "Premium" a
     **"Estándar"** (Standard).
   - Esto te da **200 GB de tráfico de salida gratis al mes** (tu bot usa
     menos de 2 GB).
   - Guarda (Done).
8. **Firewall:** deja las dos casillas SIN marcar (HTTP y HTTPS). Tu bot no las
   necesita.
9. Todo lo demás: déjalo como está. No marques nada más.
10. Haz clic en **"Crear"**. Espera 1 a 2 minutos.

> **IMPORTANTE — Vas a ver un costo de ~$7/mes. ¡NO te asustes!**
> Es el **precio de catálogo**. Google lo anula automáticamente con el beneficio
> "Always Free": en tu factura verás "$7 de costo" + "$7 de descuento" =
> **$0.00 total**. Mientras hayas puesto e2-micro + una de las 3 regiones +
> disco Standard, ese costo queda en $0.

---

## PARTE 5 — Instalar tu alarma de gastos (10 minutos, se hace UNA vez)

Es tu **cinturón de seguridad**: si algún día algo llegara a costar $1, Google
te avisa por correo al instante.

1. En el menú (☰), ve a **Facturación** (Billing).
2. En el menú lateral izquierdo, haz clic en **"Presupuestos y alertas"**.
3. Haz clic en **"Crear presupuesto"**.
4. **Nombre:** `alerta-gastos`
5. **Importe (amount):** escribe `1`
6. **Alertas:** marca las tres opciones (50%, 90% y 100%). Pon tu correo.
7. Haz clic en **"Crear"**.

> Si algún día te llega un correo de "alerta de gasto": **no es una factura**,
> es una alarma. Revisa la Parte 13 para saber qué hacer.

---

## PARTE 6 — Conectarte a tu computadora virtual (5 minutos)

Google te da una **ventana negra dentro del navegador** para controlar tu
computadora virtual. No instales nada.

1. En el menú (☰), ve a **Compute Engine → VM instances**.
2. Verás tu máquina `bot-inventario` con un **círculo verde** (significa que
   está encendida).
3. A la derecha de tu máquina, haz clic en el botón **SSH**.
4. Se abrirá una ventana negra (una "terminal"). **Esa es tu computadora
   virtual.** Desde ahora, cuando la guía diga "pega esto en la ventana", es
   aquí.

> **Dato tranquilizador:** tu bot se conecta HACIA afuera (a Telegram), así que
> no necesita una dirección fija. Si la IP cambia al reiniciar, no importa: el
> bot sigue funcionando igual.

---

## PARTE 7 — Instalar tu bot (10 minutos)

Desde ahora, **cada cuadro gris es UN solo comando**. Cópialo, pégalo en la
ventana negra y presiona **Enter**. Espera a que termine antes de pasar al
siguiente. Nunca pegues dos cuadros juntos.

**Paso 1 — Actualiza el sistema.** Copia, pega, Enter:

```
sudo apt-get update
```

Espera a que termine (1 a 3 minutos).

**Paso 2 — Instala la herramienta para descargar el bot.** Copia, pega, Enter:

```
sudo apt-get install -y git
```

**Paso 3 — Descarga tu bot desde GitHub.** Copia, pega, Enter:

```
git clone https://github.com/Vinito19/inventario-bot.git
```

**Paso 4 — Entra a la carpeta del bot.** Copia, pega, Enter:

```
cd inventario-bot
```

**Paso 5 — Instala el bot.** Copia, pega, Enter:

```
bash install.sh
```

Se instalará solo (esto tarda 2 a 4 minutos, no lo interrumpas).

**Paso 6 — Te hará 3 preguntas.** Responde así:

| Pregunta | Qué escribir |
|---|---|
| `Ingresa tu BOT_TOKEN de Telegram:` | Tu token (el código largo de @BotFather) |
| `Ingresa tu ADMIN_IDS (separados por coma):` | `6296592750` |
| `Hora del backup diario (HH:MM, default 00:00):` | Presiona **Enter** (deja `00:00`) |

**Paso 7 — Verás la pantalla final:** `BOT DESPLEGADO CORRECTAMENTE`.

Tu bot ya está **corriendo 24/7 en la nube**. No necesitas dejar tu PC encendida.

---

## PARTE 8 — Comprobar que el bot funciona (5 minutos)

1. Abre Telegram y busca tu bot (el mismo de siempre).
2. Escribe `/start`.
3. El bot debe responder con el menú.
4. Prueba: agregar un repuesto, buscar, editar. Todo debe funcionar igual.
5. El **backup diario** te llegará cada día a las **00:00** (hora de Ecuador),
   como un archivo `.zip` en tu chat de Telegram.

---

## PARTE 9 — Comandos útiles (por si acaso)

Guárdalos. Todos se escriben en la ventana negra (SSH), **uno por uno**.

**Ver si el bot está corriendo.** Copia, pega, Enter:

```
sudo systemctl status inventario-bot
```

**Ver los registros del bot en vivo.** Copia, pega, Enter:

```
sudo journalctl -u inventario-bot -f
```

Para salir de los registros, presiona `Ctrl + C`.

**Reiniciar el bot.** Copia, pega, Enter:

```
sudo systemctl restart inventario-bot
```

> Si el bot se cae por cualquier motivo, Google lo **reinicia solo**
> automáticamente. No tienes que hacer nada.

---

## PARTE 10 — El día a día: cuando corrijas un bug

Cuando necesites arreglar algo del bot, el flujo es siempre este:

**1. Corriges en tu PC** (en la carpeta `Inventario de Repuesto VCH`).

**2. Subes el cambio a GitHub** desde Git CMD en tu PC, **un comando a la vez**:

```
git add .
```

```
git commit -m "describe el cambio"
```

```
git push origin main
```

**3. Actualizas la máquina virtual** en la ventana negra de Google:

```
bash update.sh
```

En ~5 segundos el bot vuelve a estar en línea con el arreglo.

**Reglas de oro para el día a día:**

- **NUNCA edites archivos dentro de la ventana negra** (nada de `nano` o
  `vim`). Todo cambio se hace en tu PC y se sube con `git`. Si editas dentro de
  la máquina, la próxima actualización fallará.
- **Tus datos están a salvo:** la base de datos (`inventario.db`) NO está en
  GitHub, así que actualizar el código jamás borra tu inventario.
- **Tu backup diario** llega cada día a tu chat de Telegram (archivo `.zip`).
  Guárdalos: son tu seguro de vida si algún día algo sale mal.

---

## PARTE 11 — IMPORTANTE: la fecha del día 90 (y qué hacer el día ~88)

**Esto es lo único que puede apagar tu bot para siempre. Léelo bien.**

Google Cloud tiene dos etapas:

- **Etapa 1 (días 0 a 90):** estás en el "Free Trial" con $300 de crédito.
  Todo cubierto, tu tarjeta no se usa.
- **Etapa 2 (después del día 90):** el Free Trial se cierra **solo**. Google
  **apaga tu bot** y, 30 días después, **borra tus datos para siempre**...
  A MENOS que hayas hecho **UN clic** para pasar a cuenta normal.

**El día ~88, haz esto:**

1. Entra a: **https://console.cloud.google.com**
2. Arriba verás un botón que dice **"Activate"** (Activar) o **"Upgrade"**
   (Actualizar).
3. Haz clic en él. Acepta el aviso.
4. Listo. Ahora tu cuenta es "pago por uso".

**¿Eso no me va a cobrar? NO.** Al pasar a "pago por uso", Google aplica el
**Always Free**: como tu bot usa exactamente lo que está dentro de lo gratis
(e2-micro + disco Standard 30GB + tráfico Estándar), **sigues en $0.00 para
siempre**. Además te quedan los $300 restantes como colchón.

**¿Qué pasa si me olvido?** El día 90 el bot se apaga. Tienes **30 días extra**
para hacer el clic y **recuperar todo**. Después de esos 30 días, los datos se
borran permanentemente. Por eso el día 88 es importante: ponte una alarma.

---

## PARTE 12 — Las 7 reglas de oro para que NUNCA te cobren

Estas son las únicas 7 formas en que alguien se sale de lo gratis y aparece un
cobro:

1. **Nunca crees una segunda máquina virtual.** Solo tienes derecho a UNA
   gratis. Cada VM extra = cobro.
2. **Nunca cambies la región, el tipo de máquina ni el disco** después de
   crearlo. Si un día tocas esas opciones y eliges otra cosa, empieza el cobro.
3. **Nunca aumentes el disco más allá de 30GB** ni elijas disco
   "Balanced"/"SSD".
4. **No crees cosas nuevas** (buckets de almacenamiento, bases de datos Cloud
   SQL, direcciones IP fijas, copias de seguridad "snapshots", dominios). Todo
   eso cobra. Tu bot solo necesita: 1 VM + su disco.
5. **No toques "Activate"/"Upgrade"** en ningún momento EXCEPTO el día 88
   (Parte 11), que es el único clic intencional y seguro.
6. **No compartas claves ni tokens.** Tu `BOT_TOKEN` vive solo en tu archivo
   `.env` (que no está en GitHub). No lo pegues en foros ni chats.
7. **Revisa la factura 1 vez por semana** (Parte 13). Es gratis y te da
   tranquilidad.

---

## PARTE 13 — Comprobar que todo sigue en $0.00 (1 vez por semana)

1. Entra a la consola y ve a **Facturación → Informes**.
2. Busca tu proyecto `inventario-bot`.
3. Verás algo así:

| Concepto | Valor |
|---|---|
| Costo (precio de catálogo) | ~$7.31 |
| Descuento (Always Free "Savings") | −$7.31 |
| **Total** | **$0.00** |

4. Mientras el Total sea **$0.00**, estás perfecto.
5. Si un día la alarma (Parte 5) te avisa o ves un Total mayor a $0:
   - Ve a la lista de máquinas virtuales y **revisa que haya solo UNA**.
   - Revisa si algún disco creció o si hay "snapshots".
   - Borra lo que sobra (botón eliminar). Con la alarma de $1, el máximo daño
     posible es $1. No hay motivo de pánico.

---

## PARTE 14 — Lista final antes de empezar

- [ ] Tengo mi tarjeta de débito/crédito normal a la mano (para verificar, no para pagar).
- [ ] Tengo mi `BOT_TOKEN` de @BotFather copiado.
- [ ] Sé que mi número de administrador es `6296592750`.
- [ ] Mi código ya está en GitHub (repo `Vinito19/inventario-bot`).
- [ ] Entendí que el día ~88 debo hacer el clic de "Activate" (Parte 11).

**Cuando tengas todo listo, empieza por la Parte 1. ¡Éxito!**

---

## ANEXO — Glosario en lenguaje de todos los días

| Término | Qué significa en simple |
|---|---|
| **Nube** | Computadoras de otras personas (Google) a las que te conectas por internet |
| **VM / Instancia** | Una de esas computadoras, alquilada por ti, encendida 24/7 |
| **e2-micro** | El modelo más pequeño y barato (gratis) de esas computadoras |
| **Región / Zona** | Dónde está físicamente la computadora (ciudad + edificio) |
| **Disco Standard** | El disco duro normal (lento pero gratis). Los "SSD/Balanced" son los rápidos que cobran |
| **Ubuntu** | El "Windows" de tu computadora virtual (gratis y de código abierto) |
| **SSH** | La ventana negra que te permite darle órdenes a la VM desde tu navegador |
| **Ingress** | Datos que entran a tu VM desde internet (siempre gratis) |
| **Egress** | Datos que salen de tu VM hacia internet (gratis hasta 200GB/mes en tier Estándar) |
| **Nivel de servicio de red (Estándar)** | La "ruta" por la que sale tu tráfico. Elegir Estándar = 200GB gratis |
| **Free Trial** | Los $300 de regalo por 90 días al registrarte |
| **Always Free** | La lista de cosas gratis TODOS los meses, para siempre (incluye tu VM) |
| **Billing / Facturación** | La parte de tu cuenta donde viven tu tarjeta y los informes de costo |
| **Presupuesto (Budget)** | Tu alarma: te avisa por correo si algo llega a costar |
| **Snapshot** | Una foto del disco (copia de seguridad). Cobra, evítala |
| **IP estática** | Una dirección fija para tu VM. No la necesitas (y algunas cobran) |
| **Repositorio / Repo** | Tu carpeta del código en GitHub |
| **Token** | La llave secreta de tu bot (solo tú debes tenerla) |
| **ADMIN_IDS** | Tu número de usuario de Telegram (el que manda en el bot) |

---

*Guía creada para el bot "Inventario de Repuesto VCH". Si algo no funciona o te
llega una alerta de gasto, avísame y lo revisamos juntos.*