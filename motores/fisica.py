# motores/fisica.py (VERSIÓN MEJORADA)

import math


class MotorFisica:
    """
    MÓDULO DE INGENIERÍA ELECTROMAGNÉTICA
    Aplica principios del curso: Ohm, Kirchhoff, Ampère, Faraday, Joule
    """

    # === CONSTANTES FÍSICAS (Unidades SI) ===
    VOLTAJE = 220.0  # V (Voltios - Perú)
    MU_0 = 4 * math.pi * 1e-7  # H/m (Permeabilidad magnética del vacío)
    EPSILON_0 = 8.854e-12  # F/m (Permitividad eléctrica del vacío)
    RHO_COBRE = 1.68e-8  # Ω·m (Resistividad del cobre a 20°C)
    FACTOR_CO2 = 0.203  # kg CO2/kWh (Factor de emisión red peruana)
    AREA_CABLE_STD = 2.5e-6  # m² (Cable doméstico típico 2.5mm²)

    @staticmethod
    def analizar_componente(watts, horas, dias):
        """
        ANÁLISIS ELECTROMAGNÉTICO COMPLETO de un aparato eléctrico

        Parámetros:
            watts (float): Potencia nominal del aparato (W)
            horas (float): Horas de uso diario
            dias (int): Días de uso al mes

        Retorna:
            dict: Diccionario con TODOS los parámetros electromagnéticos
        """

        # ========================================
        # 1️⃣ LEY DE OHM APLICADA (I = P/V)
        # ========================================
        corriente = watts / MotorFisica.VOLTAJE  # Amperios

        # ========================================
        # 2️⃣ RESISTENCIA EQUIVALENTE (R = V²/P)
        # ========================================
        # Forma alternativa: R = V/I (mismo resultado)
        resistencia = (MotorFisica.VOLTAJE ** 2) / watts if watts > 0 else float('inf')

        # ========================================
        # 3️⃣ LEY DE JOULE - ENERGÍA DISIPADA
        # ========================================
        segundos_totales = horas * dias * 3600  # Convertir a segundos
        energia_joules = watts * segundos_totales  # E = P·t (Joules)
        kwh = (watts * horas * dias) / 1000  # kWh (unidad comercial)

        # ========================================
        # 4️⃣ CARGA ELÉCTRICA TRANSPORTADA (Q = I·t)
        # ========================================
        carga_coulombs = corriente * segundos_totales  # Coulombs

        # ========================================
        # 5️⃣ LEY DE AMPÈRE - CAMPO MAGNÉTICO
        # ========================================
        # Para conductor recto infinito: B = (μ₀·I)/(2πr)
        distancia = 0.3  # 30 cm (distancia típica de exposición)
        campo_tesla = (MotorFisica.MU_0 * corriente) / (2 * math.pi * distancia)
        campo_microtesla = campo_tesla * 1e6  # Convertir a µT

        # ========================================
        # 6️⃣ DENSIDAD DE CORRIENTE (J = I/A)
        # ========================================
        # Importante para seguridad del cableado
        densidad_corriente = corriente / MotorFisica.AREA_CABLE_STD  # A/m²

        # ========================================
        # 7️⃣ POTENCIA DISIPADA EN CABLE (Pérdidas)
        # ========================================
        # Asumimos 10m de cable doméstico
        longitud_cable = 10.0  # metros
        resistencia_cable = (MotorFisica.RHO_COBRE * longitud_cable) / MotorFisica.AREA_CABLE_STD
        perdida_watts = (corriente ** 2) * resistencia_cable  # P = I²R
        perdida_porcentaje = (perdida_watts / watts) * 100 if watts > 0 else 0

        # ========================================
        # 8️⃣ ENERGÍA DEL CAMPO MAGNÉTICO (U = ½LI²)
        # ========================================
        # Inductancia aproximada de 10m de cable: L ≈ 0.2·L·ln(2L/r)
        inductancia = 2e-6  # Henrios (valor típico simplificado)
        energia_magnetica = 0.5 * inductancia * (corriente ** 2)  # Joules

        # ========================================
        # 9️⃣ FACTOR DE POTENCIA (Asumido 0.95 típico residencial)
        # ========================================
        factor_potencia = 0.95
        potencia_reactiva = watts * math.tan(math.acos(factor_potencia))  # VAR

        # ========================================
        # 🔟 IMPACTO AMBIENTAL
        # ========================================
        co2_emitido = kwh * MotorFisica.FACTOR_CO2  # kg CO2
        arboles_equivalentes = co2_emitido / 21  # 1 árbol absorbe ~21kg CO2/año

        # ========================================
        # 📊 CLASIFICACIÓN DE RIESGO ELECTROMAGNÉTICO
        # ========================================
        # OMS recomienda <100 µT para exposición continua
        if campo_microtesla < 1:
            nivel_riesgo = "SEGURO"
        elif campo_microtesla < 10:
            nivel_riesgo = "BAJO"
        elif campo_microtesla < 100:
            nivel_riesgo = "MODERADO"
        else:
            nivel_riesgo = "ALTO"

        # ========================================
        # 📦 RETORNO COMPLETO DE ANÁLISIS
        # ========================================
        return {
            # Básicos (Ley de Ohm)
            "I": round(corriente, 3),  # Amperios
            "R": round(resistencia, 2),  # Ohms
            "V": MotorFisica.VOLTAJE,  # Voltios

            # Energía (Ley de Joule)
            "J": round(energia_joules, 2),  # Joules
            "kWh": round(kwh, 3),  # Kilovatio-hora

            # Electromagnetismo (Ley de Ampère)
            "B": round(campo_microtesla, 2),  # Microteslas
            "B_nivel": nivel_riesgo,  # Clasificación
            "U_mag": round(energia_magnetica, 6),  # Energía magnética (J)

            # Carga y Densidad
            "Q": round(carga_coulombs, 2),  # Coulombs
            "J_densidad": round(densidad_corriente, 0),  # A/m²

            # Pérdidas (Efecto Joule en cables)
            "P_perdida": round(perdida_watts, 3),  # Watts perdidos
            "eficiencia": round(100 - perdida_porcentaje, 2),  # %

            # Potencia Reactiva
            "VAR": round(potencia_reactiva, 2),  # Voltio-amperio reactivo
            "FP": factor_potencia,  # Factor de potencia

            # Ambiental
            "CO2": round(co2_emitido, 2),  # kg CO2
            "arboles": round(arboles_equivalentes, 3)  # Árboles equivalentes
        }

    @staticmethod
    def analizar_circuito_completo(lista_items):
        """
        ANÁLISIS DEL CIRCUITO ELÉCTRICO COMPLETO (Leyes de Kirchhoff)
        Todos los aparatos están en PARALELO en una casa

        Parámetros:
            lista_items: Lista de diccionarios con datos de cada aparato

        Retorna:
            dict: Análisis del circuito total
        """

        # Corriente total (suma en paralelo)
        corriente_total = sum(item['fisica']['I'] for item in lista_items)

        # Potencia total
        potencia_total = sum(item['watts'] for item in lista_items)

        # Campo magnético resultante (suma vectorial simplificada)
        campo_total = sum(item['fisica']['B'] for item in lista_items)

        # Resistencia equivalente en paralelo: 1/Req = Σ(1/Ri)
        suma_inversos = sum(1 / item['fisica']['R'] for item in lista_items if item['fisica']['R'] > 0)
        resistencia_equivalente = 1 / suma_inversos if suma_inversos > 0 else float('inf')

        # Verificación de seguridad (Límite 20A típico en Perú)
        LIMITE_CORRIENTE = 20.0
        estado_circuito = "SEGURO" if corriente_total < LIMITE_CORRIENTE else "⚠️ SOBRECARGA"

        # Caída de voltaje estimada
        caida_voltaje = corriente_total * resistencia_equivalente * 0.01  # Simplificado

        return {
            "I_total": round(corriente_total, 2),
            "P_total": round(potencia_total, 2),
            "R_eq": round(resistencia_equivalente, 2),
            "B_total": round(campo_total, 2),
            "estado": estado_circuito,
            "porcentaje_carga": round((corriente_total / LIMITE_CORRIENTE) * 100, 1),
            "caida_V": round(caida_voltaje, 3)
        }

    @staticmethod
    def calcular_efecto_piel(frecuencia=60):
        """
        EFECTO PIEL (Skin Effect) en conductores AC
        En Perú: 60 Hz

        δ = √(ρ/(πfμ))  donde δ es la profundidad de penetración
        """
        mu = MotorFisica.MU_0
        rho = MotorFisica.RHO_COBRE

        profundidad = math.sqrt(rho / (math.pi * frecuencia * mu))
        return round(profundidad * 1000, 3)  # En milímetros