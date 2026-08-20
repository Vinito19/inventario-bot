# GUÍA GOOGLE CLOUD — Subir tu bot a la nube GRATIS (para principiantes)

Esta guía explica, **sin tecnicismos**, cómo poner tu bot de inventario en la nube de Google
para que funcione **24 horas al día, los 7 días de la semana, gratis para siempre**,
sin que te cobren nada y sin perder tus datos.

Sigue los pasos **en orden**. Donde veas **🔴 IMPORTANTE**, léelo dos veces: ahí es
donde la gente comete errores que terminan en cobros.

---

## PARTE 0 — Lo que debes saber antes de empezar (explicado simple)

### ¿Qué vamos a crear?

Una **"computadora virtual"** es una computadora que no está en tu casa, sino en un
centro de datos de Google (en Estados Unidos). Tú la usas a distancia desde tu
celular o PC. Tu bot se instalará ahí y correrá todo el tiempo, aunque cierres tu PC.

### Palabras que verás y qué significan

| Palabra | Significado simple |
|---|---|
| **Cuenta de Google Cloud** | Tu cuenta en la página de Google para desarrolladores |
| **Proyecto** | Una "carpeta" donde viven todas tus cosas en Google Cloud |
| **VM / Instancia** | La computadora virtual (donde vivirá tu bot) |
| **Región** | El país/estado donde está físicamente esa computadora |
| **e2-micro** | El modelo de computadora MÁS pequeña y débil que ofrece Google. Es la única GRATIS para siempre |
| **Disco** | El disco duro de esa computadora (donde se guarda tu base de datos) |
| **Ingress / Egress** | Datos que *entran* a tu computadora (gratis) / datos que *salen* (tienen un límite gratis) |
| **Free Trial** | Crédito de $300 por 90 días que Google te regala al registrarte |
| **Always Free** | El free tier permanente: ciertos recursos gratis TODOS los meses, para siempre |
| **Billing** | La sección de tu cuenta donde está tu tarjeta y los cobros |

### Las DOS cosas gratis de Google (y por qué importa)

1. **Los $300 de regalo (90 días):** al registrarte, Google te da $300 para gastar en
   cualquier cosa durante 90 días. **No tocan tu tarjeta** mientras uses ese crédito.
2. **El "Always Free" (para siempre):** incluso después de los 90 días, Google te deja
   usar GRATIS todos los meses: una computadora e2-micro, un disco de 30GB y 200GB
   de tráfico de salida. **Es aquí donde vivirá tu bot para siempre, a $0.**

### Tu plan con fechas

| Día | Qué pasa |
|---|---|
| **Día 0 (hoy)** | Creas tu cuenta y tu computadora virtual. Tu bot empieza a funcionar. |
| **Días 1 a 87** | El bot corre 24/7. Todo cuesta $0. Tu tarjeta no se usa jamás. |
| **Día ~88** | 🔴 **IMPORTANTE:** debes hacer UN solo clic para "activar" tu cuenta paga (explicado en la Parte 9). Es seguro: el bot SIGUE costando $0. Si no lo haces, el día 90 el bot se apaga. |
| **Día 90+** | Tu cuenta está en modo "pago por uso", pero como tu bot está dentro del Always Free, **sigues pagando $0.00 para siempre**. |

**Resumen mental:** los primeros 90 días hay un colchón de $300 que te protege de
cualquier error. Después, tu bot está dentro del "Always Free", así que sigue gratis.

---

## PARTE 1 — Crear tu cuenta (10 minutos)

1. Abre tu navegador y ve a: **https://cloud.google.com**
2. Haz clic en **"Empezar gratis"** (Start free) o **"Probar gratis"**.
3. Inicia sesión con tu **cuenta de Google** (la misma de Gmail).
4. Te preguntarán:
   - **País:** Ecuador
   - **Términos y condiciones:** acéptalos (lee lo básico, no pasa nada)
