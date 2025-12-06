class MotorFinanzas:
    """
    ENCARGADO DE: Economía, Tarifas FOSE (Perú 2025) y Proyecciones.
    """

    # Base de datos completa (Recuperada de tu Código 1)
    TARIFAS_DATA = {
        "Lima y Callao": (0.67, 0.69), "Arequipa": (0.75, 0.77), "Cusco": (0.81, 0.88),
        "Trujillo (La Libertad)": (0.78, 0.80), "Chiclayo (Lambayeque)": (0.74, 0.76),
        "Piura": (0.80, 0.83), "Iquitos (Loreto)": (0.76, 0.86), "Huancayo (Junín)": (0.81, 0.98),
        "Ica": (0.74, 0.76), "Cajamarca": (0.78, 0.80), "Puno": (0.81, 0.93),
        "Tacna": (0.76, 0.78), "Ayacucho": (0.81, 0.98), "Huánuco": (0.81, 0.98),
        "Chachapoyas": (0.81, 0.98), "Moyobamba": (0.81, 0.99), "Pucallpa": (0.81, 0.90),
        "Moquegua": (0.74, 0.76), "Tumbes": (0.80, 0.83), "Huaraz (Ancash)": (0.78, 0.80),
        "Puerto Maldonado": (0.81, 0.89), "Cerro de Pasco": (0.81, 0.98),
        "Abancay": (0.81, 0.88), "Huancavelica": (0.81, 0.98), "Personalizado": (0.85, 0.90)
    }

    @staticmethod
    def obtener_lista_regiones():
        return list(MotorFinanzas.TARIFAS_DATA.keys())

    @staticmethod
    def get_tarifas_region(region):
        return MotorFinanzas.TARIFAS_DATA.get(region, (0.85, 0.90))

    @staticmethod
    def calcular_tarifa_dinamica(kwh_total, tarifas_tupla):
        """
        Retorna: (Precio_Aplicado, Bool_Tiene_Subsidio)
        """
        LIMITE_FOSE = 140  # kWh

        if kwh_total <= LIMITE_FOSE:
            return tarifas_tupla[0], True  # Tarifa con Subsidio (Index 0)
        else:
            return tarifas_tupla[1], False  # Tarifa Full (Index 1)

    @staticmethod
    def obtener_ranking(kwh_total):
        # Gamificación del consumo
        if kwh_total < 100:
            return "🏆 Rango: ECO-MASTER (Top 10%)"
        elif kwh_total < 200:
            return "🥈 Rango: EFICIENTE (Promedio)"
        elif kwh_total < 350:
            return "⚠️ Rango: CONSUMO ALTO"
        else:
            return "🚨 Rango: CRÍTICO (Derrochador)"