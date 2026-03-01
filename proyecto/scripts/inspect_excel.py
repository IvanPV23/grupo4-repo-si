import openpyxl
from pathlib import Path
ruta=Path(r'c:\Users\Ghino\Desktop\Grupo-4-SI\proyecto\data\outputs\reporte_acumulativo.xlsx')
if ruta.exists():
    wb=openpyxl.load_workbook(ruta,data_only=True)
    ws=wb.active
    rows=list(ws.iter_rows(values_only=True))
    for row in rows[-10:]:
        print(row)
else:
    print('no existe')