5. 🔴 **IMPORTANTE — La tarjeta:** te pedirán una tarjeta de crédito o débito.
   - **NO te van a cobrar nada.** Solo la usan para verificar que eres una persona real.
   - Verás un **"cargo pendiente" de entre $0 y $1** en tu banco. **No es un cobro**: es una
     retención temporal que desaparece sola en 1 a 14 días hábiles (a veces tarda hasta
     un mes, depende de tu banco).
   - Las tarjetas **prepagadas** normalmente NO sirven.
   - La tarjeta debe ser **débito o crédito normal** (Visa/Mastercard) a tu nombre.
6. ¡Listo! Google te da automáticamente **$300 de crédito** válidos por 90 días.

> Si te aparece una ventana diciendo "**Activate**" o "**Upgrade**" (activar/actualizar
> a cuenta paga) durante la creación: **NO la toques todavía**. Ese clic lo haremos a
> propósito el día 88 (Parte 9).

---

## PARTE 2 — Crear tu "proyecto" (5 minutos)

1. Entra a la consola: **https://console.cloud.google.com**
2. Arriba a la izquierda verás un recuadro con el nombre de un proyecto
   (ej: "My First Project"). Haz clic ahí.
3. En la ventanita que aparece, haz clic en **"Nuevo proyecto"** (New Project).
4. **Nombre del proyecto:** escribe `inventario-bot`
5. Haz clic en **"Crear"** (Create).
6. Arriba a la izquierda, vuelve a hacer clic en el selector de proyectos y
   **selecciona `inventario-bot`** para entrar en él.

---

## PARTE 3 — Crear la computadora virtual (VM) — 🔴 LA PARTE MÁS DELICADA

Aquí es donde casi todos los errores de cobro ocurren. Sigue **exactamente** estos
valores. Cada valor está explicado y marcado si es peligroso equivocarse.

1. En el menú de tres líneas (☰) arriba a la izquierda, ve a:
   **Compute Engine → VM instances** (Computación → Máquinas virtuales).
2. Haz clic en **"Crear instancia"** (Create instance).
3. **Nombre:** escribe `bot-inventario` (o el que quieras).
4. **🔴 Región y zona (IMPORTANTE):**
   - **Región:** elige UNA de estas 3 exactas (son las únicas gratis):
     - `us-central1 (Iowa)`  ← **recomendada**
     - `us-west1 (Oregon)`
     - `us-east1 (South Carolina)`
   - **Zona:** cualquiera (ej: `us-central1-a`). Da igual cuál.
   - Cualquier otra región (Europa, Sudamérica, Asia) **COBRA**.
5. **Tipo de máquina (Machine type):**
   - Haz clic en el desplegable del tipo de máquina.
   - En la pestaña **"Uso general"** (General purpose), busca la serie **E2**.
   - Elige **`e2-micro`** (2 vCPU compartidas, 1 GB de memoria).
   - 🔴 Es la ÚNICA máquina gratis. Elegir otra = cobro.
6. **Disco de arranque (Boot disk):** haz clic en **"Cambiar"** (Change).
   - Pestaña **"Imágenes públicas"** (Public images).
   - **Sistema operativo:** `Ubuntu`
   - **Versión:** `Ubuntu 22.04 LTS` (o 24.04 LTS, ambas sirven)
   - **Tamaño:** escribe `30` GB
   - 🔴 **Tipo (Type):** aquí está la trampa #1. Verás un desplegable que dice
     **"Balanced persistent disk"** (disco equilibrado). **CÁMBIALO a:**
     **"Standard persistent disk"** (disco estándar).
     - El "Balanced" y el "SSD" **COBRAN**. El "Standard" es el único gratis.
   - Haz clic en **"Seleccionar"** (Select).
7. **🔴 Nivel de servicio de red (IMPORTANTE para que nunca te cobren por tráfico):**
   - Despliega **"Opciones avanzadas"** (Advanced options).
   - Entra en **"Redes"** (Networking).
   - En **"Interfaces de red"**, haz clic en el **lápiz (editar)**.
   - Busca **"Nivel de servicio de red"** (Network Service Tier) y cámbialo de
     "Premium" a **"Estándar"** (Standard).
   - Esto te da **200 GB de tráfico de salida gratis al mes** (tu bot usa menos de 2GB).
   - Guarda (Done).
