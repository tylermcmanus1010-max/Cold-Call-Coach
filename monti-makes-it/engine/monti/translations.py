"""Spanish for the interface. Not for anything a client wrote.

WHAT IS IN HERE
    Interface language: navigation, buttons, labels, status words, headings,
    and the body copy this site wrote about itself.

WHAT IS NOT, AND MUST NEVER BE
    Anything a client typed. Company names, product names, specifications,
    notes, the answer to "what do you sell". §1.6 forbids machine-translating
    a client's own words, and putting one of their sentences in this file would
    be exactly that. `monti/i18n.py` enforces it structurally; this file must
    not undermine it by carrying a client's phrasing as a key.

    Identifiers. Timezone names (America/New_York), references (MMI-…), SKUs,
    version hashes, currency codes. They are the same in every language because
    they are not words.

    Money. Every figure appears identically on both sides of an entry, and
    `i18n._validate` refuses to load this module if one does not — a crash on
    boot rather than a wrong price on a client's screen.

REGISTER
    Second person singular ("tú"), matching the English, which is deliberately
    direct — "we'd rather make everything you sell for the next ten years than
    squeeze you once" is not a page that would say "usted". Terminology follows
    trade Spanish rather than literal translation: flete, herramental, plazo de
    entrega, costo puesto en destino.

COVERAGE
    Partial and honest. What is not here renders in English, visibly, and
    `i18n.coverage()` lists it. A gap someone can see is worth more than a
    machine-translated sentence nobody checked.
"""

