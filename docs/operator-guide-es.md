# Guia Operativa - Oracle Opportunity Pulse

Esta guia operativa describe como ejecutar Oracle Opportunity Pulse en Codex para centralizar informacion de oportunidades Oracle en SharePoint. El README raiz queda en ingles para publicacion en GitHub; este documento queda en espanol para ejecucion, validacion y capturas reales.

## Objetivo

Construir una wiki Markdown gobernada por SharePoint para dar trazabilidad a oportunidades Oracle desde discovery hasta oportunidad formal. El plugin usa:

- `Opportunities`: lista maestra con cliente, pais, oportunidad, SR, workload, delivery, lideres CE y contexto.
- `Knowledge Items`: lista normalizada de evidencias con `SourceType = Zoom | Outlook | Slack | Notes`.
- `Automation Runs`: auditoria por usuario/fuente/direccion y watermark `NextScanFrom` para sincronizacion incremental.
- `OracleOpportunityPulseWiki/`: estructura Markdown en SharePoint para archivos `.md`, templates, pendientes e indices.
- `_config/pulse-profile.json`: perfil compartido no secreto para que otros usuarios se conecten al mismo Pulse.
- `_index/*.jsonl`: indice reconstruible para busqueda, tags, backlinks, timelines y frescura.

## Mapa Rapido De Skills

- `pulse-00-orchestrator`: entrada principal para registrar oportunidades y coordinar evidencias.
- `pulse-01-setup`: instalacion nueva o conexion a un Pulse existente.
- `pulse-02-automation`: validacion y preparacion de automatizacion personal diaria.
- `pulse-03-outlook`: captura de correos recibidos/enviados con `@agent_data`.
- `pulse-04-zoom`: captura de transcripciones desde `[0] Zoom AI companion`.
- `pulse-05-slack`: registro de links/canales Slack.
- `pulse-06-notes`: notas Markdown manuales.
- `pulse-07-wiki`: refresh, busqueda, timeline, backlinks y sugerencias de links.
- `pulse-99-test`: pruebas de readiness y smoke test end-to-end.

## Prerequisitos

- Codex con el plugin Oracle Opportunity Pulse instalado.
- Conector SharePoint habilitado.
- Conector Outlook Email habilitado.
- Conector Slack habilitado para registrar links y preparar futuras lecturas.
- Sitio SharePoint y document library destino.
- Permisos para crear o actualizar carpetas y archivos en SharePoint.
- Para listas SharePoint, un flujo autorizado de Microsoft Graph cuando se pase de dry-run a escritura real.
- Carpeta exacta de Outlook: `[0] Zoom AI companion`.
- Convencion Outlook: el cuerpo del correo recibido/enviado debe incluir `@agent_data`.
- Convencion Zoom: las transcripciones se capturan desde la carpeta exacta `[0] Zoom AI companion`; no requieren `@agent_data`.

## Flujo Entre Skills

`pulse-01-setup` guia la instalacion o conexion:

- Modo `install_new`: crea o valida un Pulse nuevo.
- Modo `connect_existing`: conecta al usuario a un Pulse ya instalado.
- Listas `Opportunities`, `Knowledge Items` y `Automation Runs`.
- Carpeta raiz `OracleOpportunityPulseWiki`.
- Carpetas `_config`, `_index`, `_templates`, `_pending`.
- Perfil compartido `_config/pulse-profile.json`.
- Templates Markdown.
- Carpetas por oportunidad.

`pulse-02-automation` prepara la automatizacion personal:

- Valida SharePoint, Outlook, Zoom, Slack, listas, wiki folder y timezone.
- Usa 18:00 en la zona horaria IANA de cada usuario.
- Cada usuario escanea su propio Outlook/Zoom contra el Pulse compartido.
- Calcula ventanas incrementales desde la ultima ejecucion exitosa por usuario/fuente/direccion.
- Si la PC estuvo apagada o una ejecucion fallo, retoma desde el ultimo `NextScanFrom` exitoso.
- Usa overlap de 10 minutos y deduplicacion por `internet_message_id` o id de la fuente.
- Nunca autoaprueba; solo propone candidatos.

`pulse-07-wiki` usa esa base:

- Configura host, site path, library y root folder.
- Refresca `_index/*.jsonl`.
- Consulta evidencias aprobadas.
- Genera timelines, backlinks y sugerencias de links Markdown.

Las skills de fuente solo capturan o registran:

- `pulse-03-outlook`: correos Outlook dentro de la ventana incremental con `@agent_data`.
- `pulse-04-zoom`: transcripciones dentro de la ventana incremental desde `[0] Zoom AI companion`, sin requerir `@agent_data`.
- `pulse-05-slack`: links/canales Slack.
- `pulse-06-notes`: notas Markdown manuales.

Regla de handoff: despues de aprobar y guardar evidencia en SharePoint, refresca el indice de la Knowledge Wiki antes de confiar en la busqueda.

## Diagramas Del Flujo

El primer diagrama muestra la arquitectura general: las fuentes entran al plugin Codex, pasan por una compuerta de aprobacion humana y terminan en listas SharePoint normalizadas junto con una wiki Markdown consultable.

![Arquitectura Oracle Opportunity Pulse](images/pulse-1.png)

El segundo diagrama muestra la sincronizacion incremental personal a las 18:00: cada usuario retoma desde el ultimo `NextScanFrom`, escanea fuentes, deduplica eventos, propone clasificacion, registra `Automation Runs` y refresca el indice de la wiki despues de guardar evidencias aprobadas.

![Flujo incremental Oracle Opportunity Pulse](images/pulse-2.png)

## Primer Uso

### 1. Habilitar conectores

Verifica que esten habilitados:

- SharePoint
- Outlook Email
- Slack
- Oracle Opportunity Pulse

Prompt sugerido:

```text
Use $pulse-99-test to check required connectors and run the smoke test plan.
```

### 2. Elegir modo de setup guiado

Prompt sugerido:

```text
Use $pulse-01-setup to guide me through installing a new Oracle Opportunity Pulse or connecting to an existing one.
```

Codex debe preguntar:

- Si deseas `install_new` o `connect_existing`.
- Hostname de SharePoint.
- Site path.
- Library path.
- Root folder de la wiki.
- Nombre de listas: `Opportunities`, `Knowledge Items` y `Automation Runs`.
- Timezone IANA del usuario, por ejemplo `America/Lima`.
- Carpeta Zoom, por defecto `[0] Zoom AI companion`.

### 3. Instalar un Pulse nuevo

Usa este modo si el SharePoint aun no tiene las listas ni la estructura base.

Prompt sugerido:

```text
Use $pulse-01-setup to configure_pulse_connection in install_new mode for hostname <tenant>.sharepoint.com, site path /sites/<site>, library path Shared Documents, root folder OracleOpportunityPulseWiki, timezone <timezone>, and Zoom folder [0] Zoom AI companion.
```

Despues ejecuta:

```text
Use $pulse-01-setup to create or validate the Opportunities, Knowledge Items, and Automation Runs lists in dry-run mode, then prepare the base wiki folders including _config, _index, _templates, and _pending.
```

No se debe afirmar que SharePoint cambio hasta que un flujo Graph o herramienta SharePoint confirme la escritura.

Estructura esperada:

```text
OracleOpportunityPulseWiki/
  _config/
    pulse-profile.json
  _index/
  _templates/
  _pending/
```

### 4. Conectarse a un Pulse existente

Usa este modo si otra persona ya creo las listas y la wiki.

Prompt sugerido:

```text
Use $pulse-01-setup to configure_pulse_connection in connect_existing mode using this shared profile or these SharePoint locations: hostname <tenant>.sharepoint.com, site path /sites/<site>, library path Shared Documents, root folder OracleOpportunityPulseWiki, lists Opportunities, Knowledge Items, and Automation Runs, timezone <timezone>.
```

Si existe el archivo `_config/pulse-profile.json`, Codex puede usarlo como `shared_profile`. Este archivo no debe contener secretos, tokens ni datos privados de Outlook/Slack.

### 5. Validar conexion Pulse

- Hostname de SharePoint.
- Site path.
- Library path.
- Root folder.
- Nombre de listas: `Opportunities`, `Knowledge Items` y `Automation Runs`.
- Timezone.
- Carpeta Zoom.
- Conectores SharePoint, Outlook Email y Slack.