8. **Firewall:** deja las dos casillas SIN marcar (HTTP y HTTPS). Tu bot no las necesita.
9. **Todo lo demás:** déjalo como está. No marques nada más.
10. Haz clic en **"Crear"** (Create) al final. Espera 1-2 minutos.

### 🔴 IMPORTANTE: vas a ver un costo de ~$7/mes. ¡NO te asustes!

Al crear, la consola muestra una **estimación** (~$7 al mes). Es el **precio de
catálogo**. Google lo anula automáticamente con el beneficio "Always Free": en tu
factura verás "$7.31 de costo" + "$7.31 de descuento" = **$0.00 total**.
Mientras hayas puesto e2-micro + región correcta + disco Standard, ese costo queda en $0.

## PARTE 4 — Instalar la alarma de gastos (10 minutos, UNO SÓLO)

Este es tu **cinturón de seguridad**. Si algún día algo llegara a costar aunque sea
$1, Google te avisará por correo al instante.

1. En el menú (☰), ve a **Facturación** (Billing).
2. En el menú lateral izquierdo, haz clic en **"Presupuestos y alertas"**
   (Budgets & alerts).
3. Haz clic en **"Crear presupuesto"** (Create budget).
4. **Nombre:** `alerta-gastos`
5. **Importe (amount):** escribe `1`
6. **Alertas:** marca las tres opciones: 50%, 90% y 100%. Pon tu correo.
7. Haz clic en **"Crear"** (Create).

> Si alguna vez te llega un correo de "alerta de gasto": no es una factura, es una
> alarma. Revisa la Parte 11 para saber qué hacer.

---

## PARTE 5 — Conectarte a tu computadora virtual (5 minutos)

Google te da una **ventana de comandos** dentro del navegador para controlar tu
computadora virtual. No necesitas instalar nada.

1. En el menú (☰), ve a **Compute Engine → VM instances**.
2. Verás tu máquina `bot-inventario` con un **círculo verde** (significa que está encendida).
3. A la derecha de tu máquina, haz clic en el botón **SSH**.
4. Se abrirá una ventana negra (una "terminal"). **Esa es tu computadora virtual.**

> **Dato tranquilizador:** tu bot se conecta HACIA afuera (a Telegram), así que no
> necesita una dirección fija. Si algún día reinicias la máquina y cambia su número
> de IP, no importa: el bot sigue funcionando igual.

---

## PARTE 6 — Instalar tu bot (10 minutos)

Ahora copiamos y pegamos unos comandos en la ventana SSH. **No te preocupes por
entenderlos**: solo cópialos, pégalos y presiona Enter.

**Paso 1 — Copia y pega esto, luego Enter** (instala las herramientas básicas):

```
sudo apt-get update && sudo apt-get install -y git
```

**Paso 2 — Copia y pega esto, luego Enter** (descarga tu bot desde GitHub):

```
git clone https://github.com/Vinito19/inventario-bot.git
```

**Paso 3 — Copia y pega esto, luego Enter** (instala el bot):

```
cd inventario-bot && bash install.sh
```

**Paso 4 — Te hará 3 preguntas.** Responde así:

| Pregunta | Qué escribir |
|---|---|
| `Ingresa tu BOT_TOKEN de Telegram:` | Tu token (el código largo de @BotFather, ej: `123456:ABC...`) |
| `Ingresa tu ADMIN_IDS (separados por coma):` | Tu número de usuario (ej: `123456789`) |
| `Hora del backup diario (HH:MM, default 00:00):` | Presiona Enter para aceptar `00:00` |

**Paso 5 — Verás la pantalla final:** `BOT DESPLEGADO CORRECTAMENTE ✅`

Tu bot ya está **corriendo 24/7 en la nube**.

---

## PARTE 7 — Verificar que funciona (5 minutos)

1. Abre Telegram y escribe `/start` a tu bot.
2. El bot debe responder con el menú.
3. Prueba agregar un repuesto, buscar, editar, etc. Todo debe funcionar igual.
4. El **backup diario** te llegará cada día a las **00:00** (hora de Ecuador) en tu
   chat de Telegram, como un archivo `.zip`.

**Comandos útiles en la ventana SSH (por si acaso):**

