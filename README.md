# Molinaro

`Molinaro`, visible para el usuario como `HojaSQL Studio`, es una app de escritorio para abrir archivos Excel, consultarlos con SQL y exportar resultados.

## Qué hace

- Abre `.xlsx`, `.xls` y `.xlsm`.
- Permite consultar hojas con SQL usando DuckDB.
- Incluye autocompletado, comandos rápidos y exportación a `.csv` o `.xlsx`.

## Instalación

La forma recomendada es descargar un paquete desde `Releases` y no clonar el repositorio para usar la app.

### Debian y Ubuntu

Descarga el paquete `.deb` y luego instala:

```bash
sudo apt install ./hojasql-studio_<version>_amd64.deb
```

Después podrás abrir `HojaSQL Studio` desde el menú de aplicaciones.

### Arch, Omarchy y otras distros

Descarga el portable Linux en formato `.tar.gz`, extráelo y entra a la carpeta:

```bash
tar -xzf HojaSQLStudio-linux-portable.tar.gz
cd portable-linux
```

Tienes dos formas de usarlo.

Sin instalar nada en el sistema:

```bash
./abrir_consola_excel_portable.sh
```

Instalándolo en tu sesión de usuario para que aparezca en el launcher:

```bash
./install_local.sh
```

Eso instala:

- el ejecutable en `~/.local/opt/hojasql-studio`
- el comando `hojasql-studio` en `~/.local/bin`
- el launcher en `~/.local/share/applications/hojasql-studio.desktop`
- el icono en `~/.local/share/icons/hicolor/256x256/apps`

Para desinstalar:

```bash
./uninstall_local.sh
```

### Windows

El instalador de Windows se publicará en `Releases`.

Cuando esté disponible, bastará con descargar `HojaSQLStudio-setup.exe` y ejecutarlo.

## Uso básico

1. Abre un archivo Excel.
2. Escribe una consulta SQL.
3. Ejecuta con `Enter`.
4. Exporta el resultado si lo necesitas.

Ejemplo:

```sql
SELECT COMUNA, COUNT(*) AS total
FROM panel_data
WHERE TIMELINE = '2011-2012'
GROUP BY COMUNA
ORDER BY total DESC
LIMIT 10;
```

## Actualizaciones

La aplicación puede detectar nuevas versiones publicadas en `GitHub Releases` y abrir la descarga correspondiente a tu sistema.