ES = {
    # ---- shells and navigation -------------------------------------------
    "Home": "Inicio",
    "Overview": "Resumen",
    "Catalogue": "Catálogo",
    "How it works": "Cómo funciona",
    "Membership": "Membresía",
    "Member login": "Acceso de miembros",
    "Member portal": "Portal de miembros",
    "Admin portal": "Portal de administración",
    "Public site": "Sitio público",
    "Sign out": "Cerrar sesión",
    "Password": "Contraseña",
    "Questions": "Preguntas",
    "Contact": "Contacto",
    "Contact us": "Contáctanos",
    "Disclaimers": "Avisos legales",
    "Privacy": "Privacidad",
    "Request a quote": "Solicitar cotización",
    "Request a Quote": "Solicitar cotización",
    "Apply for membership": "Solicitar membresía",
    "Apply for Membership": "Solicitar membresía",
    "Share this page": "Compartir esta página",
    "Anything else": "Cualquier otra cosa",
    "This cycle": "Este ciclo",
    "Manufacturer · direct": "Fabricante · directo",
    "Monti Makes It · we are the manufacturer": "Monti Makes It · somos el fabricante",

    # member portal
    "My products": "Mis productos",
    "Describe it badly": "Descríbelo mal",
    "My catalog": "Mi catálogo",
    "Purchased items": "Artículos comprados",
    "Orders": "Pedidos",
    "Order": "Pedido",
    "My ledger": "Mi libro mayor",
    "Current order": "Pedido actual",
    "Membership record": "Registro de membresía",

    # admin
    "Operations": "Operaciones",
    "Dashboard": "Panel",
    "Revenue": "Ingresos",
    "Master ledger": "Libro mayor general",
    "Pricing desk": "Mesa de precios",
    "Incoming quotes": "Cotizaciones entrantes",
    "Quote queue": "Cola de cotizaciones",
    "Order log": "Registro de pedidos",
    "Applications": "Solicitudes",
    "Relationships": "Relaciones",
    "Calendar": "Calendario",
    "Consultation hours": "Horario de consultas",
    "Open a client portal": "Abrir un portal de cliente",
    "Product": "Producto",
    "Private catalog": "Catálogo privado",
    "System": "Sistema",
    "Email log": "Registro de correos",
    "Settings": "Configuración",
    "Admin": "Administración",
    "Scheduling": "Agenda",
    "CRM": "CRM",

    # ---- actions ----------------------------------------------------------
    "Save": "Guardar",
    "Search": "Buscar",
    "Add to order": "Añadir al pedido",
    "Buy this route": "Comprar esta ruta",
    "Create order →": "Crear pedido →",
    "Remove": "Quitar",
    "Submit": "Enviar",
    "Submit my application": "Enviar mi solicitud",
    "Send": "Enviar",
    "Cancel": "Cancelar",
    "Continue": "Continuar",
    "Back": "Atrás",
    "Read →": "Leer →",
    "See it": "Verlo",
    "Read them now": "Léelos ahora",
    "Read them →": "Léelos →",
    "See your record →": "Ver tu registro →",
    "Read the questions page →": "Ver la página de preguntas →",
    "Request a box": "Solicitar una caja",
    "Stop offering": "Dejar de ofrecer",
    "Add this window": "Añadir este horario",
    "Block these dates": "Bloquear estas fechas",
    "Add event": "Añadir evento",
    "Today": "Hoy",
    "Next step is payment. Nothing is charged until you complete checkout.":
        "El siguiente paso es el pago. No se cobra nada hasta que completes el pago.",

    # ---- status and state --------------------------------------------------
    "Status": "Estado",
    "Active": "Activo",
    "Accepted": "Aceptada",
    "Declined": "Rechazada",
    "Placed": "Realizado",
    "Production": "Producción",
    "Payment": "Pago",
    "Awaiting payment": "En espera de pago",
    "Awaiting approval": "En espera de aprobación",
    "Received": "Recibido",
    "Specification in review": "Especificación en revisión",
    "Priced — awaiting release": "Con precio — en espera de publicación",
    "In progress": "En curso",
    "Yours to order": "Listos para pedir",
    "Being worked out": "En desarrollo",
    "Priced, not yet opened": "Con precio, aún sin abrir",
    "Ready to order": "Listo para pedir",
    "Not priced yet": "Aún sin precio",
    "Nothing yet.": "Nada todavía.",
    "Nothing to reorder yet.": "Aún no hay nada para volver a pedir.",
    "Nothing waiting.": "Nada en espera.",
    "Nothing booked yet.": "Nada agendado todavía.",
    "Nothing scheduled.": "Nada programado.",
    "No sample boxes yet.": "Aún no hay cajas de muestra.",
    "Nothing accepted yet.": "Aún no has aceptado nada.",
    "Nothing here yet": "Aún no hay nada aquí",
    "Not yet measured": "Aún sin medir",
    "not entered": "sin registrar",
    "always": "siempre",
    "Not established yet. We would rather say so than fill it in.":
        "Aún no está establecido. Preferimos decirlo antes que inventarlo.",
    "We will not show you a number we cannot stand behind.":
        "No te mostramos un número que no podamos sostener.",

    # ---- table headers and field labels ------------------------------------
    "Item": "Artículo",
    "Items": "Artículos",
    "Quantity": "Cantidad",
    "Category": "Categoría",
    "Materials": "Materiales",
    "Specification": "Especificación",
    "Lead time": "Plazo de entrega",
    "Minimum order": "Pedido mínimo",
    "Freight": "Flete",
    "Route": "Ruta",
    "Total": "Total",
    "Order total": "Total del pedido",
    "Landed per unit": "Costo por unidad puesto en destino",
    "per unit": "por unidad",
    "Unit": "Unitario",
    "Line total": "Total de línea",
    "Ref": "Ref",
    "Reference": "Referencia",
    "Customer": "Cliente",
    "Company name": "Nombre de la empresa",
    "Your name": "Tu nombre",
    "Email": "Correo electrónico",
    "Phone": "Teléfono",
    "Country": "País",
    "Website or store": "Sitio web o tienda",
    "From": "Desde",
    "To": "Hasta",
    "Until": "Hasta",
    "When": "Cuándo",
    "Day": "Día",
    "Time": "Hora",
    "Timezone": "Zona horaria",
    "Reason": "Motivo",
    "Notes": "Notas",
    "Notes for the floor": "Notas para la planta",
    "Ship to": "Enviar a",
    "Title": "Título",
    "Type": "Tipo",
    "Location": "Ubicación",
    "Images": "Imágenes",
    "History": "Historial",
    "Quality": "Calidad",
    "Logistics": "Logística",
    "What it is": "Qué es",
    "How it is made": "Cómo se fabrica",
    "About this product": "Sobre este producto",
    "Version": "Versión",
    "Accepted on": "Aceptado el",
    "Against": "Contra",
    "Disclaimer": "Aviso legal",
    "(optional)": "(opcional)",
    "Optional.": "Opcional.",
    "Your account": "Tu cuenta",
    "Account manager": "Ejecutivo de cuenta",
    "Orders": "Pedidos",
    "Quotes": "Cotizaciones",
    "However you prefer": "Como prefieras",
    "Talk to a person": "Habla con una persona",
    "Something else": "Otra cosa",
    "Inspection": "Inspección",
    "All": "Todos",
    "Photograph to come.": "Fotografía pendiente.",
    "Make This Box": "Haz Esta Caja",
    "Review window": "Ventana de revisión",
    "What members get": "Qué obtienen los miembros",
    "What we should know": "Lo que deberíamos saber",
    "What the member should know about it": "Lo que el miembro debe saber",
    "Your name for it": "Tu nombre para esto",
    "never changes.": "nunca cambia.",
    "their membership record": "su registro de membresía",
    "Weekly availability": "Disponibilidad semanal",
    "Blackouts": "Fechas bloqueadas",
    "Booked consultations": "Consultas agendadas",
    "Add a window": "Añadir un horario",
    "Call length": "Duración de la llamada",
    "In this timezone": "En esta zona horaria",
    "In effect": "Vigencia",
    "Slot": "Bloque",
    "Who": "Quién",
    "Their timezone": "Su zona horaria",
    "Channel": "Canal",
    "Video call": "Videollamada",
    "Phone call": "Llamada telefónica",
    "Video": "Video",
    "New event": "Evento nuevo",
    "Upcoming": "Próximos",

    # ---- the consultation picker -------------------------------------------
    "Book your consultation": "Agenda tu consulta",
    "Your timezone": "Tu zona horaria",
    "How should we call you?": "¿Cómo prefieres que te llamemos?",
    "Number to call": "Número al que llamar",
    "Include the country code": "Incluye el código de país",
    "Detected from your browser. Change it if it is wrong.":
        "Detectada desde tu navegador. Cámbiala si no es correcta.",
    "A video link comes with the confirmation.":
        "El enlace de video llega con la confirmación.",
    "Only needed because you chose a phone call.":
        "Solo hace falta porque elegiste una llamada telefónica.",
    "Anything we should know before the call?":
        "¿Algo que debamos saber antes de la llamada?",
    "No time picked yet.": "Aún no has elegido una hora.",
    "When can you take a call?": "¿Cuándo puedes atender una llamada?",
    "Or tell us when you are usually free":
        "O dinos cuándo sueles estar disponible",
    "Use this if none of the times above suit you.":
        "Úsalo si ninguno de los horarios de arriba te sirve.",
    "No call times are published right now.":
        "Ahora mismo no hay horarios de llamada publicados.",
    "Tell us below when you are usually free and we will come back with times.":
        "Dinos abajo cuándo sueles estar disponible y te propondremos horarios.",
    "Your consultation is booked": "Tu consulta está agendada",
    "Previous month": "Mes anterior",
    "Next month": "Mes siguiente",
    "Available dates": "Fechas disponibles",
    "Available times": "Horarios disponibles",

    # ---- disclaimers and acceptance ----------------------------------------
    "What we say, and stand behind": "Lo que decimos, y respaldamos",
    "Limitation of liability": "Limitación de responsabilidad",
    "What we hold, and what we never sell":
        "Qué guardamos, y qué nunca vendemos",
    "What we can and cannot make": "Qué podemos y qué no podemos fabricar",
    "This is placeholder text and is not legal advice.":
        "Este texto es provisional y no constituye asesoría legal.",
    "What you have accepted": "Lo que has aceptado",
    "Each of these is versioned. When one changes, the old wording does not disappear — "
    "anyone who accepted it keeps a record resolving to the exact text they saw.":
        "Cada uno tiene versión. Cuando uno cambia, la redacción anterior no desaparece: "
        "quien la aceptó conserva un registro que apunta al texto exacto que vio.",
    "No disclaimers published yet.": "Aún no hay avisos legales publicados.",

    # ---- headings and body copy on the public site -------------------------
    "By acceptance only": "Solo por aceptación",
    "Membership is what lets you order. It's also the part we're careful about.":
        "La membresía es lo que te permite comprar. También es la parte que cuidamos.",
    "Manufacturer · direct from the floor": "Fabricante · directo desde la planta",
    "What do you sell?": "¿Qué vendes?",
    "Why do you want to work with us?": "¿Por qué quieres trabajar con nosotros?",
    "This is the part we read closely.": "Esta es la parte que leemos con atención.",
    "Add more detail — optional, but it helps":
        "Añade más detalle: opcional, pero ayuda",
    "We read every application. You'll hear from us either way.":
        "Leemos cada solicitud. Te responderemos en cualquier caso.",
    "The fastest way for us to understand you.":
        "La forma más rápida de que te entendamos.",
    "Which best describes you?": "¿Qué te describe mejor?",
    "How long have you been trading?": "¿Cuánto tiempo llevas operando?",
    "Thank you — it's with us.": "Gracias: ya está con nosotros.",
    "We read it": "La leemos",
    "We meet you": "Nos conocemos",
    "We decide": "Decidimos",
    "You don't have to wait to get a price":
        "No tienes que esperar para tener un precio",

    # ---- portal copy --------------------------------------------------------
    "How would you like to pay?": "¿Cómo prefieres pagar?",
    "Bank transfer (ACH)": "Transferencia bancaria (ACH)",
    "Card": "Tarjeta",
    "Simulated checkout": "Pago simulado",
    "I have read and accept the": "He leído y acepto los",
    "We record which version you accepted, so this stays answerable if the wording "
    "changes later.":
        "Registramos qué versión aceptaste, para que esto siga siendo verificable si la "
        "redacción cambia más adelante.",
    "Please read and accept the disclaimers before paying.":
        "Lee y acepta los avisos legales antes de pagar.",
    "Items arrive unnamed and numbered. Name yours whenever you like — no other member "
    "can see this list.":
        "Los artículos llegan sin nombre y numerados. Ponles el tuyo cuando quieras: "
        "ningún otro miembro ve esta lista.",
    "Nothing yet. You accept the disclaimers at checkout, and the record appears in your "
    "membership record.":
        "Nada todavía. Los avisos legales se aceptan al pagar, y el registro aparece en tu "
        "registro de membresía.",
    "Some of it may already be answered.": "Puede que ya esté respondido.",
    "Questions other people asked": "Preguntas que otros han hecho",
    "First run not yet placed. This section fills in as orders complete.":
        "Aún no se ha hecho la primera producción. Esta sección se completa a medida que "
        "se cierran pedidos.",
    "Freight and duties are added by our team before payment where they aren't already "
    "priced in.":
        "El flete y los aranceles los añade nuestro equipo antes del pago cuando no están "
        "ya incluidos en el precio.",
    "If we decline it, or send it back for missing information, you are not charged.":
        "Si la rechazamos, o la devolvemos por falta de información, no se te cobra.",
    "Three ways to buy the same part. Move the quantity, change the route, and every "
    "figure below re-prices from what the desk actually entered.":
        "Tres formas de comprar la misma pieza. Mueve la cantidad, cambia la ruta, y cada "
        "cifra de abajo se recalcula con lo que la mesa realmente registró.",
    "Order quantity": "Cantidad del pedido",
    "Decision Room": "Sala de Decisión",
    "Reorder": "Volver a pedir",
    "Locked": "Bloqueado",
    "What we still need": "Lo que aún necesitamos",
    "What you sent": "Lo que enviaste",

    # ---- phrases that sit next to a figure ---------------------------------
    #
    # Every one of these carries its number through unchanged — same digits,
    # same separators, same order. `i18n._validate` refuses to load this file if
    # one does not, so "20,000" cannot quietly become "20.000" on the way into
    # Spanish even though that is what Spanish would normally do.
    "per unit at 20,000 — your price moves with quantity":
        "por unidad a 20,000 — tu precio cambia con la cantidad",
    "from 20,000 units": "desde 20,000 unidades",
    "per unit · your agreed price": "por unidad · tu precio acordado",
    "per unit · catalogue price": "por unidad · precio de catálogo",
    "Ready to order ·": "Listo para pedir ·",
    "Awaiting approval ·": "En espera de aprobación ·",
    "Reorder ·": "Volver a pedir ·",
    "We already make this for you. Reorder at your registered price without re-quoting, "
    "or price a different run below.":
        "Esto ya lo fabricamos para ti. Vuelve a pedirlo a tu precio registrado sin volver "
        "a cotizar, o calcula el precio de otra corrida abajo.",
    "This one did not come through Describe it badly — it is on your account because we "
    "already make it for you. There is no specification history to show, so this page does "
    "not pretend to have one.":
        "Este no llegó por Descríbelo mal: está en tu cuenta porque ya lo fabricamos para "
        "ti. No hay historial de especificación que mostrar, así que esta página no finge "
        "tenerlo.",
    "Not orderable from here yet.": "Aún no se puede pedir desde aquí.",
    "The routes below are priced — choose one and buy it there.":
        "Las rutas de abajo tienen precio: elige una y cómprala ahí.",
    "The version column is not decoration. If a disclaimer is rewritten, your record keeps "
    "pointing at the wording you actually read — we do not move it, and we cannot: "
    "published versions are never edited, only superseded.":
        "La columna de versión no es decoración. Si un aviso se reescribe, tu registro "
        "sigue apuntando a la redacción que realmente leíste: no la movemos, y no podemos "
        "hacerlo, porque las versiones publicadas nunca se editan, solo se reemplazan.",
    "You accept the disclaimers at checkout. The record appears here, naming the exact "
    "version you read.":
        "Los avisos legales se aceptan al pagar. El registro aparece aquí, indicando la "
        "versión exacta que leíste.",

    # ---- language switcher --------------------------------------------------
    "Language": "Idioma",
    "English": "English",
    "Español": "Español",
    "Interface only. Prices, references and anything a member wrote stay exactly as they "
    "are.":
        "Solo la interfaz. Los precios, las referencias y todo lo que un miembro escribió "
        "quedan exactamente como están.",
}
