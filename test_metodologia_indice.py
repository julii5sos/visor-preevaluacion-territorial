import unittest

from metodologia_indice import (
    PESOS_INDICE,
    PUNTAJE_MAXIMO,
    calcular_indice_prioridad,
    evaluar_senales,
)


class IndicePrioridadTest(unittest.TestCase):
    def calcular(self, tmf=False, hansen=False, esri=False, gedi=False):
        return calcular_indice_prioridad(
            senal_tmf=tmf,
            senal_hansen=hansen,
            senal_esri=esri,
            senal_gedi=gedi,
        )

    def test_pesos_metodologicos(self):
        self.assertEqual(PESOS_INDICE["tmf"], 2.0)
        self.assertEqual(PESOS_INDICE["hansen"], 2.0)
        self.assertEqual(PESOS_INDICE["esri"], 1.5)
        self.assertEqual(PESOS_INDICE["gedi"], 0.5)
        self.assertEqual(PESOS_INDICE["ndvi"], 0.0)
        self.assertEqual(PUNTAJE_MAXIMO, 6.0)

    def test_esri_no_supera_fuentes_forestales(self):
        aportes_esri, puntaje_esri, prioridad_esri = self.calcular(esri=True)
        _, puntaje_tmf, _ = self.calcular(tmf=True)
        _, puntaje_hansen, _ = self.calcular(hansen=True)

        self.assertEqual(aportes_esri["esri"], 1.5)
        self.assertEqual(aportes_esri["ndvi"], 0.0)
        self.assertEqual(puntaje_esri, 1.5)
        self.assertEqual(prioridad_esri, "Media")
        self.assertLess(puntaje_esri, puntaje_tmf)
        self.assertLess(puntaje_esri, puntaje_hansen)

    def test_cada_fuente_se_suma_una_sola_vez(self):
        aportes, puntaje, prioridad = self.calcular(
            tmf=True,
            hansen=True,
            esri=True,
            gedi=True,
        )

        self.assertEqual(aportes, PESOS_INDICE)
        self.assertEqual(puntaje, 6.0)
        self.assertEqual(prioridad, "Alta")

    def test_gedi_solo_genera_prioridad_preventiva(self):
        _, puntaje, prioridad = self.calcular(gedi=True)
        self.assertEqual(puntaje, 0.5)
        self.assertEqual(prioridad, "Preventiva")

    def test_sin_senales_la_prioridad_es_baja(self):
        aportes, puntaje, prioridad = self.calcular()
        self.assertTrue(all(valor == 0.0 for valor in aportes.values()))
        self.assertEqual(puntaje, 0.0)
        self.assertEqual(prioridad, "Baja")

    def evaluar(self, **cambios):
        valores = {
            "tmf_deforestacion_ha": 0.0,
            "tmf_deforestacion_pct": 0.0,
            "tmf_degradacion_ha": 0.0,
            "tmf_degradacion_pct": 0.0,
            "hansen_post_2020_ha": 0.0,
            "esri_salida_arboles_ha": 0.0,
            "esri_salida_arboles_pct": 0.0,
            "gedi_altura_media_m": 20.0,
            "gedi_cobertura_valida_pct": 100.0,
            "linea_base_arborea_pct": 100.0,
        }
        valores.update(cambios)
        return evaluar_senales(**valores)

    def test_esri_exige_extension_y_porcentaje(self):
        senales, _ = self.evaluar(
            esri_salida_arboles_ha=0.10,
            esri_salida_arboles_pct=4.9,
        )
        self.assertFalse(senales["esri"])

        senales, _ = self.evaluar(
            esri_salida_arboles_ha=0.09,
            esri_salida_arboles_pct=5.0,
        )
        self.assertFalse(senales["esri"])

        senales, _ = self.evaluar(
            esri_salida_arboles_ha=0.10,
            esri_salida_arboles_pct=5.0,
        )
        self.assertTrue(senales["esri"])

    def test_jrc_admite_umbral_absoluto_o_relativo(self):
        senales, _ = self.evaluar(tmf_deforestacion_pct=1.0)
        self.assertTrue(senales["tmf"])

        senales, _ = self.evaluar(tmf_degradacion_ha=2.0)
        self.assertTrue(senales["tmf"])

    def test_gedi_requiere_los_tres_criterios(self):
        senales, disponible = self.evaluar(
            gedi_altura_media_m=7.9,
            gedi_cobertura_valida_pct=20.0,
            linea_base_arborea_pct=10.0,
        )
        self.assertTrue(disponible)
        self.assertTrue(senales["gedi"])

        senales, disponible = self.evaluar(
            gedi_altura_media_m=7.9,
            gedi_cobertura_valida_pct=19.9,
            linea_base_arborea_pct=10.0,
        )
        self.assertFalse(disponible)
        self.assertFalse(senales["gedi"])


if __name__ == "__main__":
    unittest.main()