| Para... | Escribe |
|---|---|
| Ver si el bot está corriendo | `sudo systemctl status inventario-bot` |
| Ver los registros en vivo | `sudo journalctl -u inventario-bot -f` |
| Actualizar el bot (tras un fix) | `bash update.sh` |
| Reiniciar el bot | `sudo systemctl restart inventario-bot` |

> Si el bot se cae por cualquier razón, Google lo **reinicia solo** automáticamente
> (el servicio está configurado con `Restart=always`).

## PARTE 8 — El día a día (qué hacer cuando corrijas un bug)

Cuando necesites corregir algo del bot (como hiciste con los botones), el flujo es:

1. **Corrige en tu PC** (en la carpeta `Inventario de Repuesto VCH`).
2. **Sube el cambio a GitHub** (desde Git CMD en tu PC):

```
git add .
git commit -m "describe el cambio"
git push origin main
```

3. **Actualiza la máquina virtual** (en la ventana SSH de Google):

```
bash update.sh
```

En ~5 segundos el bot vuelve a estar en línea con el arreglo.

**Reglas de oro para el día a día:**

- 🔴 **NUNCA edites archivos dentro de la ventana SSH** (nada de `nano` o `vim`).
  Todo cambio se hace en tu PC y se sube con `git`. Si editas dentro de la VM, la
  próxima actualización fallará.
- **Tus datos están a salvo:** la base de datos (`inventario.db`) NO está en GitHub,
  así que actualizar el código jamás borra tu inventario.
- **Tu backup diario** llega cada día a tu chat de Telegram (el archivo `.zip`).
  Guárdalos: son tu seguro de vida si algún día algo sale mal.

---

## PARTE 9 — 🔴 LA FECHA IMPORTANTE: el día 90 (y qué hacer el día ~88)

**Esto es lo único que puede apagar tu bot para siempre. Léelo bien.**

Google Cloud tiene dos etapas:

- **Etapa 1 (días 0 a 90):** estás en el "Free Trial" con $300 de crédito. Todo cubierto.
- **Etapa 2 (después del día 90):** el Free Trial se cierra SOLO. Google **apaga tu
  bot** y, 30 días después, **borra tus datos para siempre**... A MENOS que hayas
  hecho UN clic para pasar a cuenta normal.

**🔴 El día 88, haz esto:**

1. Entra a la consola: **https://console.cloud.google.com**
2. Arriba verás un botón que dice **"Activate"** (Activar) o **"Upgrade"** (Actualizar).
3. Haz clic en él. Acepta el aviso.
4. Listo. Ahora tu cuenta es "pago por uso".

**¿Y eso no me va a cobrar? NO.** Al pasar a "pago por uso", Google aplica el
**Always Free**: como tu bot usa exactamente lo que está dentro de lo gratis
(e2-micro + disco Standard 30GB + Standard tier), **sigues en $0.00 para siempre**.
Además, te quedan los $300 restantes como colchón por si algo se dispara.

**¿Qué pasa si me olvido?** El día 90 el bot se apaga. Tienes 30 días extra para
hacer el clic y **recuperar todo**. Después de esos 30 días, los datos se borran
permanentemente. Por eso el día 88 es importante.

> **Recuerda:** el único momento en que esta cuenta cobra algo es si creas recursos
> por FUERA del Always Free. Las 7 reglas de oro (Parte 10) te protegen de eso.

## PARTE 10 — Las 7 reglas de oro para que NUNCA te cobren

Copia mentalmente estas reglas. Son las únicas 7 formas en que alguien se sale de
lo gratis y aparece un cobro:

1. 🔴 **Nunca crees una segunda máquina virtual.** Solo tienes derecho a UNA gratis.
   Cada VM extra = cobro.
2. 🔴 **Nunca cambies la región, el tipo de máquina ni el disco** después de creado.
   Si un día tocas esas opciones y eliges otra cosa, empieza el cobro.
3. 🔴 **Nunca aumentes el disco más allá de 30GB** ni elijas disco "Balanced"/"SSD".
4. 🔴 **No crees cosas nuevas** (buckets de almacenamiento, bases de datos Cloud SQL,
   direcciones IP fijas, copias de seguridad "snapshots", dominios). Todo eso cobra.
   Tu bot solo necesita: 1 VM + su disco.
