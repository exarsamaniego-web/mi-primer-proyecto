from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os
import datetime


class MotorReportes:
    """
    ENCARGADO DE: Generación de Documentos Técnicos PDF.
    """

    @staticmethod
    def generar_pdf(items, totales, region, tarifa_actual, filename="Reporte_LuzSmart_Pro.pdf"):
        try:
            c = canvas.Canvas(filename, pagesize=letter)
            w, h = letter

            # 1. Encabezado
            c.setFillColorRGB(0.1, 0.2, 0.1)  # Verde oscuro
            c.rect(0, h - 100, w, 100, fill=True, stroke=False)

            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 24)
            c.drawString(30, h - 60, "LUZ SMART PRO - REPORTE DETALLADO")
            c.setFont("Helvetica", 10)
            c.drawString(30, h - 85, f"Fecha: {datetime.date.today()} | Región: {region}")

            # 2. Resumen Ejecutivo
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(30, h - 140, "RESUMEN DE FACTURACIÓN")

            c.setFont("Helvetica", 11)
            # Calculamos el cargo fijo restando el total - consumo variable
            cargo_fijo_aprox = 4.50
            costo_variable = totales['dinero'] - cargo_fijo_aprox

            c.drawString(40, h - 165, f"• Consumo Energía (Variable): S/ {costo_variable:.2f}")
            c.drawString(40, h - 185, f"• Cargo Fijo (Mantenimiento): S/ {cargo_fijo_aprox:.2f}")
            c.drawString(40, h - 205, f"• TOTAL A PAGAR: S/ {totales['dinero']:.2f}")

            c.drawString(300, h - 165, f"• Energía Consumida: {totales['kwh']:.2f} kWh")
            c.drawString(300, h - 185, f"• Tarifa Base: S/ {tarifa_actual:.4f} / kWh")
            c.drawString(300, h - 205, f"• Estado: {totales['tarifa_nombre']}")

            # 3. Tabla Tipo Excel
            y_inicio = h - 260
            c.setFont("Helvetica-Bold", 12)
            c.drawString(30, y_inicio + 25, "DESGLOSE DE CONSUMO")

            # Definimos posiciones X de las columnas
            # X0(Inicio) | X1(Aparato) | X2(Uso) | X3($/h) | X4(Amper) | X5(Resist) | X6(Campo) | X7(Total)
            cols = [20, 150, 260, 320, 380, 440, 510, 580]

            # --- DIBUJAR ENCABEZADO (FONDO) ---
            c.setFillColor(colors.lightgrey)
            c.rect(cols[0], y_inicio, cols[-1] - cols[0], 20, fill=True, stroke=True)

            # Texto Encabezado
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(cols[0] + 5, y_inicio + 6, "APARATO")
            c.drawString(cols[1] + 5, y_inicio + 6, "DÍAS x MES | HRS x DÍA")
            c.drawString(cols[2] + 5, y_inicio + 6, "COSTO/HORA")
            c.drawString(cols[3] + 5, y_inicio + 6, "AMPERIOS")
            c.drawString(cols[4] + 5, y_inicio + 6, "RESIST.")
            c.drawString(cols[5] + 5, y_inicio + 6, "CAMPO(µT)")
            c.drawString(cols[6] + 5, y_inicio + 6, "TOTAL MES")

            y = y_inicio

            c.setFont("Courier", 8)
            for item in items:
                y -= 20  # Bajamos 20 puntos por fila

                # Texto de la fila
                nombre = item['nombre'][:22]
                uso = f"{item['dias']} días | {item['horas']}h/día"
                costo_hora = (item['watts'] / 1000) * tarifa_actual
                fisica = item['fisica']

                c.drawString(cols[0] + 5, y + 6, nombre)
                c.drawString(cols[1] + 5, y + 6, uso)
                c.drawString(cols[2] + 5, y + 6, f"S/ {costo_hora:.4f}")
                c.drawString(cols[3] + 5, y + 6, str(fisica['I']))
                c.drawString(cols[4] + 5, y + 6, str(fisica['R']))
                c.drawString(cols[5] + 5, y + 6, str(fisica['B']))
                c.drawString(cols[6] + 5, y + 6, f"S/ {item['costo']:.2f}")

                # Líneas de la cuadrícula
                c.setStrokeColor(colors.black)
                c.line(cols[0], y, cols[-1], y)
                for x in cols:
                    c.line(x, y, x, y + 20)

                # Nueva página si se acaba el espacio
                if y < 50:
                    c.showPage()
                    y = h - 50

            # === SECCIÓN DE FUNDAMENTOS TEÓRICOS (NUEVO) ===

            # Verificamos si queda espacio. Si queda menos de 200px, nueva página.
            if y < 200:
                c.showPage()
                y = h - 50

            y -= 40
            c.setFillColor(colors.black)  # Asegurar color negro
            c.setFont("Helvetica-Bold", 14)
            c.drawString(30, y, "FUNDAMENTOS DE ELECTROMAGNETISMO APLICADOS")

            y -= 25
            c.setFont("Helvetica", 10)
            ecuaciones = [
                "• LEY DE OHM: I = P/V → Corriente eléctrica en amperios",
                "• LEY DE JOULE: E = P·t → Energía disipada en joules",
                "• LEY DE AMPÈRE: B = (μ₀·I)/(2πr) → Campo magnético en teslas",
                "• CARGA ELÉCTRICA: Q = I·t → Coulombs transportados",
                "• RESISTENCIA: R = V²/P → Ohmios de resistencia equivalente",
                "• PÉRDIDAS: P_pérdida = I²R_cable → Pérdidas por efecto Joule"
            ]

            for ec in ecuaciones:
                c.drawString(40, y, ec)
                y -= 20

            c.save()
            os.startfile(filename)
        except Exception as e:
            print(f"Error PDF: {e}")