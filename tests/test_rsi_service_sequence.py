"""Exercise service routing without importing the app, config or live clients."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call


class SequenceTests(unittest.TestCase):
    def service(self):
        path = Path(__file__).resolve().parents[1] / 'SignalDetectorService.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        cls.bases = []
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '__initTask']
        env = {}
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(path), 'exec'), env)
        service = env['SignalDetectorService']()
        service._SignalDetectorService__testNo = 20
        agent = Mock()
        service._SignalDetectorService__tradingAgent = agent
        service._SignalDetectorService__log = Mock()
        return service, agent

    def test_buy_then_sell_without_live_initialization(self):
        service, agent = self.service()
        service._SignalDetectorService__initTask()
        self.assertEqual(agent.mock_calls, [
            call.runBuyRSIBuyOperation(target_symbol=None, wait_minutes=60, cooldown_hours=2),
            call.runSellRSIOperation(target_symbol=None)])

    def test_buy_failure_does_not_start_sell(self):
        service, agent = self.service()
        agent.runBuyRSIBuyOperation.side_effect = RuntimeError('buy failed')
        with self.assertRaisesRegex(RuntimeError, 'buy failed'):
            service._SignalDetectorService__initTask()
        agent.runSellRSIOperation.assert_not_called()

    def test_test20_constructs_database_only_agent(self):
        path = Path(__file__).resolve().parents[1] / 'SignalDetectorService.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        constructor = next(n for n in ast.walk(tree) if isinstance(n, ast.Call)
                           and isinstance(n.func, ast.Name) and n.func.id == 'TradingAgent')
        expression = next(k.value for k in constructor.keywords if k.arg == 'database_only')
        service = SimpleNamespace(_SignalDetectorService__testNo=20, __testNo=20)
        self.assertTrue(eval(compile(ast.Expression(expression), str(path), 'eval'), {'self': service}))


if __name__ == '__main__':
    unittest.main()