Prompt sugerido:

```text
Use $pulse-01-setup to validate my Pulse connection before ingestion or automation.
```

Si hay errores, primero corrige conectores, rutas o timezone.

### 6. Crear automatizacion personal a las 18:00

Cada usuario debe crear su propia automatizacion. Esto permite que usuarios en Peru, Colombia, Mexico u otros paises sincronicen a las 18:00 de su zona horaria local.

Prompt sugerido:

```text
Use $pulse-02-automation to validate my sources and prepare my personal daily sync automation at 18:00 for timezone <timezone>.
```

Codex debe:

- Ejecutar `validate_pulse_connection`.
- Ejecutar `prepare_daily_sync_automation`.
- Mostrar bloqueos o advertencias.
- Pedir confirmacion antes de llamar `automation_update`.
- Crear una automation personal, no una central compartida.

La automation escanea usando ventana incremental:

- Correos recibidos desde la ultima ejecucion exitosa, solo si contienen `@agent_data`.
- Correos enviados desde la ultima ejecucion exitosa, solo si contienen `@agent_data`.
- Carpeta Zoom configurada desde la ultima ejecucion exitosa, sin requerir `@agent_data`.
- Slack solo como validacion/link registration V1 si se habilita.

Cada fuente/direccion debe registrar una fila en `Automation Runs` con `RunId`, usuario, fuente, direccion, `ScanFrom`, `ScanTo`, estado, conteos y `NextScanFrom`.

### 7. Registrar oportunidad Discovery

Si aun no hay codigo de oportunidad ni SR, registra una oportunidad Discovery.

Prompt sugerido:

```text
Use $pulse-00-orchestrator to register a Discovery opportunity for client <cliente>, country <pais>, workload <descripcion>, delivery model <modelo>, and CE leaders <correos>.
```

Codex debe usar:

- `LifecycleStage = Discovery`
- `DiscoveryId`
- `OpportunityKey`
- `NeedsOpportunityCode = true`
- `NeedsSR = true`

### 8. Registrar Slack

Prompt sugerido:

```text
Use $pulse-05-slack to register this Slack channel URL for client <cliente> and opportunity key <OpportunityKey>.
```

Slack V1 solo registra el link/canal. No se debe afirmar que se leyeron mensajes.

### 9. Escanear Outlook

Prompt sugerido:

```text
Use $pulse-03-outlook to scan received and sent messages since the last successful run whose body contains @agent_data.
```

Reglas:

- Usar `prepare_incremental_sync_window` para calcular `scan_from` y `scan_to`.
- Debe existir `@agent_data` en el cuerpo.
- Registrar la ejecucion con `record_automation_run`.
- Siempre proponer, nunca autoaprobar.

### 10. Escanear Zoom

Prompt sugerido:

```text
Use $pulse-04-zoom to scan messages since the last successful run in [0] Zoom AI companion.
```

Reglas:

- `SourceType = Zoom`.
- `Direction = MeetingTranscript`.
- La carpeta exacta `[0] Zoom AI companion` es la senal de captura.
- No requiere `@agent_data`.
- Registrar la ejecucion con `record_automation_run`.
- Preservar la transcripcion original.
- No resumir ni reescribir antes de almacenar.

### 11. Aprobar o rechazar candidatos

Codex debe mostrar:

- Candidate id.
- Cliente propuesto.
- OpportunityKey, DiscoveryId, codigo de oportunidad o SR si aplica.
- Source type.
- Direction.
- Evidencia de clasificacion.
- Confianza.
- Link fuente, si existe.

Tu respuesta debe confirmar una de estas acciones:

- Aprobar como esta.
- Aprobar con correcciones.
- Rechazar con razon.

### 12. Refrescar indice

Prompt sugerido:

```text
Use $pulse-07-wiki to refresh the Knowledge Wiki index from the approved Opportunities, Knowledge Items, and Markdown files.
```

El refresh genera:

- `opportunities.jsonl`
- `knowledge-items.jsonl`
- `documents.jsonl`
- `backlinks.jsonl`
- `tags.jsonl`
- `last-refresh.json`

### 13. Consultar la wiki

Prompt sugerido:

```text
Use $pulse-07-wiki to query what we know about client <cliente>, include evidence links and warn if the index is stale or documents were not fetched.
```