5. 🔴 **No marques "Activate"/"Upgrade" en ningún momento** EXCEPTO el día 88
   (Parte 9), que es el único clic intencional y seguro.
6. 🔴 **No expongas claves ni tokens.** Tu `BOT_TOKEN` y cualquier clave viven solo en
   tu `.env` (que no está en GitHub). No los pegues en foros ni en chats.
7. ✅ **Revisa la factura 1 vez por semana** (Parte 11). Es gratis y te da tranquilidad.

---

## PARTE 11 — Cómo comprobar que todo sigue en $0.00 (1 vez por semana)

1. Entra a la consola y ve a **Facturación → Informes** (Billing → Reports).
2. Busca tu proyecto `inventario-bot`.
3. **Verás algo así:**

| Concepto | Valor |
|---|---|
| Costo (precio de catálogo) | ~$7.31 |
| Descuento (Always Free "Savings") | −$7.31 |
| **Total** | **$0.00** ✅ |

4. Mientras el Total sea **$0.00**, estás perfecto.
5. Si un día la alarma (Parte 4) te avisa o ves un Total mayor a $0:
   - Ve a la lista de máquinas virtuales y **revisa si hay MÁS de una**.
   - Revisa si algún disco creció o si hay "snapshots".
   - Borra lo que sobra (botón eliminar). Con la alarma de $1, el máximo daño
     posible es $1, así que no hay motivo de pánico.

---

## PARTE 12 — Antes de empezar: checklist final

- [ ] Tengo mi tarjeta de débito/crédito normal a la mano (para verificar, no para pagar).
- [ ] Tengo mi `BOT_TOKEN` de @BotFather y mi número de usuario (ADMIN_IDS) copiados.
- [ ] Mi código está subido a GitHub (repo `Vinito19/inventario-bot`).
- [ ] Entendí que el día ~88 debo hacer el clic de "Activate".

**Cuando tengas todo listo, sigue la Parte 1. ¡Éxito! 🎉**

---

## ANEXO — Glosario en lenguaje de todos los días

| Término | Qué significa en simple |
|---|---|
| **Nube** | Computadoras de otras personas (Google) a las que te conectas por internet |
| **VM / Instancia** | Una de esas computadoras, alquilada por ti, encendida 24/7 |
| **e2-micro** | El modelo más pequeño y barato (gratis) de esas computadoras |
| **Región / Zona** | Dónde está físicamente la computadora (ciudad + edificio) |
| **Disco Standard** | El disco duro normal (lento pero gratis). Los "SSD/Balanced" son los rápidos que cobran |
| **Boot disk / Disco de arranque** | El disco donde está instalado el sistema (Ubuntu) y tus datos |
| **Ubuntu** | El "Windows" de tu computadora virtual (gratis y de código abierto) |
| **SSH** | La ventana negra que te permite darle órdenes a la VM desde tu navegador |
| **Ingress** | Datos que entran a tu VM desde internet (siempre gratis) |
| **Egress** | Datos que salen de tu VM hacia internet (gratis hasta 200GB/mes en tier Standard) |
| **Network Service Tier (Estándar)** | La "ruta" por la que sale tu tráfico. Elegir Estándar = 200GB gratis |
| **Free Trial** | Los $300 de regalo por 90 días al registrarte |
| **Always Free** | La lista de cosas gratis TODOS los meses, para siempre (incluye tu VM) |
| **Billing / Facturación** | La parte de tu cuenta donde viven tu tarjeta y los informes de costo |
| **Budget / Presupuesto** | Tu alarma: te avisa por correo si algo llega a costar |
| **Snapshot** | Una foto del disco (copia de seguridad). Cobra, evítala |
| **IP estática** | Una dirección fija para tu VM. No la necesitas (y algunas cobran) |
| **Repositorio / Repo** | Tu carpeta del código en GitHub |
| **Token** | La llave secreta de tu bot (solo tú debes tenerla) |
| **ADMIN_IDS** | Tu número de usuario de Telegram (el que manda en el bot) |

---

*Guía creada para el bot "Inventario de Repuesto VCH". Si algo no funciona o te llega
una alerta de gasto, avísame y lo revisamos juntos.*