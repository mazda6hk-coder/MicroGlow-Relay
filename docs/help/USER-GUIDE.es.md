# Guía de uso de MicroGlow Relay

## Conexión

1. En la página Modelos, introduzca la dirección del proveedor y la clave API, y añada los modelos.
2. Cierre normalmente la aplicación de escritorio y la línea de comandos de Codex. Active Relay, espere a que el servicio esté listo y siga las indicaciones para habilitar la conexión de Codex.
3. Vuelva a iniciar Codex. Para Claude Code, utilice su interruptor de conexión y siga las indicaciones.

Desactivar Relay o salir normalmente restaura el acceso nativo de Codex. Minimizar a la bandeja no cierra la aplicación; utilice la opción de salida del menú de la bandeja.

Salga primero de Codex / Claude Code y después de Relay. Relay restaura la configuración de conexión antes de salir. Si falla, permanece abierto y muestra el motivo. Resuelva el problema e intente salir de nuevo.

## Modelos y sesiones

- Elija el modelo dentro de su sesión de Codex. Configure el modelo predeterminado en la página Modelos. Allí puede añadir, editar, buscar y eliminar configuraciones, y añadir varios canales para el mismo modelo.
- Si el nombre de un modelo guardado coincide exactamente con un modelo nativo de Codex, su entrada aparece en el selector de Codex. Por ejemplo, guardar una configuración llamada `gpt-6-astra` hace que aparezca esa entrada. Al eliminar la última configuración que la proporciona, desaparece. No se muestran nombres sin una configuración correspondiente.
- Una entrada nativa enviada por Relay a un proveedor externo permite continuar la conversación, pero se elimina el razonamiento cifrado. El proveedor recibe resúmenes del razonamiento y texto. Solo OpenAI puede leer el contenido cifrado por OpenAI. Para conservar la cadena de razonamiento cifrada, use un canal con la dirección `api.openai.com` y su propia clave de OpenAI.
- La continuidad de sesiones solo modifica la configuración de acceso de la sesión seleccionada; no reescribe el historial. Salga normalmente de Codex antes de continuar, según las indicaciones.
- La conversión funciona igual en ambas direcciones: cierre Codex de escritorio y de línea de comandos, seleccione la sesión y el destino, y aplique el cambio. Codex no necesita estar ejecutándose ni tener una sesión iniciada, y Relay no necesita estar activado. Guarde una configuración de modelo antes de cambiar al acceso por Relay.
- Para volver al acceso oficial, se usa primero el modelo de la sesión oficial más reciente que sea válido. Si no existe, se usa la copia de seguridad de los metadatos oficiales originales de esa sesión. La conversión se detiene si ninguna fuente es fiable.
- Tras la conversión, active Relay antes de iniciar Codex para usar Relay; desactive Relay antes de iniciar Codex para usar el acceso oficial. Codex puede seguir solicitando que inicie sesión en los servicios oficiales.

## Preguntas frecuentes

### ¿No aparecen modelos?

Una instalación nueva no incluye modelos preconfigurados. Añada su proveedor y sus modelos. Al obtener los modelos disponibles puede seleccionar varios; cada uno se guarda como una configuración independiente.

### ¿Fallan las solicitudes?

Compruebe la dirección, la clave API, el saldo y el nombre del modelo. No incluya claves ni contenido de conversaciones al informar de un problema.

### ¿De dónde salen las estadísticas de Token?

Proceden de los datos de uso de la respuesta original del proveedor. Relay no envía solicitudes adicionales para cada lugar donde muestra las estadísticas.

### ¿Cómo se usa Trip Token A/B?

A y B son subtotales independientes. Cada uno cuenta su ámbito seleccionado desde su propio reinicio. Continúan al cambiar de día y al reiniciar la aplicación; solo el botón de reinicio de cada columna los pone a cero. El reinicio conserva los totales del día y los registros de solicitudes, y archiva el intervalo anterior en el historial de trayectos. Úselos para tareas diferentes y asígneles nombres. Las solicitudes fallidas siguen contando como solicitudes; los Token se contabilizan según el uso comunicado por el proveedor.

### ¿Cómo funcionan los filtros de fecha?

Seleccione una fecha y un período de día, semana, mes, trimestre o año para ver el intervalo correspondiente. El denominador de la proporción de errores es el total de solicitudes de ese intervalo.

### ¿Cómo funciona el consentimiento para estadísticas anónimas?

Ninguna opción de consentimiento está preseleccionada durante la instalación. Elija una vez si desea participar o rechazarlo para continuar. La elección controla las estadísticas anónimas locales y el permiso de envío, sin una segunda confirmación. Rechazarlo no afecta a la instalación ni al uso; puede cambiarlo en Configuración. Las instalaciones silenciosas nuevas lo desactivan por defecto; las actualizaciones silenciosas conservan el consentimiento existente. Solo se intenta enviar al salir normalmente. Si falla, se reintenta en la siguiente salida. Consulte los campos completos y el comportamiento de almacenamiento en la política de privacidad.

### ¿Cómo se actualiza?

Con la comprobación automática activada, Relay busca actualizaciones en segundo plano después de iniciarse y cada 24 horas. GitHub es la fuente principal y la web oficial es la alternativa. Los instaladores nuevos se descargan automáticamente y se comprueban su tamaño y SHA256. Pulse Instalar actualización en Configuración para abrir el instalador y cierre Relay normalmente antes de instalar. El instalador nunca se ejecuta automáticamente. También puede usar Comprobar ahora para buscar manualmente.

### Datos y desinstalación

Configuración muestra el directorio de datos. La desinstalación conserva los datos del usuario. Para eliminarlos, salga normalmente de Relay, haga una copia de lo que necesite y elimine únicamente ese directorio de datos. No borre el directorio de Codex.

## Contacto

- Web oficial: https://www.microglow.com.cn
- Soporte del producto: support@microglow.com.cn
- Privacidad: privacy@microglow.com.cn
- Avisos de seguridad: security@microglow.com.cn
