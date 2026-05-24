from __future__ import annotations

import unittest

from travelmate.agents.formatter_agent import _is_formatter_output_consistent


class FormatterAgentConsistencyTests(unittest.TestCase):
    def test_accepts_consistent_destination_and_days(self) -> None:
        markdown = """
## 🗺️ Lizbona - Plan Podróży (5 Dni)

### Dzień 1: Alfama
### Dzień 2: Baixa
### Dzień 3: Belém
### Dzień 4: Chiado
### Dzień 5: Sintra
""".strip()
        ok, reason = _is_formatter_output_consistent(markdown, destination="Lizbona", expected_days=5)
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_rejects_destination_mismatch(self) -> None:
        markdown = """
## 🗺️ 3 Dni w Paryżu: Sztuka i Historia
### Dzień 1: Centrum
### Dzień 2: Montmartre
### Dzień 3: Sekwana
""".strip()
        ok, reason = _is_formatter_output_consistent(markdown, destination="Lizbona", expected_days=3)
        self.assertFalse(ok)
        self.assertEqual(reason, "destination_mismatch")

    def test_rejects_days_mismatch_when_headers_present(self) -> None:
        markdown = """
## 🗺️ Paryż - Plan Podróży
### Dzień 1: Centrum
### Dzień 2: Montmartre
### Dzień 3: Luwr
""".strip()
        ok, reason = _is_formatter_output_consistent(markdown, destination="Paryż", expected_days=5)
        self.assertFalse(ok)
        self.assertEqual(reason, "days_mismatch:3!=5")


if __name__ == "__main__":
    unittest.main()