La respuesta debe incluir:

- Resumen corto.
- Evidencias con links a `.md`.
- Oportunidad relacionada.
- Source type.
- Fecha.
- Advertencia si el indice esta stale o el resultado es metadata-only.

## Preguntas Que Codex Debe Hacer

Antes de registrar o aprobar evidencia, Codex debe confirmar o proponer:

- Cliente.
- Pais.
- Descripcion de workload.
- Modelo de delivery: `Oracle Services`, `P2P`, `Partner`, `Customer`.
- CE lideres.
- Modo de setup: `install_new` o `connect_existing`.
- Ubicacion de listas y folder wiki cuando se conecta a un Pulse existente.
- Timezone IANA del usuario para automatizacion.
- Confirmacion antes de crear una automation personal con `automation_update`.
- Usuario que ejecuta la automatizacion para poder registrar auditoria en `Automation Runs`.
- Codigo de oportunidad, si existe.
- SR, si existe.
- `OpportunityKey` o `DiscoveryId` cuando aun no hay codigo/SR.
- Source type: `Zoom`, `Outlook`, `Slack`, `Notes`.
- Direccion: `Received`, `Sent`, `MeetingTranscript`, `Manual`.
- Evidencia usada para clasificar.
- Confirmacion explicita para aprobar, corregir o rechazar.

## Ejemplos De Consulta

Por cliente:

```text
Use $pulse-07-wiki to query all approved evidence for client ACME Bank.
```

Por DiscoveryId:

```text
Use $pulse-07-wiki to query DiscoveryId DISC-20260611-acme-123456.
```

Por codigo de oportunidad:

```text
Use $pulse-07-wiki to query opportunity code OPP-12345 and include source links.
```

Por SR:

```text
Use $pulse-07-wiki to query SR 3-12345678901 and show related evidence.
```

Por source type:

```text
Use $pulse-07-wiki to show only Zoom evidence for ACME Bank.
```

Timeline:

```text
Use $pulse-07-wiki to get the opportunity timeline for OpportunityKey DISC-20260611-acme-123456.
```

Backlinks:

```text
Use $pulse-07-wiki to get backlinks for OracleOpportunityPulseWiki/acme-bank/DISC-20260611-acme-123456/context.md.
```

Pendientes:

```text
Use $pulse-07-wiki to inspect pending candidates and pending wiki files for today.
```

## Capturas Pendientes

Reemplaza estos placeholders con capturas reales despues de ejecutar el flujo:

![Plugin installed](images/01-plugin-installed.png)
![Readiness check](images/02-readiness-check.png)
![SharePoint folders](images/03-sharepoint-folders.png)
![Candidate proposal](images/04-candidate-proposal.png)
![Wiki query](images/05-wiki-query.png)

## Troubleshooting

- Plugin no visible: refresca Codex y abre un thread nuevo.
- Thread actual sin herramientas nuevas: los threads activos pueden no cargar skills instaladas despues de iniciarse.
- Conector faltante: ejecuta `check_required_connectors`.
- Indice stale: ejecuta `refresh_knowledge_index` antes de confiar en la respuesta.
- Resultado metadata-only: falta fetch de los `.md`; usa SharePoint para recuperar documentos antes de responder por contenido.
- SharePoint write no confirmado: no reportes exito hasta que una herramienta SharePoint o flujo Graph confirme la escritura.
- Outlook no detecta candidatos: verifica que `@agent_data` este en el cuerpo del correo y que `scan_from` / `scan_to` cubran el mensaje.
- Zoom no detecta candidatos: verifica que el correo este en la carpeta exacta `[0] Zoom AI companion` y dentro de la ventana incremental; no agregues `@agent_data` solo para Zoom.
- PC apagada o ejecucion perdida: revisa `Automation Runs`; la siguiente ejecucion debe partir del ultimo `NextScanFrom` exitoso.

## Proxima Iteracion Con Capturas

Cuando tengas capturas reales:

1. Guarda cada imagen en `docs/images/` con el nombre del placeholder.
2. Comparte las capturas en el thread.
3. Actualizare esta guia con observaciones reales del flujo, pasos visuales y ajustes de troubleshooting.
