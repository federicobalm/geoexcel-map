# GeoExcel Map — interfaz para el aula

## Dirección
Herramienta guiada para estudiantes que crean su primer mapa en notebook. Modo operativo: una decisión principal por etapa, sin portada promocional ni formularios extensos desplegados al iniciar.

## Sistema visual implementado
- Fondo de página `#f3f6f7`, superficies blancas, texto `#223439`, secundario `#586b72`.
- Acción principal verde petróleo `#126d60`; no utilizar los colores del mapa como estados de navegación.
- Tipografía de interfaz: Segoe UI / system-ui, base 15px. Títulos 24–36px, sin fuentes externas obligatorias.
- Controles de 44px como mínimo, radios de 7–10px, contenedores de 12–16px; bordes discretos, sin vidrio ni fondos decorativos.
- Foco azul visible y enlace para saltar al contenido. Estados hidden con prioridad sobre las reglas de layout.

## Estructura
- Cabecera persistente con dos destinos: Crear mapas y Análisis Rossmo.
- Mapas generales: Tus datos → Elegí un mapa → Explorá y descargá.
- Entrada: subir CSV/XLSX o cargar directamente 300 casos sintéticos de CABA.
- Selector visual nativo de siete tipos mediante radios, con ejemplos gráficos y descripciones breves.
- Coordenadas, fondo, etiquetas y tabla en desplegables. Categoría y extensión de calor aparecen solo cuando corresponden.
- La ficha cartográfica es obligatoria antes de generar: Titulo, territorio, período declarado y autor. Resultados incorporan título específico, autoría, cobertura, norte, escala y leyenda descriptiva. Datos ficticios y período deben confirmarse nuevamente al cambiar de archivo.
- Coropleta por grilla disponible para conteos; opción proporcional para frecuencia por ubicación. Densidad KDE con ancho de banda métrico y azules por defecto. Hot map independiente con colores clásicos de azul a rojo, radio y niveles editables.
- Resultados: mapa amplio, cambiar representación, descargar HTML/PDF, reencuadrar, conteos y referencias.
- Rossmo conserva sus seis pasos y parámetros; configuración avanzada agrupada en un desplegable.

## Comportamiento
- Volver conserva datos y elecciones. Cargar otro archivo invalida el resultado anterior.
- Exportar utiliza la configuración del mapa generado, no cambios aún sin aplicar.
- Operaciones en curso deshabilitan botones y anuncian estado; errores recuperables visibles.
- Fondo inicial OpenStreetMap. Otros proveedores siguen disponibles como opciones y dependen de sus servicios externos.

## Adaptación
Ancho máximo 1280px. En notebooks de poca altura se compactan espaciados. En celular, cabecera en dos líneas, selector a dos columnas, formularios a una columna.

## Verificación
`tools/verify_flows.py`: carga del ejemplo, siete tipos con 300 registros, navegación de vuelta, exportaciones HTML, PDF de Hot map/KDE/coropleta/Rossmo, seis pasos de Rossmo, recálculo, errores legibles y ausencia de excepciones JavaScript.
