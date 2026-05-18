# HojaSQL Studio

Interfaz para abrir cualquier Excel del computador, escribir consultas SQL en una consola estilo ciberpunk y ver los resultados en una tabla dentro de la misma ventana.

## Mejoras principales

- Selector grafico de archivo Excel.
- Consola visual estilo terminal con soporte para SQL y comandos tipo `.help`.
- `Enter` ejecuta y `Shift+Enter` agrega una nueva linea.
- Autocompletado con `TAB` para comandos, tablas, columnas y keywords SQL.
- Tabla de resultados persistente en la parte inferior.
- Exportacion directa a `.xlsx` o `.csv`.

## Ejecutar en desarrollo

### Linux

```bash
./abrir_consola_excel.sh
```

O abriendo un archivo especifico:

```bash
./abrir_consola_excel.sh ruta/al/archivo.xlsx
```

### Windows

Doble click en `abrir_consola_excel.bat` o desde PowerShell/CMD:

```bat
abrir_consola_excel.bat ruta\al\archivo.xlsx
```

## Uso

1. Abre un archivo Excel.
2. Escribe SQL o un comando en la consola.
3. Ejecuta con `Enter`.
4. Usa `Shift+Enter` para ordenar la consulta en varias lineas.
5. Usa `TAB` para autocompletar.
6. Revisa el resultado abajo y exporta si lo necesitas.

Comandos utiles:

```text
.help
.tables
.cols panel_data COMUNA
.find TIMELINE
.preview panel_data 20
.count panel_data
.open
.export resultado.xlsx
.status
.quit
```

Ejemplo:

```sql
SELECT COMUNA, COUNT(*) AS total
FROM panel_data
WHERE TIMELINE = '2011-2012'
GROUP BY COMUNA
ORDER BY total DESC
LIMIT 10;
```

## Dependencias

Runtime:

```text
pandas
openpyxl
duckdb
```

Build:

```text
pip install -r requirements-build.txt
```

## Builds portables

### Linux

```bash
./build_linux.sh
```

Genera una app grafica en:

```text
dist/HojaSQLStudio/
```

### Windows

```bat
build_windows.bat
```

Genera:

```text
portable-windows\HojaSQLStudio.exe
HojaSQLStudio-windows-portable.zip
```
